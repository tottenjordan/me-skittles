# Google Cloud Brand Reference

## Core Colors

| Name | Hex | Usage |
|------|-----|-------|
| Blue | `#4285F4` | Primary brand, links, interactive elements |
| Red | `#EA4335` | Alerts, errors, critical items |
| Yellow | `#FBBC05` | Warnings, highlights, data/analytics |
| Green | `#34A853` | Success, healthy, active states |
| Dark Gray | `#202124` | Primary text |
| Medium Gray | `#5F6368` | Secondary text |
| Light Gray | `#E8EAED` | Borders, dividers |
| White | `#FFFFFF` | Backgrounds |

## Extended Palette (Diagram Accents)

| Purpose | Hex | Usage |
|---------|-----|-------|
| Deep Blue | `#1A73E8` | Selected states, emphasis |
| Light Blue | `#E8F0FE` | Blue tinted backgrounds |
| Deep Green | `#1E8E3E` | Active/running indicators |
| Light Green | `#E6F4EA` | Green tinted backgrounds |
| Deep Red | `#D93025` | Error states |
| Light Red | `#FCE8E6` | Red tinted backgrounds |
| Deep Yellow | `#F9AB00` | Data/analytics accent |
| Light Yellow | `#FEF7E0` | Yellow tinted backgrounds |
| Purple | `#A142F4` | AI/ML features |
| Light Purple | `#F3E8FD` | AI tinted backgrounds |
| Teal | `#12B5CB` | Networking, serverless |
| Light Teal | `#E4F7FB` | Teal tinted backgrounds |

## Typography

- **Primary**: Google Sans (headings, product names)
- **Body**: Roboto (body text, descriptions)
- **Mono**: Roboto Mono (code, resource IDs)
- **Sizes**: Title 24-32px, Subtitle 16-20px, Body 13-14px, Caption 11-12px

## Icon System (2025)

### Core Product Icons (4-color, unique)

Unique icons for top products. Use all 4 brand colors:
- AI: Vertex AI, AI Hypercomputer
- Compute: Compute Engine, GKE, Cloud Run
- Data: BigQuery, Spanner, AlloyDB, Cloud SQL
- Storage: Cloud Storage, Hyperdisk
- Analytics: Looker
- Integration: Apigee
- Security: Security Command Center, Google Security Operations, Mandiant, Google Threat Intelligence
- Hybrid: Anthos, Google Distributed Cloud

### Category Product Icons (2-color, blue + gray)

Simpler 2-color icons for product categories:
- AI/ML, AI Applications & Agents
- Compute, Containers, Serverless Computing
- Data Analytics, Databases, Business Intelligence
- Storage, Networking
- Security Identity, Operations, Observability
- Developer Tools, DevOps
- Migration, Integration Services
- Management Tools, Hybrid & Multicloud
- Media Services, Maps & Geospatial
- Collaboration, Web3, Mixed Reality, Marketplace

## Diagram Style Guidelines

### Layout
- Clean white background (`#FFFFFF`)
- Consistent spacing (16px/24px/32px grid)
- Top-to-bottom or left-to-right flow
- Group related services in rounded-corner containers
- Use subtle background tints for grouping (light blue, light green, etc.)

### Containers/Groups
- Rounded corners (8-12px radius)
- 1-2px border in group color
- Light tint fill matching border color
- Group label at top-left in bold

### Nodes/Services
- Rounded rectangle boxes (6-8px radius) — NEVER hexagons
- White fill with colored left border or icon
- Product name in Google Sans 14px
- Resource ID or detail in Roboto 11px gray
- Do NOT use hexagonal shapes — GCP icons are rectangular/circular, never hexagonal

### Connections
- Straight lines or right-angle connectors
- 1.5-2px stroke width
- Arrowheads for direction
- Labels in Roboto 11px, placed at midpoint
- Use color to indicate connection type

### Legend
- Bottom or right side
- Color-coded connection types
- Icon meaning if non-obvious

### Watermark
- "Google Cloud" logo at bottom-left
- Small, subtle, not distracting
