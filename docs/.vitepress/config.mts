import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
//
// `base` is the GitHub Pages project-site path (the repo name), so the same build
// serves from <user>.github.io/cambridge-open-data-ma-ai/. Links below use the
// `.html` form because clean URLs are disabled: on static hosting that guarantees
// no 404s without a rewrite handler.
const base = '/cambridge-open-data-ma-ai/'

// Brand colour + fonts live in .vitepress/theme/custom.css, NOT in themeConfig.
// In this VitePress 1.6 build the `themeConfig.brandColor` and `fonts` keys are
// no-ops (the type defs and runtime do not read them), so recoloring by CSS
// variable is the version-proof route. custom.css overrides --vp-c-brand-* and
// --vp-font-family-* for both light (:root) and dark (.dark) -- a two-stop green
// (deep emerald on the white light navbar, the logo's exact #34D399 on dark) and
// a Space Grotesk / Inter / IBM Plex Mono pairing: Space Grotesk for titles, Inter
// for body/UI, IBM Plex Mono for code. See .vitepress/theme/index.ts.
const theme = './.vitepress/theme'

export default defineConfig({
  title: 'Cambridge Open Data MA',
  description:
    'An MCP server and a Skill for asking an AI agent to analyse Cambridge MA open data across datasets.',
  base,
  theme,

  // Google Fonts (preconnected for speed) plus the favicon and iOS touch-icon.
  // Public assets live in docs/public/ and are served at `base`, hence the prefixes.
  head: [
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
    [
      'link',
      {
        rel: 'stylesheet',
        href:
          'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap',
      },
    ],
    ['link', { rel: 'icon', type: 'image/svg+xml', href: `${base}favicon.svg` }],
    ['link', { rel: 'apple-touch-icon', href: `${base}apple-touch-icon.png` }],
  ],

  themeConfig: {
    // VitePress prepends `base` to a logo path automatically (unlike `head` link
    // hrefs, which we prefix by hand), so this is base-relative.
    logo: '/logo.svg',

    nav: [
      { text: 'Guide', link: '/getting-started.html' },
      { text: 'Tutorials', link: '/tutorials/01-budget-salary-vs-operating.html' },
      { text: 'Reference', link: '/reference.html' },
      { text: 'GitHub', link: 'https://github.com/ali5ter/cambridge-open-data-ma-ai' },
    ],

    sidebar: [
      {
        text: 'Guide',
        items: [
          { text: 'Getting started', link: '/getting-started.html' },
          { text: 'Install and register', link: '/install.html' },
          { text: 'Concepts', link: '/concepts.html' },
          { text: 'Gotchas', link: '/gotchas.html' },
          { text: 'Configuration', link: '/configuration.html' },
        ],
      },
      {
        text: 'Tutorials',
        items: [
          {
            text: '1 · Salary vs. operating budget',
            link: '/tutorials/01-budget-salary-vs-operating.html',
          },
          {
            text: '2 · Are parking tickets paid?',
            link: '/tutorials/02-parking-ticket-payment-status.html',
          },
          {
            text: '3 · Privately owned public spaces',
            link: '/tutorials/03-privately-owned-public-spaces.html',
          },
          {
            text: '4 · Property profile, 80 Thorndike St',
            link: '/tutorials/04-property-profile-80-thorndike.html',
          },
          {
            text: '5 · First Street Garage / East End House',
            link: '/tutorials/05-first-street-garage-agreements.html',
          },
          {
            text: '6 · Drive the Skill in opencode',
            link: '/tutorials/06-drive-the-skill-in-opencode.html',
          },
        ],
      },
      {
        text: 'Reference',
        items: [{ text: 'Tools and resources', link: '/reference.html' }],
      },
    ],

    search: { provider: 'local' },

    // VitePress 1.6's useEditLink reads only `text` and `pattern` (the legacy
    // repo/docsDir/branch keys are ignored), so the GitHub edit URL is a
    // `:path` template here -- without it the link degrades to a dead span.
    editLink: {
      pattern: 'https://github.com/ali5ter/cambridge-open-data-ma-ai/edit/main/docs/:path',
      text: 'Edit this page',
    },
    lastUpdated: true,

    socialLinks: [
      { icon: 'github', link: 'https://github.com/ali5ter/cambridge-open-data-ma-ai' },
    ],
  },
})
