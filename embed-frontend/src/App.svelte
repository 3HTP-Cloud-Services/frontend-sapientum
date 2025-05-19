<script>
  import Router from 'svelte-spa-router';
  import { push, location } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { isAuthenticated, checkAuth } from '@shared/utils/auth.js';
  import { i18nStore, initializeI18n } from '@shared/utils/i18n.js';
  import { writable } from 'svelte/store';
  
  // Import components
  import Header from './components/Header.svelte';
  import Login from './routes/Login.svelte';
  import EmbeddedChat from './components/EmbeddedChat.svelte';

  // Define routes for this app
  const routes = {
    '/': EmbeddedChat,
    '/login': Login,
    '/chat': EmbeddedChat
  };

  // Loading state
  const isLoading = writable(true);
  
  // We're always in embedded mode in this app
  const isEmbedded = true;

  // Handle logout
  async function handleLogout() {
    try {
      await fetch('/api/logout', {
        method: 'POST',
        credentials: 'include'
      });
      isAuthenticated.set(false);
      push('/login');
    } catch (error) {
      console.error('Logout error:', error);
    }
  }

  onMount(async () => {
    console.log('App mounted, initializing...');
    isLoading.set(true);
    
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
      push('/login');
    } else if ($isAuthenticated && $location === '/login') {
      push('/chat');
    }
    
    isLoading.set(false);
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
  <Header handleLogout={handleLogout} title="Sapientum Chat" />
  
  <main>
    {#if $isLoading}
      <div class="loading">Loading...</div>
    {:else}
      <Router {routes} />
    {/if}
  </main>
</div>

<style>
  .app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background-color: #f8f9fa;
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