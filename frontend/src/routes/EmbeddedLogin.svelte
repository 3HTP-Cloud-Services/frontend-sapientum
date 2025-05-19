<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { checkAuth, checkChatAccess, isEmbedded } from '@shared/utils/auth.js';
  import { i18nStore } from '@shared/utils/i18n.js';
  import Login from '@shared/Login/Login.svelte';

  let hasChatAccess = false;
  let error = '';
  
  // Check if we're in chatOnly mode
  const urlParams = new URLSearchParams(window.location.hash.split('?')[1] || '');
  const chatOnly = urlParams.get('chatOnly') === 'true';
  
  // Custom login handler for embedded mode to check chat access
  async function checkEmbeddedAccess() {
    // Check if already authenticated
    const isAuth = await checkAuth();
    
    if (isAuth) {
      // Check if user has chat access
      hasChatAccess = await checkChatAccess();
      
      if (hasChatAccess) {
        push('/embedded/chat');
      } else {
        // Show specific error based on the mode
        if (chatOnly || $isEmbedded) {
          error = $i18nStore?.t('chat_only_access_required') || 'This embed requires chat access permission, which your account does not have';
        } else {
          error = $i18nStore?.t('no_chat_access') || 'You do not have access to chat functionality';
        }
      }
    }
  }
  
  // Initialize check on mount
  onMount(async () => {
    console.log('EmbeddedLogin mounted');
    await checkEmbeddedAccess();
  });
</script>

<Login 
  redirectTo="/embedded/chat" 
  isEmbedded={true} 
/>

{#if error}
  <div class="error-overlay">
    <div class="error-message">{error}</div>
  </div>
{/if}

<style>
  .error-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    z-index: 1000;
    background-color: rgba(229, 62, 62, 0.85);
    padding: 1rem;
    color: white;
    text-align: center;
    font-weight: bold;
  }
  
  .error-message {
    max-width: 80%;
    margin: 0 auto;
  }
</style>

