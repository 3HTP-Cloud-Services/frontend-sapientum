<script>
  import Router from 'svelte-spa-router';
  import { push, location } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { isAuthenticated, checkAuth } from '../../shared-components/utils/auth.js';
  import { i18nStore, initializeI18n } from '../../shared-components/utils/i18n.js';
  import { writable } from 'svelte/store';
  import { httpCall } from '../../shared-components/utils/httpCall.js';

  import Login from '../../shared-components/Login/Login.svelte';
  import EmbeddedChat from '../../shared-components/Chat/EmbeddedChat.svelte';

  const routes = {
    '/': EmbeddedChat,
    '/login': Login,
    '/chat': EmbeddedChat
  };

  const isLoading = writable(true);

  // We're always in embedded mode in this app
  const isEmbedded = true;

  async function handleLogout() {
    try {
      await httpCall('/api/logout', {
        method: 'POST',
        credentials: 'include'
      });
      isAuthenticated.set(false);
      userRole.set(null);
      userEmail.set(null);
      isAuthenticated.set(false);
      push('/login');
    } catch (error) {
      console.error('Logout error:', error);
    }
  }

  onMount(async () => {
    console.log('App mounted, initializing...');
    isLoading.set(true);

    // Add logout event listener
    const handleLogoutEvent = () => {
      console.log('Logout event detected, preparing for redirect');
      isAuthenticated.set(false);
      // We don't redirect here - the component will handle that
    };
    window.addEventListener('app-logout', handleLogoutEvent);

    // Initialize i18n
    try {
      await initializeI18n();
    } catch (e) {
      console.error('i18n initialization failed:', e);
    }

    // Check authentication status
    await checkAuth();

    // Redirect based on auth status
    if (!$isAuthenticated && $location !== '/login') {
      console.log('Authentication failed, redirecting to login:', $location);
      push('/login');
    } else if ($isAuthenticated && $location === '/login') {
      console.log('Authenticated user on login page, redirecting to chat');
      push('/chat');
    } else if ($location === '' || $location === '/') {
      console.log('Root path - redirecting based on auth status');
      if ($isAuthenticated) {
        push('/chat');
      } else {
        push('/login');
      }
    }

    isLoading.set(false);

    // Clean up event listener
    return () => {
      window.removeEventListener('app-logout', handleLogoutEvent);
    };
  });

  // Redirect to login if not authenticated
  $: {
    if (!$isLoading && !$isAuthenticated && $location !== '/login') {
      push('/login');
    }
  }
</script>

<div class="app-container">
  <!-- Always show header with logout button -->
  <!-- Header handleLogout={handleLogout} title="Sapientum Chat" / -->

  <main>
    {#if $isLoading}
      <div class="loading">Loading...</div>
    {:else}
      <Router {routes} />
    {/if}
  </main>
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

  .app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
  }

  main {
    flex: 1;
    overflow: auto;
  }

  .loading {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    font-size: 1.2rem;
    color: #4a5568;
  }
</style>
