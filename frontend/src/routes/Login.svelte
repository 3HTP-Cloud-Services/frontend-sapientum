<script>
  import { push, location } from 'svelte-spa-router';
  import { login, isAuthenticated } from '../lib/auth.js';
  import { i18nStore } from '../lib/i18n.js';

  let username = '';
  let password = '';
  let error = '';
  
  function setLocale(locale) {
    if ($i18nStore) {
      $i18nStore.locale = locale;
    }
  }

  async function handleSubmit() {
    error = '';
    const result = await login(username, password);

    if (result.success) {
      push('/');
    } else {
      error = result.message || 'Login failed';
    }
  }

  // Redirect to documents if already authenticated
  $: {
    if ($isAuthenticated) {
      push('/');
    }
  }
</script>

<div class="login-container">
  <div class="language-selector">
    <button class={`locale_button ${$i18nStore.locale === 'en' ? 'selected' : ''}`} 
            on:click={() => setLocale('en')}>English</button>
    <button class={`locale_button ${$i18nStore.locale === 'es' ? 'selected' : ''}`}
            on:click={() => setLocale('es')}>Español</button>
  </div>
  <h1>{$i18nStore.t('login_title')}</h1>

  <form on:submit|preventDefault={handleSubmit}>
    {#if error}
      <div class="error">{error}</div>
    {/if}

    <div class="form-group">
      <label for="username">{$i18nStore.t('username')}</label>
      <input
        type="text"
        id="username"
        bind:value={username}
        required
      />
    </div>

    <div class="form-group">
      <label for="password">{$i18nStore.t('password')}</label>
      <input
        type="password"
        id="password"
        bind:value={password}
        required
      />
    </div>

    <button class="login_button" type="submit">{$i18nStore.t('login_button')}</button>
  </form>
</div>

<style>
  .login-container {
    max-width: 400px;
    margin: 0 auto;
    padding: 2rem;
    background-color: #4a5568;;
    color: white;
    border-radius: 8px;
  }

  .language-selector {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 1rem;
  }

  .locale_button {
    margin: 0 4px;
    color: white;
    background-color: #718096;
    padding: 0.3rem 0.6rem;
    border: 2px solid transparent;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8rem;
  }

  .locale_button.selected {
    background-color: #4a72b3;
    border: 2px solid white;
  }

  .error {
    color: #ff6b6b;
    margin-bottom: 1rem;
    padding: 0.5rem;
    background-color: rgba(255, 107, 107, 0.1);
    border-radius: 4px;
  }
</style>
