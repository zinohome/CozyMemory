# CozyMemory Website

Product landing page for [CozyMemory](https://github.com/zinohome/CozyMemory), built with [Astro](https://astro.build/) and the [AstroWind](https://github.com/onwidget/astrowind) template.

## Development

```bash
cd website
npm install
npm run dev     # http://localhost:4321
npm run build   # Static output to dist/
```

## Deployment

Deployed automatically to GitHub Pages via `.github/workflows/deploy-website.yml` on push to `main` (when `website/**` files change).

## Structure

- `src/pages/` — EN pages at `/`, ZH pages at `/zh/`
- `src/data/post/` — Blog posts (MDX)
- `src/i18n/` — EN/ZH translation strings
- `src/navigation.ts` — Header nav + footer config
