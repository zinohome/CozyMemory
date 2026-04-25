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
