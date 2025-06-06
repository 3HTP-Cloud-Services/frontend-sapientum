import { writable } from 'svelte/store';
import './app.css'
import './embedded.css'
import App from './App.svelte'
import {isAuthenticated} from '../../shared-components/utils/auth.js';
import config from './config.json';

// Parse URL parameters
const urlParams = new URLSearchParams(window.location.search);
const theme = urlParams.get('theme') || 'light';

// Check if we're in embedded mode (either by route or query param)
const isEmbedded = urlParams.get('embedded') === 'true' ||
                   window.location.pathname.startsWith('/embedded');

// Set a flag for static mode at the global level
window.isStaticMode = window.location.pathname === '/' &&
                      !window.location.href.includes('localhost:5173');

window.isEmbedded = isEmbedded;
window.embeddedTheme = theme;

// Set up API configuration
const getApiBaseUrl = () => {
  // If in static mode, always use lambda
  if (window.isStaticMode) {
    console.log('Using lambda API URL:', config.lambda.apiUrl);
    return config.lambda.apiUrl;
  }
  // Otherwise use local
  console.log('Using local API URL:', config.local.apiUrl);
  return config.local.apiUrl;
};

// Override fetch for API calls
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
  // Only intercept calls to /api
  if (typeof url === 'string' && url.startsWith('/api')) {
    const baseUrl = getApiBaseUrl();
    const normalizedEndpoint = url.replace('/api/', '');
    const newUrl = `${baseUrl}/${normalizedEndpoint}`;
    console.log(`Redirecting API call from ${url} to ${newUrl}`);
    return originalFetch(newUrl, options);
  }

  // Pass through all other fetch calls
  return originalFetch(url, options);
};

if (window.isStaticMode) {
  console.log('Application starting in STATIC mode');
} else {
  console.log('Application starting in DEVELOPMENT mode');
}

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
