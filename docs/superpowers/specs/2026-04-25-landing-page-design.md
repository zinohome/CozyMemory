# CozyMemory Landing Page Design Spec

**Date**: 2026-04-25
**Status**: Approved

---

## Goal

Build a bilingual (EN/ZH) product landing page for CozyMemory using the AstroWind template, deployed to GitHub Pages via GitHub Actions. The site targets AI application developers and technical decision-makers, showcasing CozyMemory's three-engine unified memory platform.

## Decisions

| Dimension | Decision |
|-----------|----------|
| Template | AstroWind (Astro 5 + Tailwind CSS), fork and customize |
| Audience | AI developers + technical decision-makers |
| Pages | Home + Features + Blog + About (x2 languages) |
| i18n | English default (`/`), Chinese at `/zh/` prefix, manual translations |
| Deployment | GitHub Pages + GitHub Actions auto-build |
| Location | `website/` subdirectory in main repo |
| Style | AstroWind default blue-purple palette + dark mode |
| Initial blog | 1 post: "Introducing CozyMemory v0.2.0" |

---

## 1. Project Structure

```
website/
├── src/
│   ├── pages/
│   │   ├── index.astro              # EN Home
│   │   ├── features.astro           # EN Features
│   │   ├── about.astro              # EN About
│   │   ├── blog/                    # EN Blog (auto-generated from content)
│   │   └── zh/
│   │       ├── index.astro          # ZH Home
│   │       ├── features.astro       # ZH Features
│   │       ├── about.astro          # ZH About
│   │       └── blog/                # ZH Blog
│   ├── content/
│   │   └── post/
│   │       ├── en/                  # EN blog posts (MDX)
│   │       └── zh/                  # ZH blog posts (MDX)
│   ├── components/                  # AstroWind components (retained and reused)
│   ├── layouts/                     # Page layouts
│   ├── assets/                      # Images, icons
│   │   └── images/
│   │       ├── hero-architecture.svg
│   │       ├── screenshot-profiles.png
│   │       └── screenshot-knowledge.png
│   └── i18n/
│       ├── en.ts                    # EN UI strings (nav, buttons, footer)
│       └── zh.ts                    # ZH UI strings
├── public/
│   ├── favicon.ico
│   └── og-image.png                 # Open Graph preview image
├── astro.config.mjs
├── tailwind.config.js
└── package.json
```

## 2. Pages

### 2.1 Header (shared across all pages)

- Left: Logo + "CozyMemory" text
- Center nav: Home / Features / Blog / About
- Right: Language toggle (EN/ZH) + GitHub Star badge + Dark mode toggle

### 2.2 Home Page (`/` and `/zh/`)

Seven sections, top to bottom:

**Section 1 — Hero**
- Headline (EN): "Unified AI Memory for Every LLM App"
- Subline: "One API to rule three memory engines — conversations, profiles, and knowledge graphs. Self-hosted, open-source, production-ready."
- CTA buttons: "Get Started" (-> GitHub README) / "API Docs" (-> Swagger UI)
- Visual: simplified architecture diagram as SVG (derived from README ASCII art)

**Section 2 — Three Engines Cards**
Three columns, each card: icon + engine name + tagline + 3 capability bullet points

| Mem0 Conversation Memory | Memobase User Profiles | Cognee Knowledge Graph |
|---|---|---|
| Auto-extract facts from conversations | Structured preference storage | Documents -> entity-relation graphs |
| Semantic search | Generate LLM context prompts | Graph retrieval |
| Fact dedup & merge | Multi-dimension profiles | RAG enhancement |

**Section 3 — Code Example**
Python SDK snippet showing 4-line integration:
```python
from cozymemory import CozyMemoryClient
with CozyMemoryClient(api_key="cozy_xxx") as c:
    c.conversations.add("alice", [{"role": "user", "content": "I love hiking"}])
    ctx = c.context.get_unified("alice", query="outdoor activity")
```

**Section 4 — Stats Bar**
Four metrics: `3 Engines` / `50+ API Endpoints` / `524 Unit Tests` / `REST + gRPC`

**Section 5 — Why CozyMemory**
Four advantage cards (icon + title + description):
- **Unified API** — One interface aggregating three memory types
- **Multi-tenant Ready** — Organization -> App -> Key data isolation, SaaS-grade auth
- **Self-hosted** — Docker Compose one-click deploy, full data control
- **Observable** — Built-in Prometheus + Grafana monitoring and alerting

