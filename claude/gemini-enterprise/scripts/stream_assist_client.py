"""Portable StreamAssist client for the Discovery Engine REST API.

A standalone client for querying Gemini Enterprise via the streamAssist
conversational endpoint. Handles authentication, session management,
retry logic, and connection pooling.

Usage:
    from stream_assist_client import StreamAssistClient

    client = StreamAssistClient(
        project_id="my-project",
        location="global",
        engine_id="my-engine",
    )
    session_id = client.create_session()
    response = client.query("What are the closing procedures?", session_id)
    print(response.text)

Requirements:
    pip install google-auth requests tenacity
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import google.auth
import requests
from google.auth.transport.requests import Request
from requests.adapters import HTTPAdapter
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class AgentAuthorizationError(Exception):
    """Raised when agent requires OAuth authorization (403 error)."""

    def __init__(self, agent_id: str, project_id: str, location: str, engine_id: str):
        self.agent_id = agent_id
        self.project_id = project_id
        self.location = location
        self.engine_id = engine_id
        super().__init__(f"Agent {agent_id} requires OAuth authorization")


class RetryableAPIError(Exception):
    """Raised when API returns a retryable error (429, 500-504)."""


@dataclass
class StreamAssistReply:
    """Parsed reply from a streamAssist response chunk."""

    text: str = ""
    role: str = "model"
    is_thought: bool = False


@dataclass
class StreamAssistResponse:
    """Parsed streamAssist response with extracted content.

    Properties:
        text: Concatenated non-thought reply text (the grounded answer).
        thoughts: Concatenated thought text (model reasoning).
    """

    replies: List[StreamAssistReply] = field(default_factory=list)
    session_name: Optional[str] = None
    state: Optional[str] = None
    raw: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Concatenated non-thought reply text."""
        return "\n".join(r.text for r in self.replies if not r.is_thought and r.text)

    @property
    def thoughts(self) -> str:
        """Concatenated thought text."""
        return "\n".join(r.text for r in self.replies if r.is_thought and r.text)


