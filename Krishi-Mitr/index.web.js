/**
 * Web entry point. Mounts the same `App` the phone mounts.
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
  html, body, #root {
    height: 100%;
    width: 100%;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    background-color: #FAF6EE;
  }
  #root > div {
    height: 100%;
    width: 100%;
    display: flex;
    flex-direction: column;
    flex: 1;
  }

  /* ★ Full-bleed web layout — no more phone container.
     The app fills the viewport. The navbar and footer provide framing. */

  /* Smooth scrolling for the whole page */
  * {
    -webkit-tap-highlight-color: transparent;
    box-sizing: border-box;
  }
  html {
    scroll-behavior: smooth;
  }

  /* Interactive element enhancements for web */
  [role="button"], [data-focusable="true"], button, a {
    cursor: pointer;
    transition: opacity 0.15s ease, transform 0.1s ease, background-color 0.15s ease;
  }
  [role="button"]:hover, [data-focusable="true"]:hover {
    opacity: 0.92;
  }
  [role="button"]:active {
    transform: scale(0.985);
  }

  /* Focus outlines for keyboard navigation (accessibility) */
  :focus-visible {
    outline: 2px solid #C2410C;
    outline-offset: 2px;
    border-radius: 4px;
  }

  /* Custom tactile scrollbar */
  ::-webkit-scrollbar {
    width: 7px;
    height: 7px;
  }
  ::-webkit-scrollbar-track {
    background: transparent;
  }
  ::-webkit-scrollbar-thumb {
    background: #DCC9A8;
    border-radius: 6px;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: #C2410C;
  }

  /* Selection color matching the brand */
  ::selection {
    background: rgba(194, 65, 12, 0.15);
    color: #1C1C17;
  }
`),
);
document.head.appendChild(style);

const appName = appJson.name || 'KrishiMitr';

AppRegistry.registerComponent(appName, () => App);

AppRegistry.runApplication(appName, {
  initialProps: {},
  rootTag: document.getElementById('root'),
});
