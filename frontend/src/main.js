import { writable } from 'svelte/store';
import './app.css'
import App from './App.svelte'
import {isAuthenticated} from "./lib/auth.js";

// Set a flag for static mode at the global level
window.isStaticMode = window.location.pathname === '/' &&
                      !window.location.href.includes('localhost:5173');

if (window.isStaticMode) {
  console.log('Application starting in STATIC mode');
} else {
  console.log('Application starting in DEVELOPMENT mode');
}

const app = new App({
  target: document.getElementById('app'),
});

export default app;
