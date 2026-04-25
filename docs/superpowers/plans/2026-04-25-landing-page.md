# CozyMemory Landing Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bilingual product landing page for CozyMemory using AstroWind, deployed to GitHub Pages.

**Architecture:** AstroWind template (Astro 5 + Tailwind v3) initialized in `website/` subdirectory. Pages assembled from AstroWind widget components (Hero, Features, Content, Stats, CallToAction). i18n via Astro's built-in routing with `/zh/` prefix for Chinese. GitHub Actions auto-deploys on push.

**Tech Stack:** Astro 5, Tailwind CSS v3, AstroWind template, MDX, GitHub Pages, GitHub Actions

**Spec:** `docs/superpowers/specs/2026-04-25-landing-page-design.md`

---

## File Structure

```
website/                                    # AstroWind template root
├── src/
│   ├── config.yaml                         # Site name, URL, blog, theme settings
│   ├── navigation.ts                       # Header nav + footer links (EN/ZH aware)
│   ├── pages/
│   │   ├── index.astro                     # EN Home (replace AstroWind default)
│   │   ├── features.astro                  # EN Features (new)
│   │   ├── about.astro                     # EN About (replace AstroWind default)
│   │   └── zh/
│   │       ├── index.astro                 # ZH Home
│   │       ├── features.astro              # ZH Features
│   │       └── about.astro                 # ZH About
│   ├── data/
│   │   └── post/
│   │       ├── introducing-cozymemory-v020.mdx   # EN blog post
│   │       └── cozymemory-v020-发布.mdx           # ZH blog post
│   ├── assets/images/
│   │   ├── screenshot-dashboard.png        # Copied from repo root
│   │   ├── screenshot-knowledge.png        # Copied from repo root
│   │   └── screenshot-playground.png       # Copied from repo root
│   └── i18n/
│       ├── index.ts                        # useTranslations() helper
│       ├── en.ts                           # EN UI strings
│       └── zh.ts                           # ZH UI strings
├── astro.config.ts                         # Add i18n routing config
└── .github/workflows/deploy-website.yml    # GitHub Pages deploy (repo root level)
```

**Files to delete** (unused AstroWind demo pages):
- `src/pages/homes/` (entire directory)
- `src/pages/landing/` (entire directory)
- `src/pages/pricing.astro`
- `src/pages/services.astro`
- `src/pages/contact.astro`

---

### Task 1: Initialize AstroWind Template

**Files:**
- Create: `website/` (entire directory via template)

- [ ] **Step 1: Create website directory from AstroWind template**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
npm create astro@latest -- --template onwidget/astrowind website
```

When prompted: select "Install dependencies" (yes), "Initialize git" (no — already in a repo), TypeScript (strict).

- [ ] **Step 2: Verify the template builds**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/website
npm run build
```

Expected: Build completes successfully with output in `website/dist/`.

- [ ] **Step 3: Verify dev server starts**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/website
npm run dev
```

Expected: Dev server starts at `http://localhost:4321`, default AstroWind page renders.

- [ ] **Step 4: Add website to root .gitignore if needed**

Check if `website/node_modules/` and `website/dist/` are covered by existing `.gitignore`. If not, add them to the root `.gitignore`:

```
# Website
website/node_modules/
website/dist/
website/.astro/
```

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add website/ .gitignore
git commit -m "feat(website): initialize AstroWind template in website/"
```

---

### Task 2: Configure Site Settings

**Files:**
- Modify: `website/src/config.yaml`
- Modify: `website/astro.config.ts`

- [ ] **Step 1: Update config.yaml**

Replace the site section and metadata in `website/src/config.yaml`:

```yaml
site:
  name: CozyMemory
  site: 'https://zinohome.github.io'
  base: '/CozyMemory'
  trailingSlash: false

metadata:
  title:
    default: CozyMemory
    template: '%s — CozyMemory'
  description: 'Unified AI Memory for Every LLM App — One API to rule three memory engines: conversations, profiles, and knowledge graphs.'
  robots:
    index: true
    follow: true
  openGraph:
    site_name: CozyMemory
    type: website

i18n:
  language: en
  textDirection: ltr

apps:
  blog:
    isEnabled: true
    postsPerPage: 6
    post:
      permalink: '/%slug%'
    list:
      pathname: 'blog'
    category:
      pathname: 'category'
    tag:
      pathname: 'tag'
    isRelatedPostsEnabled: true
    relatedPostsCount: 4

ui:
  theme: 'system'
```

- [ ] **Step 2: Add i18n routing to astro.config.ts**

Add the `i18n` block to the Astro config in `website/astro.config.ts`:

```typescript
export default defineConfig({
  output: 'static',

  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'zh'],
    routing: {
      prefixDefaultLocale: false,
    },
  },

  // ... keep existing integrations unchanged
});
```

- [ ] **Step 3: Verify build still passes**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/website
npm run build
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add website/src/config.yaml website/astro.config.ts
git commit -m "feat(website): configure site settings and i18n routing"
```

---

### Task 3: Set Up i18n Translation System

**Files:**
- Create: `website/src/i18n/en.ts`
- Create: `website/src/i18n/zh.ts`
- Create: `website/src/i18n/index.ts`

- [ ] **Step 1: Create EN translation strings**

Create `website/src/i18n/en.ts`:

