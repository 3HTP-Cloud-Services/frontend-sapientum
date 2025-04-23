<script>
  import Router from 'svelte-spa-router';
  import { push, location } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { isAuthenticated, checkAuth } from './lib/auth.js';
  import Login from './routes/Login.svelte';
  import Documents from './routes/Documents.svelte';
  import DocumentDetail from './routes/DocumentDetail.svelte';
  import Console from './routes/Console.svelte';
  import Permissions from './routes/Permissions.svelte';

  // Define routes
  const routes = {
    '/': Console,
    '/console': Console,
    '/documents': Documents,
    '/login': Login,
    '/documents/:id': DocumentDetail,
    '/permissions': Permissions
  };

  onMount(async () => {
    // Use the global static mode flag
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

    // Debug log the current route
    console.log('Current route at mount:', $location);
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
  <Router {routes} />
</div>
