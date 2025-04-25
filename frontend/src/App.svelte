<script>
  import Router from 'svelte-spa-router';
  import { push, location } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { isAuthenticated, checkAuth } from './lib/auth.js';
  import Login from './routes/Login.svelte';
  import Console from './routes/Console.svelte';

  const routes = {
    '/': Console,
    '/console': Console,
    '/login': Login,
  };

  onMount(async () => {
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