```typescript
export const en = {
  nav: {
    home: 'Home',
    features: 'Features',
    blog: 'Blog',
    about: 'About',
    docs: 'Docs',
  },
  hero: {
    title: 'Unified AI Memory for Every LLM App',
    subtitle:
      'One API to rule three memory engines — conversations, profiles, and knowledge graphs. Self-hosted, open-source, production-ready.',
    getStarted: 'Get Started',
    apiDocs: 'API Docs',
  },
  engines: {
    mem0: {
      name: 'Mem0 · Conversation Memory',
      tagline: 'Auto-extract facts from conversations',
      items: ['Semantic search over memories', 'Fact deduplication & merge', 'Full conversation history'],
    },
    memobase: {
      name: 'Memobase · User Profiles',
      tagline: 'Structured user preference storage',
      items: ['Generate LLM context prompts', 'Multi-dimension profiles', 'Topic-based organization'],
    },
    cognee: {
      name: 'Cognee · Knowledge Graph',
      tagline: 'Documents to entity-relation graphs',
      items: ['Graph retrieval & completion', 'Multiple search modes', 'RAG enhancement'],
    },
  },
  stats: {
    engines: '3 Engines',
    endpoints: '50+ API Endpoints',
    tests: '524 Unit Tests',
    protocols: 'REST + gRPC',
  },
  why: {
    title: 'Why CozyMemory?',
    unified: {
      title: 'Unified API',
      description: 'One interface aggregating three memory types. No need to integrate each engine separately.',
    },
    multiTenant: {
      title: 'Multi-tenant Ready',
      description: 'Organization → App → Key data isolation with SaaS-grade JWT + API Key authentication.',
    },
    selfHosted: {
      title: 'Self-hosted',
      description: 'Docker Compose one-click deploy with 15 containers. Your data stays on your infrastructure.',
    },
    observable: {
      title: 'Observable',
      description: 'Built-in Prometheus + Grafana monitoring with alerting rules out of the box.',
    },
  },
  cta: {
    starOnGithub: 'Star on GitHub',
    readTheDocs: 'Read the Docs',
  },
  features: {
    title: 'Three Engines, One API',
    subtitle: 'Deep dive into each memory engine and how they work together.',
    unifiedContext: {
      title: 'Unified Context',
      description: 'One call to /context fuses all three engines into a single LLM-ready response.',
    },
  },
  about: {
    title: 'About CozyMemory',
    vision:
      'AI applications need memory — not just chat history, but structured user profiles and domain knowledge. CozyMemory unifies three best-of-breed open-source engines into a single, production-ready platform.',
    techStack: 'Tech Stack',
    license: 'License',
    licenseText: 'CozyMemory is open-source software licensed under AGPL-3.0-or-later.',
    contributing: 'Contributing',
    contributingText: 'We welcome contributions! Check out our GitHub repository to get started.',
  },
  footer: {
    product: 'Product',
    resources: 'Resources',
    community: 'Community',
    madeWith: 'Made with',
  },
  lang: {
    switchTo: '中文',
  },
} as const;
```

- [ ] **Step 2: Create ZH translation strings**

Create `website/src/i18n/zh.ts`:

```typescript
export const zh = {
  nav: {
    home: '首页',
    features: '功能',
    blog: '博客',
    about: '关于',
    docs: '文档',
  },
  hero: {
    title: '统一 AI 记忆服务平台',
    subtitle: '单一 API 整合三大记忆引擎 —— 对话记忆、用户画像、知识图谱。自托管、开源、生产就绪。',
    getStarted: '快速开始',
    apiDocs: 'API 文档',
  },
  engines: {
    mem0: {
      name: 'Mem0 · 对话记忆',
      tagline: '从对话中自动提取事实',
      items: ['语义搜索记忆', '事实去重与合并', '完整对话历史'],
    },
    memobase: {
      name: 'Memobase · 用户画像',
      tagline: '结构化存储用户偏好',
      items: ['生成 LLM 上下文提示词', '多维度画像', '基于主题的组织'],
    },
    cognee: {
      name: 'Cognee · 知识图谱',
      tagline: '文档转化为实体关系图',
      items: ['图检索与补全', '多种搜索模式', 'RAG 增强'],
    },
  },
  stats: {
    engines: '3 大引擎',
    endpoints: '50+ API 端点',
    tests: '524 单元测试',
    protocols: 'REST + gRPC',
  },
  why: {
    title: '为什么选择 CozyMemory？',
    unified: {
      title: '统一 API',
      description: '一个接口聚合三种记忆类型，无需分别对接每个引擎。',
    },
    multiTenant: {
      title: '多租户就绪',
      description: 'Organization → App → Key 数据隔离，SaaS 级 JWT + API Key 鉴权。',
    },
    selfHosted: {
      title: '自托管',
      description: 'Docker Compose 一键部署 15 个容器，数据完全可控。',
    },
    observable: {
      title: '可观测',
      description: '内置 Prometheus + Grafana 监控，开箱即用的告警规则。',
    },
  },
  cta: {
    starOnGithub: '在 GitHub 上点星',
    readTheDocs: '阅读文档',
  },
  features: {
    title: '三大引擎，一个 API',
    subtitle: '深入了解每个记忆引擎及其协同方式。',
    unifiedContext: {
      title: '统一上下文',
      description: '一次 /context 调用融合三个引擎的结果，返回 LLM 就绪的响应。',
    },
  },
  about: {
    title: '关于 CozyMemory',
    vision:
      'AI 应用需要记忆 —— 不仅是聊天历史，还有结构化的用户画像和领域知识。CozyMemory 将三个最优秀的开源引擎统一为一个生产就绪的平台。',
    techStack: '技术栈',
    license: '开源协议',
    licenseText: 'CozyMemory 是开源软件，采用 AGPL-3.0-or-later 协议。',
    contributing: '参与贡献',
    contributingText: '欢迎贡献！请访问我们的 GitHub 仓库开始参与。',
  },
  footer: {
    product: '产品',
    resources: '资源',
    community: '社区',
    madeWith: '使用',
  },
  lang: {
    switchTo: 'English',
  },
} as const;
```

- [ ] **Step 3: Create translation helper**

Create `website/src/i18n/index.ts`:

