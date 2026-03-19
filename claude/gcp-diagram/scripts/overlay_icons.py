#!/usr/bin/env python3
"""Overlay official GCP product icons onto a Gemini-generated architecture diagram.

Usage:
    python overlay_icons.py diagram.png output.png --icons "BigQuery:100,200 Vertex AI:400,200 Cloud Run:250,350"

Or programmatically:
    from overlay_icons import overlay_icons
    overlay_icons("diagram.png", "output.png", [
        {"product": "BigQuery", "x": 100, "y": 200},
        {"product": "Vertex AI", "x": 400, "y": 200, "size": 48},
    ])
"""

import argparse
import os
import sys
from pathlib import Path
from PIL import Image

# Map product names to icon file paths (relative to assets/icons/)
ICON_MAP = {
    # Analytics
    "bigquery": "analytics/bigquery.png",
    "big query": "analytics/bigquery.png",
    "composer": "analytics/composer.png",
    "cloud composer": "analytics/composer.png",
    "data catalog": "analytics/data-catalog.png",
    "dataflow": "analytics/dataflow.png",
    "data fusion": "analytics/data-fusion.png",
    "dataproc": "analytics/dataproc.png",
    "looker": "analytics/looker.png",
    "pub/sub": "analytics/pubsub.png",
    "pubsub": "analytics/pubsub.png",
    "cloud pub/sub": "analytics/pubsub.png",
    # API
    "api gateway": "api/api-gateway.png",
    "apigee": "api/apigee.png",
    "endpoints": "api/endpoints.png",
    "cloud endpoints": "api/endpoints.png",
    # Compute
    "app engine": "compute/app-engine.png",
    "compute engine": "compute/compute-engine.png",
    "cloud functions": "compute/functions.png",
    "functions": "compute/functions.png",
    "cloud run": "compute/run.png",
    "gke": "compute/kubernetes-engine.png",
    "kubernetes engine": "compute/kubernetes-engine.png",
    "google kubernetes engine": "compute/kubernetes-engine.png",
    "gpu": "compute/gpu.png",
    # Database
    "bigtable": "database/bigtable.png",
    "cloud bigtable": "database/bigtable.png",
    "datastore": "database/datastore.png",
    "firestore": "database/firestore.png",
    "memorystore": "database/memorystore.png",
    "cloud sql": "database/sql.png",
    "spanner": "database/spanner.png",
    "cloud spanner": "database/spanner.png",
    # ML / AI
    "vertex ai": "ml/vertex-ai.png",
    "ai platform": "ml/ai-platform.png",
    "automl": "ml/automl.png",
    "dialogflow": "ml/dialog-flow-enterprise-edition.png",
    "natural language api": "ml/natural-language-api.png",
    "speech to text": "ml/speech-to-text.png",
    "text to speech": "ml/text-to-speech.png",
    "translation api": "ml/translation-api.png",
    "vision api": "ml/vision-api.png",
    "tpu": "ml/tpu.png",
    "recommendations ai": "ml/recommendations-ai.png",
    "video intelligence api": "ml/video-intelligence-api.png",
    # Network
    "cloud armor": "network/armor.png",
    "cloud cdn": "network/cdn.png",
    "cloud dns": "network/dns.png",
    "cloud load balancing": "network/load-balancing.png",
    "load balancing": "network/load-balancing.png",
    "cloud nat": "network/nat.png",
    "vpc": "network/virtual-private-cloud.png",
    "virtual private cloud": "network/virtual-private-cloud.png",
    "cloud vpn": "network/vpn.png",
    "cloud router": "network/router.png",
    "service mesh": "network/service-mesh.png",
    "traffic director": "network/traffic-director.png",
    "cloud ids": "network/cloud-ids.png",
    "private service connect": "network/private-service-connect.png",
    # Security
    "iam": "security/iam.png",
    "cloud iam": "security/iam.png",
    "iap": "security/iap.png",
    "identity-aware proxy": "security/iap.png",
    "kms": "security/key-management-service.png",
    "cloud kms": "security/key-management-service.png",
    "secret manager": "security/secret-manager.png",
    "security command center": "security/security-command-center.png",
    "scc": "security/security-command-center.png",
    "certificate manager": "security/certificate-manager.png",
    # Storage
    "cloud storage": "storage/storage.png",
    "gcs": "storage/storage.png",
    "filestore": "storage/filestore.png",
    "persistent disk": "storage/persistent-disk.png",
    # DevTools
    "cloud build": "devtools/build.png",
    "cloud shell": "devtools/cloud-shell.png",
    "container registry": "devtools/container-registry.png",
    "artifact registry": "devtools/container-registry.png",
    "cloud scheduler": "devtools/scheduler.png",
    "cloud tasks": "devtools/tasks.png",
    "source repositories": "devtools/source-repositories.png",
    # Common aliases and modern services
    "discovery engine": "ml/recommendations-ai.png",
    "agent builder": "ml/recommendations-ai.png",
    "agent engine": "ml/ai-platform.png",
    "reasoning engine": "ml/ai-platform.png",
    "gemini": "ml/vertex-ai.png",
    "gemini enterprise": "ml/vertex-ai.png",
    "imagen": "ml/vision-api.png",
    "vertex ai imagen": "ml/vision-api.png",
    "alloydb": "database/sql.png",
    "model armor": "network/armor.png",
    "cloud armor": "network/armor.png",
    "cloud logging": "devtools/sdk.png",
    "cloud monitoring": "devtools/sdk.png",
    "artifact registry": "devtools/container-registry.png",
    "cloud deploy": "devtools/build.png",
    "eventarc": "analytics/pubsub.png",
    "workflows": "devtools/scheduler.png",
    "document ai": "ml/natural-language-api.png",
    "healthcare api": "ml/natural-language-api.png",
    "dialogflow cx": "ml/dialog-flow-enterprise-edition.png",
    "memory bank": "ml/ai-hub.png",
    "preload memory tool": "ml/ai-hub.png",
    "a2a": "compute/run.png",
    "mcp toolbox": "analytics/data-catalog.png",
    "genai-toolbox": "analytics/data-catalog.png",
    "stream assist": "ml/recommendations-ai.png",
    "streamassist": "ml/recommendations-ai.png",
    # Official GCP category icons (from services.google.com/fh/files/misc/category-icons.zip)
    "ai/ml": "categories/ai-ml.png",
    "ai machine learning": "categories/ai-ml.png",
    "data analytics": "categories/data-analytics.png",
    "compute": "categories/compute.png",
    "storage category": "categories/storage.png",
    "networking category": "categories/networking.png",
    "security identity": "categories/security.png",
    "databases": "categories/databases.png",
    "containers": "categories/containers.png",
    "serverless computing": "categories/serverless.png",
    "serverless": "categories/serverless.png",
    "developer tools": "categories/developer-tools.png",
    "operations": "categories/operations.png",
    "observability": "categories/observability.png",
    "agents": "categories/agents.png",
    "devops": "categories/devops.png",
    "integration services": "categories/integration.png",
    "management tools": "categories/management-tools.png",
    "hybrid multicloud": "categories/hybrid-multicloud.png",
    "business intelligence": "categories/business-intelligence.png",
    "collaboration": "categories/collaboration.png",
    "marketplace": "categories/marketplace.png",
    "maps geospatial": "categories/maps-geospatial.png",
}

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


