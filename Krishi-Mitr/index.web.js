/**
 * Web entry point for Krishi Mitr.
 */

import { AppRegistry } from 'react-native';
import App from './App';
import appJson from './app.json';

// react-native-web needs the root chain to be a full-height flex column, or
// every `flex: 1` screen inside it collapses to zero height.
const style = document.createElement('style');
style.type = 'text/css';
style.appendChild(
  document.createTextNode(`
  *, *::before, *::after {
    box-sizing: border-box;
    -webkit-tap-highlight-color: transparent;
  }
  html, body {
    height: 100%;
    width: 100%;
    max-width: 100%;
    margin: 0;
    padding: 0;
    overflow-x: hidden !important;
    overflow-y: auto;
    background-color: #FAF6EE;
    font-family: 'Inter', 'Plus Jakarta Sans', 'Noto Sans Devanagari', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    touch-action: pan-y pinch-zoom;
    scroll-behavior: smooth;
  }
  #root, [dir="auto"], input, button, select, textarea {
    font-family: 'Inter', 'Plus Jakarta Sans', 'Noto Sans Devanagari', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
  }
  #root {
    height: 100%;
    width: 100%;
    max-width: 100%;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    overflow-x: hidden !important;
    background-color: #FAF6EE;
  }
  #root > div {
    height: 100%;
    width: 100%;
    max-width: 100%;
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow-x: hidden !important;
  }

  /* ★ Full-bleed web layout — the app fills the viewport. The navbar and footer provide framing. */

  /* Interactive web element enhancements */
  [role="button"], [data-focusable="true"], button, a {
    cursor: pointer;
    transition: opacity 0.15s ease, transform 0.1s ease;
  }
  [role="button"]:hover, [data-focusable="true"]:hover {
    opacity: 0.94;
  }
  [role="button"]:active {
    transform: scale(0.985);
  }

  /* Lift cards on hover */
  [data-hover="lift"] {
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease !important;
  }
  @media (hover: hover) {
    [data-hover="lift"]:hover {
      transform: translateY(-2px) !important;
      box-shadow: 0 12px 24px rgba(155, 47, 0, 0.08) !important;
      border-color: rgba(194, 65, 12, 0.4) !important;
    }
  }

  /* Focus outlines for keyboard accessibility */
  :focus-visible {
    outline: 2px solid #C2410C;
    outline-offset: 2px;
    border-radius: 4px;
  }

  /* Modern clean scrollbar */
  ::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  ::-webkit-scrollbar-track {
    background: transparent;
  }
  ::-webkit-scrollbar-thumb {
    background: rgba(155, 47, 0, 0.22);
    border-radius: 4px;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: #C2410C;
  }

  /* Selection color matching the brand */
  ::selection {
    background: rgba(194, 65, 12, 0.15);
    color: #1C1C17;
  }
`)
);
document.head.appendChild(style);

const appName = appJson.name || 'KrishiMitr';

AppRegistry.registerComponent(appName, () => App);

AppRegistry.runApplication(appName, {
  initialProps: {},
  rootTag: document.getElementById('root'),
});
