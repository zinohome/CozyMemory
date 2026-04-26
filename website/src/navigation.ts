import { getPermalink, getBlogPermalink, getAsset } from './utils/permalinks';
import { useTranslations, type Locale } from './i18n';

const GITHUB_URL = 'https://github.com/zinohome/CozyMemory';
const GITHUB_DOCS = 'https://github.com/zinohome/CozyMemory/tree/main/docs';

export function getHeaderData(locale: Locale = 'en') {
  const t = useTranslations(locale);
  const prefix = locale === 'en' ? '' : '/zh';

  return {
    links: [
      {
        text: t.nav.home,
        href: getPermalink(prefix + '/'),
      },
      {
        text: t.nav.features,
        href: getPermalink(prefix + '/features'),
      },
      {
        text: t.nav.blog,
        href: getBlogPermalink(),
      },
      {
        text: t.nav.about,
        href: getPermalink(prefix + '/about'),
      },
      {
        text: t.nav.docs,
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
}

export function getFooterData(locale: Locale = 'en') {
  const t = useTranslations(locale);
  const prefix = locale === 'en' ? '' : '/zh';

  return {
    links: [
      {
        title: t.footer.product,
        links: [
          { text: t.nav.features, href: getPermalink(prefix + '/features') },
          { text: t.nav.about, href: getPermalink(prefix + '/about') },
          { text: t.nav.blog, href: getBlogPermalink() },
        ],
      },
      {
        title: t.footer.resources,
        links: [
          { text: 'API Reference', href: `${GITHUB_DOCS}/api-reference.md`, target: '_blank' },
          { text: 'Architecture', href: `${GITHUB_DOCS}/architecture.md`, target: '_blank' },
          { text: 'Deployment', href: `${GITHUB_DOCS}/deployment.md`, target: '_blank' },
          { text: 'SDK & Clients', href: `${GITHUB_DOCS}/sdk-clients.md`, target: '_blank' },
        ],
      },
      {
        title: t.footer.community,
        links: [
          { text: 'GitHub', href: GITHUB_URL, target: '_blank' },
          { text: 'Issues', href: `${GITHUB_URL}/issues`, target: '_blank' },
          { text: 'Discussions', href: `${GITHUB_URL}/discussions`, target: '_blank' },
        ],
      },
    ],
    secondaryLinks: [],
    socialLinks: [
      { ariaLabel: 'Github', icon: 'tabler:brand-github', href: GITHUB_URL },
      { ariaLabel: 'RSS', icon: 'tabler:rss', href: getAsset('/rss.xml') },
    ],
    footNote: `
      Built with <a class="text-blue-600 underline dark:text-muted" href="https://astro.build/">Astro</a> &amp;
      <a class="text-blue-600 underline dark:text-muted" href="https://github.com/onwidget/astrowind">AstroWind</a> ·
      Licensed under <a class="text-blue-600 underline dark:text-muted" href="https://github.com/zinohome/CozyMemory/blob/main/LICENSE">AGPL-3.0</a>
    `,
  };
}

// Backwards-compatible exports for non-localized usage
export const headerData = getHeaderData('en');
export const footerData = getFooterData('en');
