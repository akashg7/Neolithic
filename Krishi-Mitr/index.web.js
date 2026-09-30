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
  /* Clean, responsive web layout.
     On mobile: full-bleed native feel.
     On tablet / desktop: polished responsive framing with rich tactile parchment ground,
     subtle borders, refined elevation, and smooth scrolling without disruptive CSS zoom hacks. */
  @media (min-width: 900px) {
    body {
      background: radial-gradient(1400px 800px at 50% 0%, #FFFDF7 0%, #FAF6EE 55%, #EFE8DC 100%);
    }
    #root {
      align-items: center;
      padding: 16px 20px;
    }
    #root > div {
      max-width: 1180px;
      border-radius: 24px;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(28, 28, 23, 0.05), 0 20px 50px -20px rgba(28, 28, 23, 0.18), 0 0 0 1px #DCC9A8;
      background-color: #FAF6EE;
    }
  }

  @media (min-width: 1400px) {
    #root > div {
      max-width: 1260px;
    }
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
`),
);
document.head.appendChild(style);

const appName = appJson.name || 'KrishiMitr';

AppRegistry.registerComponent(appName, () => App);

AppRegistry.runApplication(appName, {
  initialProps: {},
  rootTag: document.getElementById('root'),
});
