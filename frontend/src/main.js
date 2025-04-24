import { writable } from 'svelte/store';
import { initializeI18n } from './lib/i18n.js';
import './app.css'
import App from './App.svelte'
import {isAuthenticated} from "./lib/auth.js";

// Set a flag for static mode at the global level
window.isStaticMode = window.location.pathname === '/' &&
                      !window.location.href.includes('localhost:5173');

await initializeI18n();

// Log startup mode for debugging
if (window.isStaticMode) {
  console.log('Application starting in STATIC mode');
} else {
  console.log('Application starting in DEVELOPMENT mode');
}

// For Svelte 5, we should use create() instead of new App()
// But with compatibility mode, both should work
const app = new App({
  target: document.getElementById('app'),
})

export default app