**Section 6 — Bottom CTA**
"Star on GitHub" + "Read the Docs" buttons

**Section 7 — Footer (shared)**
- Project links: GitHub / Docs / Swagger / Changelog
- Community: Issues / Discussions
- License: AGPL-3.0
- "Built with Astro + AstroWind"

### 2.3 Features Page (`/features` and `/zh/features`)

Three engine sections in alternating left-right layout (text-image zigzag):

**Block 1 — Mem0 Conversation Memory**
- Left: capability description (auto-extract facts, semantic search, fact dedup, conversation history)
- Right: API code examples (`POST /conversations` + `POST /conversations/search`)

**Block 2 — Memobase User Profiles**
- Left: screenshot of admin UI Profiles page
- Right: capability description (structured profiles, LLM context prompt generation, multi-topic management)

**Block 3 — Cognee Knowledge Graph**
- Left: capability description (document ingestion, graph building, search modes: CHUNKS/SUMMARIES/GRAPH_COMPLETION)
- Right: force-directed graph visualization screenshot from admin UI Knowledge page

**Bottom Banner — Unified Context**
Highlight `POST /context` endpoint: one call fuses all three engines. Show code example + JSON response structure.

### 2.4 Blog Page (`/blog` and `/zh/blog`)

- AstroWind built-in blog system, MDX format
- Initial post: "Introducing CozyMemory v0.2.0" (adapted from CHANGELOG.md)
- Tags and categories supported
- RSS feed auto-generated
- EN posts in `content/post/en/`, ZH posts in `content/post/zh/`

### 2.5 About Page (`/about` and `/zh/about`)

Single-section page:
- Project vision: why unify three memory engines
- Tech stack overview: Python 3.11 / FastAPI / gRPC / Next.js 16 / Docker
- License: AGPL-3.0 explanation
- Contributing: link to GitHub CONTRIBUTING.md (to be created)
- Contact: GitHub Issues link

### 2.6 Docs Entry

Not a standalone page. Header nav "Docs" links externally:
- "API Reference" -> GitHub docs folder (`https://github.com/zinohome/CozyMemory/tree/main/docs/api-reference.md`)
- "GitHub Docs" -> `https://github.com/zinohome/CozyMemory/tree/main/docs`

## 3. i18n Strategy

- Default language: English (routes at `/`)
- Chinese: all routes prefixed with `/zh/`
- Header language toggle button switches between corresponding pages
- Translation approach:
  - UI strings (nav, buttons, footer labels) in `src/i18n/en.ts` and `src/i18n/zh.ts`
  - Page body content: separate `.astro` files per language (not auto-translated)
  - Blog posts: separate MDX files per language in `content/post/en/` and `content/post/zh/`

## 4. Visual Assets

Sources for images:
- **Architecture diagram**: convert README ASCII art to a clean SVG
- **Product screenshots**: use existing screenshots from repo root (`dark_dash.png`, `dark_kb.png`, `dark_pg.png`, etc.)
- **Engine icons**: use AstroWind's built-in icon system (Tabler icons)
- **OG image**: create a 1200x630 preview card with logo + tagline

## 5. Deployment

### GitHub Actions Workflow

File: `.github/workflows/deploy-website.yml`

```yaml
name: Deploy Website
on:
  push:
    branches: [main]
    paths: ['website/**']
  workflow_dispatch:

jobs:
  build-deploy:
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm ci
        working-directory: website
      - run: npm run build
        working-directory: website
      - uses: actions/upload-pages-artifact@v3
        with:
          path: website/dist
      - uses: actions/deploy-pages@v4
```

### Astro Config

```javascript
// website/astro.config.mjs
export default defineConfig({
  site: 'https://zinohome.github.io',
  base: '/CozyMemory',
  output: 'static',
  // ... AstroWind integrations
});
```

### Repository Settings

- Settings -> Pages -> Source: GitHub Actions
- Custom domain: optional, can be added later

## 6. Scope Exclusions

The following are explicitly NOT in scope for this iteration:
- Custom logo design (use text logo for now)
- Pricing page (open-source, self-hosted only)
- API Playground embedded in landing page
- Automated i18n translation
- Analytics integration (can be added later)
- Custom domain setup
