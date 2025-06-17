<script>
  import { push } from 'svelte-spa-router';
  import { login, setNewPassword, isAuthenticated } from '../utils/auth.js';
  import { i18nStore } from '../utils/i18n.js';
  import PasswordChange from './PasswordChange.svelte';

  // Props to control behavior
  export let redirectTo = '/';
  export let isEmbedded = false;

  let username = '';
  let password = '';
  let error = '';
  let isLoading = false;
  
  // Password change state
  let showPasswordChange = false;
  let passwordChangeSession = '';
  let passwordChangeUsername = '';

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
      push(redirectTo);
    } else if (result.error === 'new_password_required') {
      // Show password change form
      showPasswordChange = true;
      passwordChangeSession = result.session;
      passwordChangeUsername = result.username;
      error = ''; // Clear error since this is expected flow
    } else {
      error = result.message || 'Login failed';
    }
  }

  async function handlePasswordChange(event) {
    error = '';
    isLoading = true;

    const { username, newPassword, session } = event.detail;

    const result = await setNewPassword(username, newPassword, session);

    isLoading = false;

    if (result.success) {
      // Password updated successfully, redirect
      showPasswordChange = false;
      push(redirectTo);
    } else {
      error = result.message || 'Failed to update password';
    }
  }

  function handlePasswordChangeCancel() {
    // Go back to login form
    showPasswordChange = false;
    passwordChangeSession = '';
    passwordChangeUsername = '';
    error = '';
    password = ''; // Clear the temporary password
  }

  // Redirect to destination if already authenticated
  $: {
    if ($isAuthenticated) {
      push(redirectTo);
    }
  }
</script>

{#if showPasswordChange}
  <!-- Password Change Form -->
  <PasswordChange
    username={passwordChangeUsername}
    session={passwordChangeSession}
    {isLoading}
    errorMessage={error}
    on:passwordChange={handlePasswordChange}
    on:cancel={handlePasswordChangeCancel}
  />
{:else}
  <!-- Regular Login Form -->
  <div class="login-container" class:embedded={isEmbedded}>
    <div class="language-selector">
      <button class={`locale-button ${$i18nStore?.locale === 'en' ? 'selected' : ''}`}
              on:click={() => setLocale('en')}>English</button>
      <button class={`locale-button ${$i18nStore?.locale === 'es' ? 'selected' : ''}`}
              on:click={() => setLocale('es')}>Español</button>
    </div>
    <h1>{$i18nStore?.t('login_title') || 'Login'}</h1>

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
{/if}

<style>
  .login-container {
    max-width: 400px;
    margin: 0 auto;
    padding: 2rem;
    background-color: #4a5568;
    color: white;
    border-radius: 8px;
  }

  .login-container.embedded {
    margin-top: 50px;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .language-selector {
    display: flex;
    justify-content: flex-end;
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
    border: 2px solid white;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
  }

  input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    background-color: rgba(255, 255, 255, 0.9);
    color: #2d3748;
    font-size: 1rem;
  }

  .error {
    color: #ff6b6b;
    margin-bottom: 1rem;
    padding: 0.5rem;
    background-color: rgba(255, 107, 107, 0.1);
    border-radius: 4px;
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

  input:disabled, button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  h1 {
    text-align: center;
    margin-bottom: 1.5rem;
  }
</style>