```typescript
import { en } from './en';
import { zh } from './zh';

const translations = { en, zh } as const;

export type Locale = keyof typeof translations;

export function useTranslations(locale: Locale = 'en') {
  return translations[locale];
}

export function getLocaleFromUrl(url: URL): Locale {
  const [, locale] = url.pathname.split('/');
  if (locale === 'zh') return 'zh';
  return 'en';
}

export function getLocalizedPath(path: string, locale: Locale): string {
  if (locale === 'en') return path;
  return `/${locale}${path}`;
}
```

- [ ] **Step 4: Verify build**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/website
npm run build
```

Expected: Build succeeds (new files are not yet imported, but syntax must be valid).

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add website/src/i18n/
git commit -m "feat(website): add i18n translation system with EN/ZH strings"
```

---

### Task 4: Build Home Page (EN)

**Files:**
- Modify: `website/src/pages/index.astro` (replace AstroWind default)
- Modify: `website/src/navigation.ts`

- [ ] **Step 1: Copy product screenshots to website assets**

```bash
cp /home/ubuntu/CozyProjects/CozyMemory/dark_dash.png /home/ubuntu/CozyProjects/CozyMemory/website/src/assets/images/screenshot-dashboard.png
cp /home/ubuntu/CozyProjects/CozyMemory/dark_kb.png /home/ubuntu/CozyProjects/CozyMemory/website/src/assets/images/screenshot-knowledge.png
cp /home/ubuntu/CozyProjects/CozyMemory/dark_pg.png /home/ubuntu/CozyProjects/CozyMemory/website/src/assets/images/screenshot-playground.png
```

- [ ] **Step 2: Update navigation.ts for CozyMemory**

Replace the entire content of `website/src/navigation.ts`:

```typescript
import { getPermalink, getBlogPermalink } from './utils/permalinks';

export const headerData = {
  links: [
    { text: 'Home', href: getPermalink('/') },
    { text: 'Features', href: getPermalink('/features') },
    { text: 'Blog', href: getBlogPermalink() },
    { text: 'About', href: getPermalink('/about') },
    {
      text: 'Docs',
      links: [
        { text: 'API Reference', href: 'https://github.com/zinohome/CozyMemory/blob/main/docs/api-reference.md' },
        { text: 'Architecture', href: 'https://github.com/zinohome/CozyMemory/blob/main/docs/architecture.md' },
        { text: 'Deployment', href: 'https://github.com/zinohome/CozyMemory/blob/main/docs/deployment.md' },
        { text: 'SDK & Clients', href: 'https://github.com/zinohome/CozyMemory/blob/main/docs/sdk-clients.md' },
      ],
    },
  ],
  actions: [
    { text: 'GitHub', href: 'https://github.com/zinohome/CozyMemory', target: '_blank' },
  ],
};

export const footerData = {
  links: [
    {
      title: 'Product',
      links: [
        { text: 'Features', href: getPermalink('/features') },
        { text: 'Blog', href: getBlogPermalink() },
        { text: 'Changelog', href: 'https://github.com/zinohome/CozyMemory/blob/main/CHANGELOG.md' },
      ],
    },
    {
      title: 'Resources',
      links: [
        { text: 'Documentation', href: 'https://github.com/zinohome/CozyMemory/tree/main/docs' },
        { text: 'Python SDK', href: 'https://github.com/zinohome/CozyMemory/tree/main/sdks/python' },
        { text: 'JS/TS SDK', href: 'https://github.com/zinohome/CozyMemory/tree/main/sdks/js' },
      ],
    },
    {
      title: 'Community',
      links: [
        { text: 'GitHub', href: 'https://github.com/zinohome/CozyMemory' },
        { text: 'Issues', href: 'https://github.com/zinohome/CozyMemory/issues' },
        { text: 'Discussions', href: 'https://github.com/zinohome/CozyMemory/discussions' },
      ],
    },
  ],
  secondaryLinks: [
    { text: 'AGPL-3.0 License', href: 'https://github.com/zinohome/CozyMemory/blob/main/LICENSE' },
  ],
  socialLinks: [
    { ariaLabel: 'GitHub', icon: 'tabler:brand-github', href: 'https://github.com/zinohome/CozyMemory' },
  ],
  footNote: 'Built with <a class="text-blue-600 underline dark:text-muted" href="https://astro.build/">Astro</a> + <a class="text-blue-600 underline dark:text-muted" href="https://github.com/onwidget/astrowind">AstroWind</a>. Licensed under AGPL-3.0.',
};
```

- [ ] **Step 3: Replace index.astro with CozyMemory home page**

Replace `website/src/pages/index.astro` with:

```astro
---
import Layout from '~/layouts/PageLayout.astro';
import Hero from '~/components/widgets/Hero.astro';
import Features from '~/components/widgets/Features.astro';
import Stats from '~/components/widgets/Stats.astro';
import Content from '~/components/widgets/Content.astro';
import CallToAction from '~/components/widgets/CallToAction.astro';
import Note from '~/components/widgets/Note.astro';

import { useTranslations } from '~/i18n';
const t = useTranslations('en');

const metadata = {
  title: 'CozyMemory — Unified AI Memory for Every LLM App',
  description: t.hero.subtitle,
};
---

<Layout metadata={metadata}>
  <Hero
    actions={[
      { variant: 'primary', text: t.hero.getStarted, href: 'https://github.com/zinohome/CozyMemory#快速开始', target: '_blank', icon: 'tabler:rocket' },
      { text: t.hero.apiDocs, href: 'https://github.com/zinohome/CozyMemory/blob/main/docs/api-reference.md', target: '_blank', icon: 'tabler:book' },
    ]}
  >
    <Fragment slot="title">
      {t.hero.title}
    </Fragment>
    <Fragment slot="subtitle">
      {t.hero.subtitle}
    </Fragment>
  </Hero>

  <Features
    id="engines"
    title="Three Engines, One API"
    subtitle="CozyMemory integrates three best-of-breed memory engines into a unified platform."
    items={[
      { title: t.engines.mem0.name, description: t.engines.mem0.items.join('. ') + '.', icon: 'tabler:brain' },
      { title: t.engines.memobase.name, description: t.engines.memobase.items.join('. ') + '.', icon: 'tabler:user-circle' },
      { title: t.engines.cognee.name, description: t.engines.cognee.items.join('. ') + '.', icon: 'tabler:topology-star-3' },
    ]}
  />

  <Note
    title="Quick Integration"
  >
    <Fragment slot="description">
      <pre class="text-sm bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-x-auto"><code>{`from cozymemory import CozyMemoryClient

