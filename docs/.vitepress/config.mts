import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
//
// `base` is the GitHub Pages project-site path (the repo name), so the same build
// serves from <user>.github.io/cambridge-open-data-ma-ai/. Links below use the
// `.html` form because clean URLs are disabled: on static hosting that guarantees
// no 404s without a rewrite handler.
export default defineConfig({
  title: 'Cambridge Open Data MA',
  description:
    'An MCP server and a Skill for asking an AI agent to analyse Cambridge MA open data across datasets.',
  base: '/cambridge-open-data-ma-ai/',

  themeConfig: {
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
        ],
      },
      {
        text: 'Reference',
        items: [
          { text: 'Tools and resources', link: '/reference.html' },
        ],
      },
    ],

    search: { provider: 'local' },

    // VitePress 1.6's useEditLink reads only `text` and `pattern` (the legacy
    // repo/docsDir/branch keys are ignored), so the GitHub edit URL is a
    // `:path` template here -- without it the link degrades to a dead span.
    editLink: {
      pattern:
        'https://github.com/ali5ter/cambridge-open-data-ma-ai/edit/main/docs/:path',
      text: 'Edit this page',
    },
    lastUpdated: true,

    socialLinks: [{ icon: 'github', link: 'https://github.com/ali5ter/cambridge-open-data-ma-ai' }],
  },
})
