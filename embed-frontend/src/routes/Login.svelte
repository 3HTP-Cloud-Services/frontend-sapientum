<script>
  import { push, location } from 'svelte-spa-router';
  import { login, isAuthenticated } from '@shared/utils/auth.js';
  import { i18nStore } from '@shared/utils/i18n.js';

  let username = '';
  let password = '';
  let error = '';
  let isLoading = false;

  function setLocale(locale) {
    if ($i18nStore) {
      $i18nStore.locale = locale;
    }
  }

  async function handleSubmit() {
    error = '';
    isLoading = true;

    const result = await login(username, password);

    isLoading = false;

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
  <h1>{$i18nStore.t('login_title')}</h1>

  <form on:submit|preventDefault={handleSubmit}>
    {#if error}
      <div class="error">{error}</div>
    {/if}

    <div class="form-group">
      <label for="username">{$i18nStore.t('username')} snncxc</label>
      <input
        type="text"
        id="username"
        bind:value={username}
        required
        disabled={isLoading}
      />
    </div>

    <div class="form-group">
      <label for="password">{$i18nStore.t('password')}</label>
      <input
        type="password"
        id="password"
        bind:value={password}
        required
        disabled={isLoading}
      />
    </div>

    <button class="login_button" type="submit" disabled={isLoading}>
      {isLoading ? $i18nStore.t('logging_in') || 'Logging in...' : $i18nStore.t('login_button')}
    </button>
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

  input:disabled, button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
</style>