with CozyMemoryClient(api_key="cozy_xxx") as c:
    c.conversations.add("alice", [{"role": "user", "content": "I love hiking"}])
    ctx = c.context.get_unified("alice", query="outdoor activity")`}</code></pre>
    </Fragment>
  </Note>

  <Stats
    title="Built for Production"
    stats={[
      { title: t.stats.engines, amount: '3' },
      { title: t.stats.endpoints, amount: '50+' },
      { title: t.stats.tests, amount: '524' },
      { title: t.stats.protocols, amount: 'REST+gRPC' },
    ]}
  />

  <Features
    id="why"
    title={t.why.title}
    items={[
      { title: t.why.unified.title, description: t.why.unified.description, icon: 'tabler:plug-connected' },
      { title: t.why.multiTenant.title, description: t.why.multiTenant.description, icon: 'tabler:building' },
      { title: t.why.selfHosted.title, description: t.why.selfHosted.description, icon: 'tabler:server' },
      { title: t.why.observable.title, description: t.why.observable.description, icon: 'tabler:chart-line' },
    ]}
  />

  <Content
    title="Management Dashboard"
    subtitle="Full-featured Next.js 16 admin UI with dark mode, i18n, and interactive knowledge graph visualization."
    isReversed
    image={{ src: '~/assets/images/screenshot-dashboard.png', alt: 'CozyMemory Dashboard' }}
  >
    <Fragment slot="content">
      <ul class="list-disc pl-4 space-y-2">
        <li>Developer Dashboard: manage Apps, API Keys, External Users</li>
        <li>Operator Console: cross-org monitoring, backup/restore</li>
        <li>Playground: SSE streaming chat with memory context</li>
        <li>Knowledge Graph: interactive force-directed visualization</li>
      </ul>
    </Fragment>
  </Content>

  <CallToAction
    actions={[
      { variant: 'primary', text: t.cta.starOnGithub, href: 'https://github.com/zinohome/CozyMemory', target: '_blank', icon: 'tabler:brand-github' },
      { text: t.cta.readTheDocs, href: 'https://github.com/zinohome/CozyMemory/tree/main/docs', target: '_blank', icon: 'tabler:book' },
    ]}
    title="Ready to add memory to your AI app?"
    subtitle="Get started in minutes with Docker Compose. Free, open-source, self-hosted."
  />
</Layout>
```

- [ ] **Step 4: Verify build and dev server**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/website
npm run build
```

Expected: Build succeeds. Start dev server and visually verify the home page renders at `http://localhost:4321`.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add website/src/pages/index.astro website/src/navigation.ts website/src/assets/images/
git commit -m "feat(website): build EN home page with hero, features, stats, CTA"
```

---

### Task 5: Build Features Page (EN)

**Files:**
- Create: `website/src/pages/features.astro`

- [ ] **Step 1: Create features.astro**

Create `website/src/pages/features.astro`:

```astro
---
import Layout from '~/layouts/PageLayout.astro';
import Content from '~/components/widgets/Content.astro';
import Features from '~/components/widgets/Features.astro';
import Hero from '~/components/widgets/Hero.astro';
import Note from '~/components/widgets/Note.astro';

import { useTranslations } from '~/i18n';
const t = useTranslations('en');

const metadata = {
  title: 'Features — CozyMemory',
  description: t.features.subtitle,
};
---

