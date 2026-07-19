import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './app/App';
import { BUILD_METADATA } from './lib/buildMetadata';
import './index.css';
import './components/nexusUI.css';
import './admin/nexusAdminUI.css';
import './styles/dashboard-layout-lock.css';
import './styles/client-portal.css';
import './styles/nexus-operating-ui.css';

declare global {
  interface Window {
    __NEXUS_BUILD_METADATA__?: typeof BUILD_METADATA;
  }
}

window.__NEXUS_BUILD_METADATA__ = BUILD_METADATA;

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
