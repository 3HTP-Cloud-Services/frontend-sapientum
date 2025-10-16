import { writable } from 'svelte/store';
import './app.css'
import './embedded.css'
import App from './App.svelte'
import {isAuthenticated} from '../../shared-components/utils/auth.js';
import config from './backend.json';

// Parse URL parameters
const urlParams = new URLSearchParams(window.location.search);
const theme = urlParams.get('theme') || 'light';

// Check if we're in embedded mode (either by route or query param)
const isEmbedded = urlParams.get('embedded') === 'true' ||
                   window.location.pathname.startsWith('/embedded');

// Static mode flag is no longer used for API URL selection but kept for compatibility
window.isStaticMode = false;

window.isEmbedded = isEmbedded;
window.embeddedTheme = theme;

// Set up API configuration
const getApiBaseUrl = () => {
  console.log('Using API URL:', config.apiUrl);
  return config.apiUrl;
};

// Fetch override removed - using httpCall function instead

console.log('Application starting with fixed API URL');

if (isEmbedded) {
  console.log('Application running in embedded mode with theme:', theme);

  // Apply theme-specific styles
  document.documentElement.setAttribute('data-theme', theme);

  // Setup message handling for parent communication
  window.addEventListener('message', function(event) {
    // Handle messages from parent
    const message = event.data;

    if (message && message.type) {
      console.log('Received message from parent:', message);

      // Handle login requests
      if (message.type === 'sapientum:login' && message.credentials) {
        // TODO: Implement auto-login with credentials
        console.log('Auto-login requested with credentials');
      }
    }
  });

  // Notify parent that the application is ready
  if (window.parent && window.parent !== window) {
    window.parent.postMessage({
      type: 'sapientum:ready',
      status: 'success'
    }, '*');
  }
}

const app = new App({
  target: document.getElementById('app'),
});

export default app;
