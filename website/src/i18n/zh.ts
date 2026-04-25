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
