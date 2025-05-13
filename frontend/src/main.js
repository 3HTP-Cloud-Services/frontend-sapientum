import { writable } from 'svelte/store';
import './app.css'
import './embedded.css'
import App from './App.svelte'
import {isAuthenticated} from "./lib/auth.js";

// Parse URL parameters
const urlParams = new URLSearchParams(window.location.search);
const isEmbedded = urlParams.get('embedded') === 'true';
const theme = urlParams.get('theme') || 'light';

// Set a flag for static mode at the global level
window.isStaticMode = window.location.pathname === '/' &&
                      !window.location.href.includes('localhost:5173');

window.isEmbedded = isEmbedded;
window.embeddedTheme = theme;

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
