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

  onMount(async () => {
    // Initialize i18n first
    try {
      await initializeI18n();
    } catch (e) {
      console.error('i18n initialization failed:', e);
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
  });

  // Redirect to login if not authenticated
  $: {
    if (!$isAuthenticated && $location !== '/login' && $location !== '' && $location !== '/') {
      console.log('Not authenticated, redirecting to login from', $location);
      push('/login');
    }
  }
</script>

<div class="container">
  {#if $isLoading}
    <div class="loading">Loading application...</div>
  {:else}
    <Router {routes} />
  {/if}
</div>

<style>
  .loading {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    font-size: 1.2rem;
    color: #4a5568;
  }
</style>
