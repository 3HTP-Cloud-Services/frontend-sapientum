<script>
  import { onMount } from 'svelte';
  import Router from 'svelte-spa-router';
  import { push, location } from 'svelte-spa-router';
  import { isAuthenticated, checkAuth, checkChatAccess, logout, isEmbedded } from '@shared/utils/auth.js';
  import { i18nStore, initializeI18n } from '@shared/utils/i18n.js';
  import { writable } from 'svelte/store';
  import EmbeddedLogin from './EmbeddedLogin.svelte';
  import Chat from '@shared/Chat/Chat.svelte';

  // Define routes for the embedded app
  // NOTE: Make sure embedded chat is shown without console wrapper
  const routes = {
    '/embedded': EmbeddedLogin,
    '/embedded/login': EmbeddedLogin,
    '/embedded/chat': Chat  // This should be shown fullscreen
  };

  export const isLoading = writable(true);
  const embeddedTheme = window.embeddedTheme || 'light';
  
  // Extract chatOnly parameter from URL if present
  const urlParams = new URLSearchParams(window.location.hash.split('?')[1] || '');
  const chatOnly = urlParams.get('chatOnly') === 'true';

  onMount(async () => {
    console.log('EmbeddedApp mounted, initializing...');
    isLoading.set(true);
    
    // Initialize i18n if not already initialized
    if (!$i18nStore) {
      try {
        console.log('Initializing i18n in EmbeddedApp');
        await initializeI18n();
        console.log('i18n initialized successfully in EmbeddedApp');
      } catch (e) {
        console.error('i18n initialization failed:', e);
      }
    }

    // Check authentication status
    const isAuth = await checkAuth();
    console.log('Authentication status:', isAuth);
    
    if (isAuth) {
      // Check if user has chat access
      const hasChatAccess = await checkChatAccess();
      console.log('Chat access status:', hasChatAccess);
      console.log('Embedded status from backend:', $isEmbedded);
      
      // If in embedded mode or chatOnly mode is enabled, user must have chat access
      if (($isEmbedded || chatOnly) && !hasChatAccess) {
        console.log('Embedded/chat-only mode active but user does not have chat access');
        await logout();
        push('/embedded/login');
        return;
      }
      
      if (hasChatAccess) {
        if ($location === '/embedded' || $location === '/embedded/login') {
          console.log('Redirecting to embedded chat from', $location);
          push('/embedded/chat');
        }
      } else {
        // If authenticated but no chat access, force logout
        console.log('User does not have chat access, redirecting to login');
        await logout();
        if ($location !== '/embedded/login') {
          push('/embedded/login');
        }
      }
    } else {
      // Not authenticated, redirect to login
      console.log('Not authenticated, redirecting to embedded login');
      if ($location !== '/embedded/login') {
        push('/embedded/login');
      }
    }
    
    isLoading.set(false);
  });

  // Redirect to login if not authenticated
  $: {
    if (!$isLoading && !$isAuthenticated && 
      $location !== '/embedded/login' && 
      $location !== '/embedded') {
      push('/embedded/login');
    }
  }
</script>

<div class="embedded-container" data-theme={embeddedTheme}>
  {#if $isLoading}
    <div class="loading">Loading...</div>
  {:else}
    <Router {routes} />
  {/if}
</div>

<style>
  .embedded-container {
    width: 100%;
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .embedded-container[data-theme="dark"] {
    --bg-color: #1a202c;
    --text-color: #e2e8f0;
    --border-color: #4a5568;
    background-color: var(--bg-color);
    color: var(--text-color);
  }

  .embedded-container[data-theme="light"] {
    --bg-color: #ffffff;
    --text-color: #2d3748;
    --border-color: #e2e8f0;
    background-color: var(--bg-color);
    color: var(--text-color);
  }

  .loading {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    font-size: 1.2rem;
    color: var(--text-color);
  }
</style>