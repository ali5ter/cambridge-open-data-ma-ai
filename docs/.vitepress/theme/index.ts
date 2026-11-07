// Custom theme: extend VitePress's default theme and layer our brand on top via
// CSS variables. We override the brand colours and font families in custom.css
// rather than via themeConfig.brandColor/fonts, because those config keys are
// no-ops in this VitePress 1.6 build (the type defs and runtime do not read
// them) -- the CSS-variable route is the version-proof way to recolour.
import type { Theme } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import './custom.css'

export default DefaultTheme satisfies Theme