def find_icon(product_name: str) -> Path | None:
    """Resolve a product name to its icon file path."""
    key = product_name.lower().strip()
    if key in ICON_MAP:
        path = ASSETS_DIR / ICON_MAP[key]
        if path.exists():
            return path
    # Fuzzy match: try partial matching
    for map_key, icon_path in ICON_MAP.items():
        if key in map_key or map_key in key:
            path = ASSETS_DIR / icon_path
            if path.exists():
                return path
    return None


def overlay_icons(
    input_path: str,
    output_path: str,
    placements: list[dict],
    default_size: int = 48,
) -> str:
    """Overlay official GCP icons onto a diagram image.

    Args:
        input_path: Path to the source diagram image.
        output_path: Path for the output image with overlaid icons.
        placements: List of dicts with keys:
            - product: GCP product name (e.g., "BigQuery", "Cloud Run")
            - x: X coordinate (pixels from left)
            - y: Y coordinate (pixels from top)
            - size: Optional icon size in pixels (default: 48)
        default_size: Default icon size if not specified per-placement.

    Returns:
        Path to the output image.
    """
    diagram = Image.open(input_path).convert("RGBA")
    applied = []
    skipped = []

    for placement in placements:
        product = placement["product"]
        x = int(placement["x"])
        y = int(placement["y"])
        size = int(placement.get("size", default_size))

        icon_path = find_icon(product)
        if icon_path is None:
            skipped.append(product)
            continue

        icon = Image.open(icon_path).convert("RGBA")
        icon = icon.resize((size, size), Image.LANCZOS)

        # Center the icon on the specified coordinates
        paste_x = x - size // 2
        paste_y = y - size // 2

        # Composite using alpha channel
        diagram.paste(icon, (paste_x, paste_y), icon)
        applied.append(product)

    # Save as PNG (preserves transparency) or convert for JPEG
    if output_path.lower().endswith(".jpg") or output_path.lower().endswith(".jpeg"):
        diagram = diagram.convert("RGB")
    diagram.save(output_path)

    if skipped:
        print(f"Warning: No icons found for: {', '.join(skipped)}")
    print(f"Applied {len(applied)} icons: {', '.join(applied)}")
    return output_path


def list_available_icons() -> dict[str, list[str]]:
    """List all available icon product names by category."""
    categories = {}
    for name, path in sorted(ICON_MAP.items()):
        cat = path.split("/")[0]
        categories.setdefault(cat, []).append(name)
    return categories


def main():
    parser = argparse.ArgumentParser(description="Overlay GCP icons on a diagram")
    parser.add_argument("input", help="Input diagram image path")
    parser.add_argument("output", help="Output image path")
    parser.add_argument(
        "--icons",
        required=False,
        help='Icon placements: "Product:x,y Product:x,y,size"',
    )
    parser.add_argument(
        "--list", action="store_true", help="List available icon names"
    )
    parser.add_argument(
        "--size", type=int, default=48, help="Default icon size (default: 48)"
    )
    args = parser.parse_args()

    if args.list:
        categories = list_available_icons()
        for cat, names in sorted(categories.items()):
            print(f"\n{cat}:")
            for n in sorted(set(names)):
                print(f"  - {n}")
        return

    if not args.icons:
        print("Error: --icons is required (or use --list)")
        sys.exit(1)

    # Parse "Product:x,y" or "Product:x,y,size" format
    placements = []
    for spec in args.icons.split():
        parts = spec.rsplit(":", 1)
        if len(parts) != 2:
            print(f"Invalid format: {spec} (expected Product:x,y)")
            continue
        product = parts[0]
        coords = parts[1].split(",")
        placement = {"product": product, "x": coords[0], "y": coords[1]}
        if len(coords) > 2:
            placement["size"] = coords[2]
        placements.append(placement)

    overlay_icons(args.input, args.output, placements, default_size=args.size)


if __name__ == "__main__":
    main()