class StreamAssistClient:
    """Client for the Discovery Engine streamAssist REST API.

    Handles authentication via Application Default Credentials, session
    management, retry logic with exponential backoff, and connection pooling.

    Args:
        project_id: GCP project ID.
        location: Engine location ("global" or regional like "us-central1").
        engine_id: Discovery Engine engine ID.
        agent_id: Optional agent ID for routing queries to a specific agent.
        max_connections: Maximum connections in the connection pool.
    """

    def __init__(
        self,
        project_id: str,
        location: str,
        engine_id: str,
        agent_id: str = "",
        max_connections: int = 100,
    ):
        self.project_id = project_id
        self.location = location
        self.engine_id = engine_id
        self.agent_id = agent_id

        # Regional vs global endpoint
        if location == "global":
            api_endpoint = "https://discoveryengine.googleapis.com"
        else:
            api_endpoint = f"https://{location}-discoveryengine.googleapis.com"

        self.base_url = (
            f"{api_endpoint}/v1alpha/projects/{project_id}/locations/{location}"
            f"/collections/default_collection/engines/{engine_id}"
        )
        self.credentials, _ = google.auth.default()

        # Connection pooling with transport-level retries
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=max_connections,
            max_retries=Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=[500, 502, 503, 504],
            ),
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "StreamAssistClient":
        """Create client from a config dictionary.

        Expected keys:
            config["project"]["id"]
            config["project"]["location"]
            config["project"]["engine_id"]
            config["project"]["agent_id"]  (optional)
        """
        project = config["project"]
        return cls(
            project_id=project["id"],
            location=project["location"],
            engine_id=project["engine_id"],
            agent_id=project.get("agent_id", ""),
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get authenticated request headers, refreshing credentials if needed."""
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        return {
            "Authorization": f"Bearer {self.credentials.token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": self.project_id,
        }

    def create_session(self, display_name: str = "Session") -> str:
        """Create a conversation session.

        Returns the full session resource name, e.g.:
        projects/{project}/locations/{location}/collections/default_collection/
        engines/{engine}/sessions/{session_id}
        """
        url = f"{self.base_url}/sessions"
        headers = self._get_headers()
        payload = {"displayName": display_name}
        response = self.session.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["name"]

    @retry(
        retry=retry_if_exception_type(RetryableAPIError),
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, min=4, max=120),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def query(
        self, text: str, session_id: Optional[str] = None
    ) -> StreamAssistResponse:
        """Query the agent via the streamAssist endpoint.

        Args:
            text: The query text to send to the agent.
            session_id: Optional session resource name. If omitted, uses
                auto-session (sessions/-) which creates a session implicitly.

        Returns:
            Parsed StreamAssistResponse with replies, thoughts, and session info.

        Raises:
            AgentAuthorizationError: For 403 errors (not retried).
            RetryableAPIError: For 429/5xx errors (automatically retried).
        """
        if not session_id:
            session_name = (
                f"projects/{self.project_id}/locations/{self.location}"
                f"/collections/default_collection/engines/{self.engine_id}/sessions/-"
            )
        else:
            session_name = session_id

        url = f"{self.base_url}/assistants/default_assistant:streamAssist"
        headers = self._get_headers()

        payload: Dict[str, Any] = {
            "session": session_name,
            "query": {"text": text},
        }

        # Route to specific agent if configured
        if self.agent_id:
            payload["agentsSpec"] = {
                "agentSpecs": [{"agentId": self.agent_id}]
            }

        logger.info("Querying agent with: %s", text)
        response = self.session.post(url, headers=headers, json=payload)

        if not response.ok:
            self._handle_error(response)

        return self._parse_response(response.json())

    def _handle_error(self, response: requests.Response) -> None:
        """Handle HTTP error responses with appropriate retry/raise behavior."""
        if response.status_code == 403:
            logger.error("Agent requires authorization (403 Forbidden)")
            raise AgentAuthorizationError(
                agent_id=self.agent_id,
                project_id=self.project_id,
                location=self.location,
                engine_id=self.engine_id,
            )

        if response.status_code in [429, 500, 502, 503, 504]:
            logger.warning(
                "Retryable error %d: %s", response.status_code, response.text[:200]
            )
            raise RetryableAPIError(
                f"API returned retryable status {response.status_code}"
            )

        if response.status_code == 400:
            if "FAILED_PRECONDITION" in response.text:
                logger.error("Agent execution failed (FAILED_PRECONDITION)")
                response.raise_for_status()
            else:
                logger.warning("Retryable 400 error: %s", response.text[:200])
                raise RetryableAPIError(
                    f"API returned retryable status {response.status_code}"
                )

        logger.error("Request failed with status %d", response.status_code)
        response.raise_for_status()

    @staticmethod
    def _parse_response(data: Any) -> StreamAssistResponse:
        """Parse raw streamAssist JSON response into structured objects.

        The streamAssist response is an array of chunks. Each chunk may contain:
        - "answer" with "replies" array (each reply has groundedContent.content)
        - "sessionInfo" with the session resource name

        Reply content fields:
        - text: The response text
        - role: "model" or "user"
        - thought: True if this is model reasoning, False for final answer
        """
        if not isinstance(data, list):
            data = [data]

        result = StreamAssistResponse(raw=data)

        for chunk in data:
            if "answer" in chunk:
                answer = chunk["answer"]
                result.state = answer.get("state", result.state)
                for reply in answer.get("replies", []):
                    grounded = reply.get("groundedContent", {})
                    content = grounded.get("content", {})
                    result.replies.append(
                        StreamAssistReply(
                            text=content.get("text", ""),
                            role=content.get("role", "model"),
                            is_thought=content.get("thought", False),
                        )
                    )
            if "sessionInfo" in chunk:
                session_info = chunk["sessionInfo"]
                result.session_name = session_info.get("name")

        return result


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 4:
        print("Usage: python stream_assist_client.py PROJECT_ID ENGINE_ID QUERY")
        print('Example: python stream_assist_client.py my-project my-engine "What are the closing procedures?"')
        sys.exit(1)

    project_id = sys.argv[1]
    engine_id = sys.argv[2]
    query_text = sys.argv[3]

    client = StreamAssistClient(
        project_id=project_id,
        location="global",
        engine_id=engine_id,
    )

    session = client.create_session()
    print(f"Session: {session}")

    resp = client.query(query_text, session)
    print(f"\nAnswer:\n{resp.text}")
    if resp.thoughts:
        print(f"\nThoughts:\n{resp.thoughts}")
