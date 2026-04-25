import { getPermalink, getBlogPermalink, getAsset } from './utils/permalinks';

const GITHUB_URL = 'https://github.com/ZhangJun/CozyMemory';
const GITHUB_DOCS = 'https://github.com/ZhangJun/CozyMemory/tree/main/docs';

export const headerData = {
  links: [
    {
      text: 'Home',
      href: getPermalink('/'),
    },
    {
      text: 'Features',
      href: getPermalink('/features'),
    },
    {
      text: 'Blog',
      href: getBlogPermalink(),
    },
    {
      text: 'About',
      href: getPermalink('/about'),
    },
    {
      text: 'Docs',
      links: [
        {
          text: 'API Reference',
          href: `${GITHUB_DOCS}/api-reference.md`,
          target: '_blank',
        },
        {
          text: 'Architecture',
          href: `${GITHUB_DOCS}/architecture.md`,
          target: '_blank',
        },
        {
          text: 'Deployment',
          href: `${GITHUB_DOCS}/deployment.md`,
          target: '_blank',
        },
        {
          text: 'SDK & Clients',
          href: `${GITHUB_DOCS}/sdk-clients.md`,
          target: '_blank',
        },
      ],
    },
  ],
  actions: [
    {
      text: 'GitHub',
      href: GITHUB_URL,
      target: '_blank',
      icon: 'tabler:brand-github',
    },
  ],
};

export const footerData = {
  links: [
    {
      title: 'Product',
      links: [
        { text: 'Features', href: getPermalink('/features') },
        { text: 'About', href: getPermalink('/about') },
        { text: 'Blog', href: getBlogPermalink() },
      ],
    },
    {
      title: 'Resources',
      links: [
        { text: 'API Reference', href: `${GITHUB_DOCS}/api-reference.md`, target: '_blank' },
        { text: 'Architecture', href: `${GITHUB_DOCS}/architecture.md`, target: '_blank' },
        { text: 'Deployment', href: `${GITHUB_DOCS}/deployment.md`, target: '_blank' },
        { text: 'SDK & Clients', href: `${GITHUB_DOCS}/sdk-clients.md`, target: '_blank' },
      ],
    },
    {
      title: 'Community',
      links: [
        { text: 'GitHub', href: GITHUB_URL, target: '_blank' },
        { text: 'Issues', href: `${GITHUB_URL}/issues`, target: '_blank' },
        { text: 'Discussions', href: `${GITHUB_URL}/discussions`, target: '_blank' },
      ],
    },
  ],
  secondaryLinks: [
    { text: 'Terms', href: getPermalink('/terms') },
    { text: 'Privacy Policy', href: getPermalink('/privacy') },
  ],
  socialLinks: [
    { ariaLabel: 'Github', icon: 'tabler:brand-github', href: GITHUB_URL },
    { ariaLabel: 'RSS', icon: 'tabler:rss', href: getAsset('/rss.xml') },
  ],
  footNote: `
    Built with <a class="text-blue-600 underline dark:text-muted" href="https://astro.build/">Astro</a> &amp;
    <a class="text-blue-600 underline dark:text-muted" href="https://github.com/arthelokyo/astrowind">AstroWind</a> ·
    Licensed under <a class="text-blue-600 underline dark:text-muted" href="https://github.com/ZhangJun/CozyMemory/blob/main/LICENSE">AGPL-3.0</a>
  `,
};