<Layout metadata={metadata}>
  <Hero>
    <Fragment slot="title">{t.features.title}</Fragment>
    <Fragment slot="subtitle">{t.features.subtitle}</Fragment>
  </Hero>

  <Content
    id="mem0"
    title={t.engines.mem0.name}
    subtitle={t.engines.mem0.tagline}
    image={{ src: '~/assets/images/screenshot-dashboard.png', alt: 'Conversation Memory' }}
  >
    <Fragment slot="content">
      <ul class="list-disc pl-4 space-y-2">
        <li>Automatically extract facts from multi-turn conversations</li>
        <li>Semantic search across all stored memories</li>
        <li>Fact deduplication and merge on new information</li>
        <li>Full CRUD: list, get, search, delete per user</li>
      </ul>
      <h4 class="mt-4 font-bold">API Example</h4>
      <pre class="text-sm bg-gray-100 dark:bg-gray-800 p-3 rounded-lg mt-2 overflow-x-auto"><code>{`POST /api/v1/conversations
{"user_id": "alice", "messages": [{"role": "user", "content": "I love hiking"}]}

POST /api/v1/conversations/search
{"user_id": "alice", "query": "outdoor activity"}`}</code></pre>
    </Fragment>
  </Content>

  <Content
    id="memobase"
    isReversed
    title={t.engines.memobase.name}
    subtitle={t.engines.memobase.tagline}
    image={{ src: '~/assets/images/screenshot-playground.png', alt: 'User Profiles' }}
  >
    <Fragment slot="content">
      <ul class="list-disc pl-4 space-y-2">
        <li>Structured storage of user preferences, background, interests</li>
        <li>Generate LLM-ready context prompts from profiles</li>
        <li>Multi-dimension topic management (topic/sub_topic/content)</li>
        <li>Buffer + flush workflow for batch processing</li>
      </ul>
      <h4 class="mt-4 font-bold">API Example</h4>
      <pre class="text-sm bg-gray-100 dark:bg-gray-800 p-3 rounded-lg mt-2 overflow-x-auto"><code>{`POST /api/v1/profiles/insert
{"user_id": "<uuid>", "messages": [...], "sync": true}

POST /api/v1/profiles/<user_id>/context
→ {"context": "User is an engineer who loves hiking..."}`}</code></pre>
    </Fragment>
  </Content>

  <Content
    id="cognee"
    title={t.engines.cognee.name}
    subtitle={t.engines.cognee.tagline}
    image={{ src: '~/assets/images/screenshot-knowledge.png', alt: 'Knowledge Graph' }}
  >
    <Fragment slot="content">
      <ul class="list-disc pl-4 space-y-2">
        <li>Ingest documents and build entity-relation knowledge graphs</li>
        <li>Multiple search modes: CHUNKS, SUMMARIES, GRAPH_COMPLETION</li>
        <li>Two-step workflow: add documents → cognify → search</li>
        <li>Dataset management for organizing knowledge domains</li>
      </ul>
      <h4 class="mt-4 font-bold">API Example</h4>
      <pre class="text-sm bg-gray-100 dark:bg-gray-800 p-3 rounded-lg mt-2 overflow-x-auto"><code>{`POST /api/v1/knowledge/add
{"data": "document text...", "dataset": "my-dataset"}

POST /api/v1/knowledge/search
{"query": "key concept", "search_type": "GRAPH_COMPLETION"}`}</code></pre>
    </Fragment>
  </Content>

  <Note title={t.features.unifiedContext.title}>
    <Fragment slot="description">
      <p class="mb-3">{t.features.unifiedContext.description}</p>
      <pre class="text-sm bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto"><code>{`POST /api/v1/context
{"user_id": "alice", "query": "outdoor activity"}

→ {
    "memories": [...],    // from Mem0
    "profile": {...},     // from Memobase
    "knowledge": [...]    // from Cognee
  }`}</code></pre>
    </Fragment>
  </Note>
</Layout>
```

- [ ] **Step 2: Verify build**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/website
npm run build
```

Expected: Build succeeds. Verify `/features` renders in dev server.

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add website/src/pages/features.astro
git commit -m "feat(website): add EN features page with three engine deep dives"
```

---

### Task 6: Build About Page (EN)

**Files:**
- Modify: `website/src/pages/about.astro` (replace AstroWind default)

- [ ] **Step 1: Replace about.astro**

Replace `website/src/pages/about.astro` with:

```astro
---
import Layout from '~/layouts/PageLayout.astro';
import Hero from '~/components/widgets/Hero.astro';
import Content from '~/components/widgets/Content.astro';
import Features from '~/components/widgets/Features.astro';
import CallToAction from '~/components/widgets/CallToAction.astro';

import { useTranslations } from '~/i18n';
const t = useTranslations('en');

const metadata = {
  title: 'About — CozyMemory',
  description: t.about.vision,
};
---

<Layout metadata={metadata}>
  <Hero>
    <Fragment slot="title">{t.about.title}</Fragment>
    <Fragment slot="subtitle">{t.about.vision}</Fragment>
  </Hero>

  <Features
    title={t.about.techStack}
    items={[
      { title: 'Python 3.11+', description: 'FastAPI async REST API + gRPC server', icon: 'tabler:brand-python' },
      { title: 'Next.js 16', description: 'React 19 admin UI with App Router', icon: 'tabler:brand-nextjs' },
      { title: 'Docker Compose', description: '15 containers, one-click deployment', icon: 'tabler:brand-docker' },
      { title: 'PostgreSQL + pgvector', description: 'Primary database with vector extension', icon: 'tabler:database' },
      { title: 'Prometheus + Grafana', description: 'Built-in monitoring and alerting', icon: 'tabler:chart-line' },
      { title: 'gRPC + REST', description: 'Dual protocol support for all endpoints', icon: 'tabler:api' },
    ]}
  />

  <Content title={t.about.license}>
    <Fragment slot="content">
      <p class="mb-4">{t.about.licenseText}</p>
      <p>{t.about.contributingText}</p>
    </Fragment>
  </Content>

  <CallToAction
    title={t.about.contributing}
    actions={[
      { variant: 'primary', text: 'View on GitHub', href: 'https://github.com/zinohome/CozyMemory', target: '_blank', icon: 'tabler:brand-github' },
      { text: 'Report an Issue', href: 'https://github.com/zinohome/CozyMemory/issues', target: '_blank', icon: 'tabler:bug' },
    ]}
  />
</Layout>
```

- [ ] **Step 2: Verify build**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/website
npm run build
```

Expected: Build succeeds. Verify `/about` renders in dev server.

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add website/src/pages/about.astro
git commit -m "feat(website): add EN about page with tech stack and license info"
```

---

### Task 7: Add Blog with Initial Post

**Files:**
- Create: `website/src/data/post/introducing-cozymemory-v020.mdx`
- Create: `website/src/data/post/cozymemory-v020-发布.mdx`

- [ ] **Step 1: Create EN blog post**

Create `website/src/data/post/introducing-cozymemory-v020.mdx`:

```mdx
---
publishDate: 2026-04-25T00:00:00Z
title: 'Introducing CozyMemory v0.2.0'
excerpt: 'CozyMemory v0.2.0 brings multi-tenant SaaS architecture, dual-role authentication, and a full-featured management UI.'
image: ~/assets/images/screenshot-dashboard.png
category: Release
tags:
  - release
  - v0.2.0
  - multi-tenant
---

## What is CozyMemory?

CozyMemory is a unified AI memory service platform that integrates three memory engines into a single REST + gRPC API:

- **Mem0** — Conversation memory: auto-extract facts, semantic search
- **Memobase** — User profiles: structured preferences, LLM context generation
- **Cognee** — Knowledge graph: document ingestion, graph retrieval

