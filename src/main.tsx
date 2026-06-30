import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './app/App';
import './index.css';
import './components/nexusUI.css';
import './admin/nexusAdminUI.css';
import './styles/dashboard-layout-lock.css';
import './styles/client-portal.css';
import './styles/nexus-operating-ui.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
