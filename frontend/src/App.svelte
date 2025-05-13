<script>
  import Router from 'svelte-spa-router';
  import { push, location } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { isAuthenticated, checkAuth } from './lib/auth.js';
  import { i18nStore, initializeI18n } from './lib/i18n.js';
  import Login from './routes/Login.svelte';
  import Console from './routes/Console.svelte';
  import { writable } from 'svelte/store';

  const routes = {
    '/': Console,
    '/console': Console,
    '/login': Login,
  };

  // Add a loading indicator
  const isLoading = writable(true);
  const isEmbedded = window.isEmbedded || false;
  const embeddedTheme = window.embeddedTheme || 'light';

  // Message handler for embedded mode
  function handleMessage(event) {
    const message = event.data;
    if (!message || !message.type) return;

    console.log('Handling embedded message:', message);

    // Handle specific message types
    if (message.type === 'sapientum:navigate') {
      if (message.path) {
        push(message.path);
      }
    }
  }

  // Send message to parent (if in embedded mode)
  function sendMessageToParent(message) {
    if (isEmbedded && window.parent && window.parent !== window) {
      window.parent.postMessage(message, '*');
    }
  }

  onMount(async () => {
    // Initialize i18n first
    try {
      await initializeI18n();
    } catch (e) {
      console.error('i18n initialization failed:', e);
    }

    // Set up message event listener for embedded mode
    if (isEmbedded) {
      window.addEventListener('message', handleMessage);
    }

    if (window.isStaticMode) {
      console.log('App component running in static mode');
      // In static mode, we'll still try auth checks since our API is available
      try {
        await checkAuth();
      } catch (e) {
        console.error('Auth check failed, setting authenticated anyway in static mode:', e);
        isAuthenticated.set(true);
      }
    } else {
      console.log('App component running in development mode');
      await checkAuth();
    }

    // If the route is empty, go to the console
    if ($location === '' || $location === '/') {
      console.log('Empty location detected, pushing to console');
      push('/console');
    }

    console.log('Current route at mount:', $location);
    isLoading.set(false);

    // Notify parent when navigation occurs (for embedded mode)
    if (isEmbedded) {
      sendMessageToParent({
        type: 'sapientum:navigationChanged',
        path: $location
      });
    }

    return () => {
      // Clean up event listener
      if (isEmbedded) {
        window.removeEventListener('message', handleMessage);
      }
    };
  });

  // Watch for route changes and notify parent in embedded mode
  $: {
    if (isEmbedded && !isLoading) {
      sendMessageToParent({
        type: 'sapientum:navigationChanged',
        path: $location
      });
    }
  }

  // Redirect to login if not authenticated
  $: {
    if (!$isAuthenticated && $location !== '/login' && $location !== '' && $location !== '/') {
      console.log('Not authenticated, redirecting to login from', $location);
      push('/login');
    }
  }
</script>

<div class="container" class:embedded={isEmbedded} data-theme={embeddedTheme}>
  {#if $isLoading}
    <div class="loading">Loading application...</div>
  {:else}
    <Router {routes} />
  {/if}
</div>

<style>
  :global(html[data-theme="dark"]) {
    --bg-color: #1a202c;
    --text-color: #e2e8f0;
    --border-color: #4a5568;
  }

  :global(html[data-theme="light"]) {
    --bg-color: #ffffff;
    --text-color: #2d3748;
    --border-color: #e2e8f0;
  }

  .container.embedded {
    border: none;
    margin: 0;
    padding: 0;
    height: 100vh;
    width: 100%;
    overflow: auto;
  }

  .container.embedded[data-theme="dark"] {
    background-color: var(--bg-color);
    color: var(--text-color);
  }

  .container.embedded[data-theme="light"] {
    background-color: var(--bg-color);
    color: var(--text-color);
  }

  .loading {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    font-size: 1.2rem;
    color: #4a5568;
  }
</style>
