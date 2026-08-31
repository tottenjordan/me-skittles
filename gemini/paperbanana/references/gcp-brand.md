# GCP Brand Kit + Verification (for PaperBanana diagrams)

Reference for producing diagrams styled like official Google Cloud Platform
documentation via `mcp__paperbanana__generate_diagram`. Fold the phrases and
color conventions below into `source_context` / `caption`.

## Required phrases in every GCP-diagram prompt

- "professional, clean architecture diagram in the style of official Google Cloud Platform documentation"
- "GCP brand colors: blue (#4285F4), green (#34A853), yellow (#FBBC05), red (#EA4335)"
- "clean white background"
- "Google Cloud product icon style, clean lines, no 3D effects, no hexagons, modern flat design"
- "Google Cloud logo watermark at bottom left"

## Color conventions by component type

| Component type | Color |
|---|---|
| Compute / Agents | Green `#34A853` |
| Data / Analytics / BigQuery | Orange-Yellow `#F9AB00` |
| AI / ML / Vertex AI | Purple `#A142F4` |
| Storage / GCS | Yellow `#FBBC05` |
| Networking / Serverless | Teal `#12B5CB` |
| Security | Red `#EA4335` |
| Discovery Engine / Search | Blue `#4285F4` |
| Users / Clients | Red ellipse `#EA4335` |
| Config / Infrastructure | Gray `#5F6368` |

## Shape hints

- Rounded rectangle → service
- Cylinder → database
- Ellipse → users / clients
- Octagon → security control
- Folder → storage bucket

## Verification checklist (MANDATORY before delivering)

**Branding**
- [ ] Colors match the conventions above
- [ ] Clean white background (`#FFFFFF`)
- [ ] Rounded rectangles / circles / ellipses — **never hexagons**
- [ ] No 3D effects, shadows, or gradients on service boxes
- [ ] Google Cloud watermark at bottom left

**Spelling** — read every label; compare to official product names:

| Correct | Common mistakes |
|---|---|
| BigQuery | Big Query, Bigquery, BQ |
| Cloud Run | CloudRun, Cloud run |
| Vertex AI | VertexAI, Vertex.AI, Vertex ai |
| Cloud Storage | CloudStorage, GCS (ok in code, not diagrams) |
| Pub/Sub | PubSub, Pub Sub |
| Cloud SQL | CloudSQL |
| Kubernetes Engine | Kubernete Engine, K8s Engine |
| Agent Engine | AgentEngine |
| Gemini | Gemni, Gemnini |
| Imagen | ImageGen, Image Gen |

- [ ] Every service name matches official spelling
- [ ] Custom labels (agent/dataset names) spelled correctly
- [ ] Acronyms consistent (don't mix "BQ" and "BigQuery")
- [ ] Resource IDs / regions match actual deployed values

**Layout**
- [ ] All components labeled; connections directional with protocols noted
- [ ] Text readable at display size; no overlapping elements

If any check fails, refine with `continue_diagram(run_id=..., feedback="fix: <what>",
image_model="gemini-3.1-flash-image", vlm_model="gemini-3.5-flash")` rather than
regenerating from scratch.
