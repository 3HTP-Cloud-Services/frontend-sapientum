<script>
  import Router from 'svelte-spa-router';
  import { push, location } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { isAuthenticated, checkAuth } from '../../shared-components/utils/auth.js';
  import { i18nStore, initializeI18n } from '../../shared-components/utils/i18n.js';
  import Login from '../../shared-components/Login/Login.svelte';
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

  // Check if we're in embedded mode from URL
  const inEmbeddedMode = $location && ($location.startsWith('/embedded'));

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
    if ((isEmbedded || inEmbeddedMode) && window.parent && window.parent !== window) {
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
    if (isEmbedded || inEmbeddedMode) {
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

    // Route handling based on mode
    if (isEmbedded || inEmbeddedMode) {
      // If we're in embedded mode but not on an embedded route, redirect to embedded
      if (!$location.startsWith('/embedded')) {
        console.log('Embedded mode detected, redirecting to embedded route');
        push('/embedded');
      }
    } else if ($location === '' || $location === '/') {
      // If regular mode and the route is empty, go to the console
      console.log('Empty location detected in regular mode, pushing to console');
      push('/console');
    }

    console.log('Current route at mount:', $location);
    isLoading.set(false);

    // Notify parent when navigation occurs (for embedded mode)
    if (isEmbedded || inEmbeddedMode) {
      sendMessageToParent({
        type: 'sapientum:navigationChanged',
        path: $location
      });
    }

    return () => {
      // Clean up event listener
      if (isEmbedded || inEmbeddedMode) {
        window.removeEventListener('message', handleMessage);
      }
    };
  });

  // Watch for route changes and notify parent in embedded mode
  $: {
    if ((isEmbedded || inEmbeddedMode) && !isLoading) {
      sendMessageToParent({
        type: 'sapientum:navigationChanged',
        path: $location
      });
    }
  }

  // Redirect to login if not authenticated (except for embedded routes)
  $: {
    if (!$isAuthenticated &&
        $location !== '/login' &&
        $location !== '' &&
        $location !== '/' &&
        !$location.startsWith('/embedded')) {
      console.log('Not authenticated, redirecting to login from', $location);
      push('/login');
    }
  }
</script>

<div class="container" class:embedded={isEmbedded || inEmbeddedMode} data-theme={embeddedTheme}>
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
