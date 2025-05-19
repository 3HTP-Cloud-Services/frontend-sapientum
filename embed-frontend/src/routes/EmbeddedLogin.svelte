<script>
  import { push } from 'svelte-spa-router';
  import { login, logout, isAuthenticated, checkAuth, userRole, checkChatAccess, isEmbedded } from '../lib/auth.js';
  import { i18nStore, initializeI18n } from '../lib/i18n.js';
  import { onMount } from 'svelte';

  let username = '';
  let password = '';
  let error = '';
  let isLoading = false;
  let hasChatAccess = false;
  
  // Check if we're in chatOnly mode
  const urlParams = new URLSearchParams(window.location.hash.split('?')[1] || '');
  const chatOnly = urlParams.get('chatOnly') === 'true';

  function setLocale(locale) {
    if ($i18nStore) {
      $i18nStore.locale = locale;
    }
  }

  async function handleSubmit() {
    error = '';
    isLoading = true;
    
    const result = await login(username, password);
    
    if (result.success) {
      // Check if the user has chat access
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
        await logout();
      }
    } else {
      error = result.message || 'Login failed';
    }
    
    isLoading = false;
  }

  // Initialize i18n directly 
  onMount(async () => {
    // Initialize i18n if needed
    console.log('EmbeddedLogin mounted');
    
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
  });
</script>

<div class="embedded-login">
  <div class="language-selector">
    <button class={`locale-button ${$i18nStore?.locale === 'en' ? 'selected' : ''}`}
            on:click={() => setLocale('en')}>English</button>
    <button class={`locale-button ${$i18nStore?.locale === 'es' ? 'selected' : ''}`}
            on:click={() => setLocale('es')}>Español</button>
  </div>
  
  <div class="login-form">
    <h1>{$i18nStore?.t('embedded_login_title') || 'Chat Login'}</h1>

    <form on:submit|preventDefault={handleSubmit}>
      {#if error}
        <div class="error">{error}</div>
      {/if}

      <div class="form-group">
        <label for="username">{$i18nStore?.t('username') || 'Username'}</label>
        <input
          type="text"
          id="username"
          bind:value={username}
          required
          disabled={isLoading}
        />
      </div>

      <div class="form-group">
        <label for="password">{$i18nStore?.t('password') || 'Password'}</label>
        <input
          type="password"
          id="password"
          bind:value={password}
          required
          disabled={isLoading}
        />
      </div>

      <button class="login-button" type="submit" disabled={isLoading}>
        {isLoading ? $i18nStore?.t('logging_in') || 'Logging in...' : $i18nStore?.t('login_button') || 'Login'}
      </button>
    </form>
  </div>
</div>

<style>
  .embedded-login {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background-color: #f8f9fa;
    padding: 1rem;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 9999;
  }

  .language-selector {
    display: flex;
    justify-content: center;
    margin-bottom: 1rem;
  }

  .locale-button {
    margin: 0 4px;
    color: white;
    background-color: #718096;
    padding: 0.3rem 0.6rem;
    border: 2px solid transparent;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8rem;
  }

  .locale-button.selected {
    background-color: #4a72b3;
    border: 2px solid #4a5568;
  }

  .login-form {
    width: 100%;
    max-width: 400px;
    background-color: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  h1 {
    text-align: center;
    color: #4a5568;
    margin-bottom: 1.5rem;
    font-size: 1.5rem;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    color: #4a5568;
  }

  input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    font-size: 1rem;
  }

  .login-button {
    width: 100%;
    background-color: #4299e1;
    color: white;
    border: none;
    padding: 0.75rem;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
    margin-top: 1rem;
  }

  .login-button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .error {
    color: #e53e3e;
    margin-bottom: 1rem;
    padding: 0.5rem;
    background-color: #fed7d7;
    border-radius: 4px;
    font-size: 0.9rem;
  }
  
  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #4a5568;
  }
  
  .loading-spinner {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: 3px solid #e2e8f0;
    border-top-color: #4299e1;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
</style>