## What's New in v0.2.0

### Multi-tenant SaaS Architecture

- **Account hierarchy**: Organization → Developer → App → API Key
- **Dual-role model**: Developer (JWT login) + Operator (bootstrap key)
- **Data isolation**: `uuid5(app_namespace, external_user_id)` transparent mapping
- **Per-App API usage tracking** with sliding window aggregation

### Developer Dashboard UI

Built with Next.js 16 and React 19:

- App management with API Key CRUD
- Memory, Profiles, Knowledge workspaces per App
- Interactive knowledge graph visualization
- SSE streaming Playground with session persistence
- i18n (EN/ZH) and dark mode

### Production Ready

- 524 unit tests + 69 integration tests
- Prometheus + Grafana monitoring with alert rules
- Docker Compose deployment with 15 containers
- Caddy reverse proxy with gRPC TLS termination

## Get Started

```bash
git clone https://github.com/zinohome/CozyMemory.git
cd CozyMemory
cp base_runtime/.env.example base_runtime/.env
sudo ./base_runtime/build.sh all
sudo docker compose -f base_runtime/docker-compose.1panel.yml up -d
```

Visit the [GitHub repository](https://github.com/zinohome/CozyMemory) for full documentation.
```

- [ ] **Step 2: Create ZH blog post**

Create `website/src/data/post/cozymemory-v020-发布.mdx`:

```mdx
---
publishDate: 2026-04-25T00:00:00Z
title: 'CozyMemory v0.2.0 发布'
excerpt: 'CozyMemory v0.2.0 带来多租户 SaaS 架构、双角色鉴权和全功能管理 UI。'
image: ~/assets/images/screenshot-dashboard.png
category: Release
tags:
  - release
  - v0.2.0
  - 多租户
---

## CozyMemory 是什么？

CozyMemory 是一个统一 AI 记忆服务平台，将三大记忆引擎整合为单一 REST + gRPC API：

- **Mem0** — 对话记忆：自动提取事实，语义搜索
- **Memobase** — 用户画像：结构化偏好存储，LLM 上下文生成
- **Cognee** — 知识图谱：文档摄入，图检索

## v0.2.0 新增内容

### 多租户 SaaS 架构

- **账号体系**：Organization → Developer → App → API Key
- **双角色模型**：Developer（JWT 登录）+ Operator（bootstrap key）
- **数据隔离**：`uuid5(app_namespace, external_user_id)` 透明映射
- **per-App API 用量统计**，滑动窗口聚合

### Developer Dashboard UI

基于 Next.js 16 和 React 19 构建：

- App 管理、API Key CRUD
- 每个 App 独立的 Memory / Profiles / Knowledge 工作台
- 交互式知识图谱力导向图可视化
- SSE 流式 Playground，会话持久化
- 中英双语 + 暗色模式

### 生产就绪

- 524 单元测试 + 69 集成测试
- Prometheus + Grafana 监控与告警
- Docker Compose 一键部署 15 个容器
- Caddy 反向代理 + gRPC TLS 终结

## 快速开始

```bash
git clone https://github.com/zinohome/CozyMemory.git
cd CozyMemory
cp base_runtime/.env.example base_runtime/.env
sudo ./base_runtime/build.sh all
sudo docker compose -f base_runtime/docker-compose.1panel.yml up -d
```

详细文档请访问 [GitHub 仓库](https://github.com/zinohome/CozyMemory)。
```

- [ ] **Step 3: Verify build**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/website
npm run build
```

Expected: Build succeeds. Blog posts appear at `/introducing-cozymemory-v020` and `/cozymemory-v020-发布` in dev server. Blog list at `/blog`.

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add website/src/data/post/
git commit -m "feat(website): add initial blog posts (EN/ZH) for v0.2.0 release"
```

---

### Task 8: Create Chinese Pages

**Files:**
- Create: `website/src/pages/zh/index.astro`
- Create: `website/src/pages/zh/features.astro`
- Create: `website/src/pages/zh/about.astro`

- [ ] **Step 1: Create ZH home page**

Create `website/src/pages/zh/index.astro`:

```astro
---
import Layout from '~/layouts/PageLayout.astro';
import Hero from '~/components/widgets/Hero.astro';
import Features from '~/components/widgets/Features.astro';
import Stats from '~/components/widgets/Stats.astro';
import Content from '~/components/widgets/Content.astro';
import CallToAction from '~/components/widgets/CallToAction.astro';
import Note from '~/components/widgets/Note.astro';

import { useTranslations } from '~/i18n';
const t = useTranslations('zh');

const metadata = {
  title: 'CozyMemory — 统一 AI 记忆服务平台',
  description: t.hero.subtitle,
};
---

<Layout metadata={metadata}>
  <Hero
    actions={[
      { variant: 'primary', text: t.hero.getStarted, href: 'https://github.com/zinohome/CozyMemory#快速开始', target: '_blank', icon: 'tabler:rocket' },
      { text: t.hero.apiDocs, href: 'https://github.com/zinohome/CozyMemory/blob/main/docs/api-reference.md', target: '_blank', icon: 'tabler:book' },
    ]}
  >
    <Fragment slot="title">
      {t.hero.title}
    </Fragment>
    <Fragment slot="subtitle">
      {t.hero.subtitle}
    </Fragment>
  </Hero>

  <Features
    id="engines"
    title="三大引擎，一个 API"
    subtitle="CozyMemory 将三个最优秀的记忆引擎整合为统一平台。"
    items={[
      { title: t.engines.mem0.name, description: t.engines.mem0.items.join('。') + '。', icon: 'tabler:brain' },
      { title: t.engines.memobase.name, description: t.engines.memobase.items.join('。') + '。', icon: 'tabler:user-circle' },
      { title: t.engines.cognee.name, description: t.engines.cognee.items.join('。') + '。', icon: 'tabler:topology-star-3' },
    ]}
  />

  <Note title="快速集成">
    <Fragment slot="description">
      <pre class="text-sm bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-x-auto"><code>{`from cozymemory import CozyMemoryClient

with CozyMemoryClient(api_key="cozy_xxx") as c:
    c.conversations.add("alice", [{"role": "user", "content": "I love hiking"}])
    ctx = c.context.get_unified("alice", query="outdoor activity")`}</code></pre>
    </Fragment>
  </Note>

  <Stats
    title="为生产环境而生"
    stats={[
      { title: t.stats.engines, amount: '3' },
      { title: t.stats.endpoints, amount: '50+' },
      { title: t.stats.tests, amount: '524' },
      { title: t.stats.protocols, amount: 'REST+gRPC' },
    ]}
  />

  <Features
    id="why"
    title={t.why.title}
    items={[
      { title: t.why.unified.title, description: t.why.unified.description, icon: 'tabler:plug-connected' },
      { title: t.why.multiTenant.title, description: t.why.multiTenant.description, icon: 'tabler:building' },
      { title: t.why.selfHosted.title, description: t.why.selfHosted.description, icon: 'tabler:server' },
      { title: t.why.observable.title, description: t.why.observable.description, icon: 'tabler:chart-line' },
    ]}
  />

  <Content
    title="管理仪表盘"
    subtitle="全功能 Next.js 16 管理 UI，支持暗色模式、中英双语和交互式知识图谱可视化。"
    isReversed
    image={{ src: '~/assets/images/screenshot-dashboard.png', alt: 'CozyMemory 仪表盘' }}
  >
    <Fragment slot="content">
      <ul class="list-disc pl-4 space-y-2">
        <li>Developer 仪表盘：管理 App、API Key、外部用户</li>
        <li>Operator 控制台：跨组织监控、备份/恢复</li>
        <li>Playground：SSE 流式聊天，带记忆上下文</li>
        <li>知识图谱：交互式力导向图可视化</li>
      </ul>
    </Fragment>
  </Content>

  <CallToAction
    actions={[
      { variant: 'primary', text: t.cta.starOnGithub, href: 'https://github.com/zinohome/CozyMemory', target: '_blank', icon: 'tabler:brand-github' },
      { text: t.cta.readTheDocs, href: 'https://github.com/zinohome/CozyMemory/tree/main/docs', target: '_blank', icon: 'tabler:book' },
    ]}
    title="准备好为你的 AI 应用添加记忆了吗？"
    subtitle="Docker Compose 几分钟即可上手。免费、开源、自托管。"
  />
</Layout>
```

- [ ] **Step 2: Create ZH features page**

Create `website/src/pages/zh/features.astro`:

```astro
---
import Layout from '~/layouts/PageLayout.astro';
import Content from '~/components/widgets/Content.astro';
import Hero from '~/components/widgets/Hero.astro';
import Note from '~/components/widgets/Note.astro';

import { useTranslations } from '~/i18n';
const t = useTranslations('zh');

const metadata = {
  title: '功能 — CozyMemory',
  description: t.features.subtitle,
};
---

<Layout metadata={metadata}>
  <Hero>
    <Fragment slot="title">{t.features.title}</Fragment>
    <Fragment slot="subtitle">{t.features.subtitle}</Fragment>
  </Hero>

  <Content
    id="mem0"
    title={t.engines.mem0.name}
    subtitle={t.engines.mem0.tagline}
    image={{ src: '~/assets/images/screenshot-dashboard.png', alt: '对话记忆' }}
  >
    <Fragment slot="content">
      <ul class="list-disc pl-4 space-y-2">
        <li>从多轮对话中自动提取事实</li>
        <li>跨所有存储记忆的语义搜索</li>
        <li>新信息到达时自动去重与合并</li>
        <li>完整 CRUD：按用户列出、获取、搜索、删除</li>
      </ul>
      <h4 class="mt-4 font-bold">API 示例</h4>
      <pre class="text-sm bg-gray-100 dark:bg-gray-800 p-3 rounded-lg mt-2 overflow-x-auto"><code>{`POST /api/v1/conversations
{"user_id": "alice", "messages": [{"role": "user", "content": "I love hiking"}]}

POST /api/v1/conversations/search
{"user_id": "alice", "query": "outdoor activity"}`}</code></pre>
    </Fragment>
  </Content>

  <Content
    id="memobase"
    isReversed
    title={t.engines.memobase.name}
    subtitle={t.engines.memobase.tagline}
    image={{ src: '~/assets/images/screenshot-playground.png', alt: '用户画像' }}
  >
    <Fragment slot="content">
      <ul class="list-disc pl-4 space-y-2">
        <li>结构化存储用户偏好、背景、兴趣</li>
        <li>从画像生成 LLM 就绪的上下文提示词</li>
        <li>多维度主题管理（topic/sub_topic/content）</li>
        <li>Buffer + flush 批量处理工作流</li>
      </ul>
      <h4 class="mt-4 font-bold">API 示例</h4>
      <pre class="text-sm bg-gray-100 dark:bg-gray-800 p-3 rounded-lg mt-2 overflow-x-auto"><code>{`POST /api/v1/profiles/insert
{"user_id": "<uuid>", "messages": [...], "sync": true}

POST /api/v1/profiles/<user_id>/context
→ {"context": "用户是一名工程师，喜欢徒步..."}`}</code></pre>
    </Fragment>
  </Content>

  <Content
    id="cognee"
    title={t.engines.cognee.name}
    subtitle={t.engines.cognee.tagline}
    image={{ src: '~/assets/images/screenshot-knowledge.png', alt: '知识图谱' }}
  >
    <Fragment slot="content">
      <ul class="list-disc pl-4 space-y-2">
        <li>摄入文档并构建实体关系知识图谱</li>
        <li>多种搜索模式：CHUNKS、SUMMARIES、GRAPH_COMPLETION</li>
        <li>两步工作流：添加文档 → cognify → 搜索</li>
        <li>数据集管理，组织不同知识领域</li>
      </ul>
      <h4 class="mt-4 font-bold">API 示例</h4>
      <pre class="text-sm bg-gray-100 dark:bg-gray-800 p-3 rounded-lg mt-2 overflow-x-auto"><code>{`POST /api/v1/knowledge/add
{"data": "文档内容...", "dataset": "my-dataset"}

POST /api/v1/knowledge/search
{"query": "关键概念", "search_type": "GRAPH_COMPLETION"}`}</code></pre>
    </Fragment>
  </Content>

  <Note title={t.features.unifiedContext.title}>
    <Fragment slot="description">
      <p class="mb-3">{t.features.unifiedContext.description}</p>
      <pre class="text-sm bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto"><code>{`POST /api/v1/context
{"user_id": "alice", "query": "outdoor activity"}

→ {
    "memories": [...],    // 来自 Mem0
    "profile": {...},     // 来自 Memobase
    "knowledge": [...]    // 来自 Cognee
  }`}</code></pre>
    </Fragment>
  </Note>
</Layout>
```

- [ ] **Step 3: Create ZH about page**

Create `website/src/pages/zh/about.astro`:

```astro
---
import Layout from '~/layouts/PageLayout.astro';
import Hero from '~/components/widgets/Hero.astro';
import Content from '~/components/widgets/Content.astro';
import Features from '~/components/widgets/Features.astro';
import CallToAction from '~/components/widgets/CallToAction.astro';

import { useTranslations } from '~/i18n';
const t = useTranslations('zh');

const metadata = {
  title: '关于 — CozyMemory',
  description: t.about.vision,
};
---

<Layout metadata={metadata}>
  <Hero>
    <Fragment slot="title">{t.about.title}</Fragment>
    <Fragment slot="subtitle">{t.about.vision}</Fragment>
  </Hero>

  <Features
    title={t.about.techStack}
    items={[
      { title: 'Python 3.11+', description: 'FastAPI 异步 REST API + gRPC 服务', icon: 'tabler:brand-python' },
      { title: 'Next.js 16', description: 'React 19 管理 UI，App Router', icon: 'tabler:brand-nextjs' },
      { title: 'Docker Compose', description: '15 个容器，一键部署', icon: 'tabler:brand-docker' },
      { title: 'PostgreSQL + pgvector', description: '主数据库 + 向量扩展', icon: 'tabler:database' },
      { title: 'Prometheus + Grafana', description: '内置监控与告警', icon: 'tabler:chart-line' },
      { title: 'gRPC + REST', description: '双协议支持所有端点', icon: 'tabler:api' },
    ]}
  />

  <Content title={t.about.license}>
    <Fragment slot="content">
      <p class="mb-4">{t.about.licenseText}</p>
      <p>{t.about.contributingText}</p>
    </Fragment>
  </Content>

  <CallToAction
    title={t.about.contributing}
    actions={[
      { variant: 'primary', text: '访问 GitHub', href: 'https://github.com/zinohome/CozyMemory', target: '_blank', icon: 'tabler:brand-github' },
      { text: '提交 Issue', href: 'https://github.com/zinohome/CozyMemory/issues', target: '_blank', icon: 'tabler:bug' },
    ]}
  />
</Layout>
```

- [ ] **Step 4: Verify build**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/website
npm run build
```

Expected: Build succeeds. ZH pages render at `/zh/`, `/zh/features`, `/zh/about` in dev server.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add website/src/pages/zh/
git commit -m "feat(website): add Chinese (ZH) versions of home, features, about pages"
```

---

### Task 9: Clean Up Unused Demo Pages

**Files:**
- Delete: `website/src/pages/homes/` (entire directory)
- Delete: `website/src/pages/landing/` (entire directory)
- Delete: `website/src/pages/pricing.astro`
- Delete: `website/src/pages/services.astro`
- Delete: `website/src/pages/contact.astro`

- [ ] **Step 1: Remove unused AstroWind demo pages**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/website
rm -rf src/pages/homes/ src/pages/landing/
rm -f src/pages/pricing.astro src/pages/services.astro src/pages/contact.astro
```

- [ ] **Step 2: Verify build**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/website
npm run build
```

Expected: Build succeeds with no broken references (deleted pages weren't imported elsewhere).

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add -A website/src/pages/
git commit -m "chore(website): remove unused AstroWind demo pages"
```

---

### Task 10: Add GitHub Actions Deployment Workflow

**Files:**
- Create: `.github/workflows/deploy-website.yml`

- [ ] **Step 1: Create deployment workflow**

Create `.github/workflows/deploy-website.yml`:

```yaml
name: Deploy Website

on:
  push:
    branches: [main]
    paths: ['website/**']
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: 'pages'
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: website/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: website

      - name: Build website
        run: npm run build
        working-directory: website

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: website/dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Final full build verification**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/website
npm run build
```

Expected: Build succeeds. All pages present in `dist/`:
- `dist/index.html` (EN home)
- `dist/features/index.html`
- `dist/about/index.html`
- `dist/blog/index.html`
- `dist/zh/index.html` (ZH home)
- `dist/zh/features/index.html`
- `dist/zh/about/index.html`
- Blog post pages

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add .github/workflows/deploy-website.yml
git commit -m "ci(website): add GitHub Actions workflow for GitHub Pages deployment"
```

- [ ] **Step 4: Push and enable GitHub Pages**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git push origin main
```

Then in GitHub UI: Settings → Pages → Source → "GitHub Actions".

After the workflow runs, the site will be live at `https://zinohome.github.io/CozyMemory/`.
