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
    engines: 'Engines',
    endpoints: 'API Endpoints',
    tests: 'Unit Tests',
    protocols: 'Protocols',
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
