<script>
  import { createEventDispatcher } from 'svelte';
  import { i18nStore } from '../utils/i18n.js';

  export let username = '';
  export let session = '';
  export let isLoading = false;
  export let errorMessage = '';

  const dispatch = createEventDispatcher();

  let newPassword = '';
  let confirmPassword = '';
  let showPassword = false;
  let validationErrors = {};

  $: {
    validatePasswords();
  }

  function validatePasswords() {
    validationErrors = {};

    if (newPassword && newPassword.length < 8) {
      validationErrors.newPassword = 'Password must be at least 8 characters long';
    }

    if (newPassword && !/(?=.*[a-z])/.test(newPassword)) {
      validationErrors.newPassword = 'Password must contain at least one lowercase letter';
    }

    if (newPassword && !/(?=.*[A-Z])/.test(newPassword)) {
      validationErrors.newPassword = 'Password must contain at least one uppercase letter';
    }

    if (newPassword && !/(?=.*\d)/.test(newPassword)) {
      validationErrors.newPassword = 'Password must contain at least one number';
    }

    if (newPassword && !/(?=.*[!@#$%^&*()_+\-=\[\]{}|;:,.<>?])/.test(newPassword)) {
      validationErrors.newPassword = 'Password must contain at least one special character';
    }

    if (confirmPassword && newPassword !== confirmPassword) {
      validationErrors.confirmPassword = 'Passwords do not match';
    }
  }

  function handleSubmit() {
    validatePasswords();

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    if (!newPassword || !confirmPassword) {
      return;
    }

    dispatch('passwordChange', {
      username,
      newPassword,
      session
    });
  }

  function handleCancel() {
    dispatch('cancel');
  }

  function togglePasswordVisibility() {
    showPassword = !showPassword;
  }

  function handleKeydown(event) {
    if (event.key === 'Enter') {
      handleSubmit();
    }
  }
</script>

<div class="password-change-container">
  <div class="language-selector">
    <button class={`locale-button ${$i18nStore?.locale === 'en' ? 'selected' : ''}`}
            on:click={() => $i18nStore && ($i18nStore.locale = 'en')}>English</button>
    <button class={`locale-button ${$i18nStore?.locale === 'es' ? 'selected' : ''}`}
            on:click={() => $i18nStore && ($i18nStore.locale = 'es')}>Español</button>
  </div>
  <h1>{$i18nStore?.t('change_password_title') || 'Set New Password'}</h1>
  <p class="subtitle">{$i18nStore?.t('change_password_subtitle') || 'Please set a new password for your account'}</p>
  <p class="user-info">User: <strong>{username}</strong></p>

  {#if errorMessage}
    <div class="error">
      {errorMessage}
    </div>
  {/if}

  <form on:submit|preventDefault={handleSubmit}>
      <div class="form-group">
        <label for="newPassword">{$i18nStore?.t('new_password_label') || 'New Password'}</label>
        <div class="password-input-wrapper">
          {#if showPassword}
            <input
              id="newPassword"
              type="text"
              bind:value={newPassword}
              placeholder={$i18nStore?.t('new_password_placeholder') || 'Enter your new password'}
              class:error={validationErrors.newPassword}
              disabled={isLoading}
              on:keydown={handleKeydown}
              required
            />
          {:else}
            <input
              id="newPassword"
              type="password"
              bind:value={newPassword}
              placeholder={$i18nStore?.t('new_password_placeholder') || 'Enter your new password'}
              class:error={validationErrors.newPassword}
              disabled={isLoading}
              on:keydown={handleKeydown}
              required
            />
          {/if}
          <button
            type="button"
            class="password-toggle"
            on:click={togglePasswordVisibility}
            disabled={isLoading}
          >
            {showPassword ? '👁️' : '👁️‍🗨️'}
          </button>
        </div>
        {#if validationErrors.newPassword}
          <div class="field-error">{validationErrors.newPassword}</div>
        {/if}
      </div>

      <div class="form-group">
        <label for="confirmPassword">{$i18nStore?.t('confirm_password_label') || 'Confirm New Password'}</label>
        {#if showPassword}
          <input
            id="confirmPassword"
            type="text"
            bind:value={confirmPassword}
            placeholder={$i18nStore?.t('confirm_password_placeholder') || 'Confirm your new password'}
            class:error={validationErrors.confirmPassword}
            disabled={isLoading}
            on:keydown={handleKeydown}
            required
          />
        {:else}
          <input
            id="confirmPassword"
            type="password"
            bind:value={confirmPassword}
            placeholder={$i18nStore?.t('confirm_password_placeholder') || 'Confirm your new password'}
            class:error={validationErrors.confirmPassword}
            disabled={isLoading}
            on:keydown={handleKeydown}
            required
          />
        {/if}
        {#if validationErrors.confirmPassword}
          <div class="field-error">{validationErrors.confirmPassword}</div>
        {/if}
      </div>

      <div class="password-requirements">
        <h4>{$i18nStore?.t('password_requirements_title') || 'Password Requirements:'}</h4>
        <ul>
          <li class:valid={newPassword && newPassword.length >= 8}>
            {$i18nStore?.t('password_req_length') || 'At least 8 characters'}
          </li>
          <li class:valid={newPassword && /(?=.*[a-z])/.test(newPassword)}>
            {$i18nStore?.t('password_req_lowercase') || 'One lowercase letter'}
          </li>
          <li class:valid={newPassword && /(?=.*[A-Z])/.test(newPassword)}>
            {$i18nStore?.t('password_req_uppercase') || 'One uppercase letter'}
          </li>
          <li class:valid={newPassword && /(?=.*\d)/.test(newPassword)}>
            {$i18nStore?.t('password_req_number') || 'One number'}
          </li>
          <li class:valid={newPassword && /(?=.*[!@#$%^&*()_+\-=\[\]{}|;:,.<>?])/.test(newPassword)}>
            {$i18nStore?.t('password_req_special') || 'One special character'}
          </li>
        </ul>
      </div>

    <button
      type="submit"
      class="login-button"
      disabled={isLoading || Object.keys(validationErrors).length > 0 || !newPassword || !confirmPassword}
    >
      {#if isLoading}
        {$i18nStore?.t('updating_password') || 'Updating Password...'}
      {:else}
        {$i18nStore?.t('update_password_button') || 'Update Password'}
      {/if}
    </button>

    <button
      type="button"
      class="cancel-button"
      on:click={handleCancel}
      disabled={isLoading}
    >
      {$i18nStore?.t('cancel_button') || 'Cancel'}
    </button>
  </form>
</div>

<style>
  .password-change-container {
    max-width: 400px;
    margin: 0 auto;
    padding: 2rem;
    background-color: #4a5568;
    color: white;
    border-radius: 8px;
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
    color: #032b36;
    font-size: 1rem;
    box-sizing: border-box;
  }

  .password-input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .password-input-wrapper input {
    padding-right: 3rem;
  }

  .password-toggle {
    position: absolute;
    right: 0.5rem;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.2rem;
    padding: 0.25rem;
    border-radius: 4px;
    color: #4a5568;
  }

  .password-toggle:hover {
    background-color: rgba(74, 85, 104, 0.1);
  }

  .password-toggle:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .error {
    color: #ff6b6b;
    margin-bottom: 1rem;
    padding: 0.5rem;
    background-color: rgba(255, 107, 107, 0.1);
    border-radius: 4px;
  }

  .field-error {
    color: #ff6b6b;
    font-size: 0.85rem;
    margin-top: 0.25rem;
  }

  .subtitle {
    text-align: center;
    margin-bottom: 1rem;
    font-size: 0.9rem;
    color: #cbd5e0;
  }

  .user-info {
    text-align: center;
    margin-bottom: 1.5rem;
    font-size: 0.9rem;
    color: #e2e8f0;
  }

  .password-requirements {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 4px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .password-requirements h4 {
    margin: 0 0 0.5rem 0;
    color: white;
    font-size: 0.9rem;
    font-weight: 600;
  }

  .password-requirements ul {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .password-requirements li {
    padding: 0.25rem 0;
    color: #cbd5e0;
    font-size: 0.85rem;
    position: relative;
    padding-left: 1.5rem;
  }

  .password-requirements li::before {
    content: '✗';
    position: absolute;
    left: 0;
    color: #ff6b6b;
    font-weight: bold;
  }

  .password-requirements li.valid {
    color: #68d391;
  }

  .password-requirements li.valid::before {
    content: '✓';
    color: #68d391;
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

  .cancel-button {
    width: 100%;
    background-color: #718096;
    color: white;
    border: none;
    padding: 0.75rem;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
    margin-top: 0.5rem;
  }

  .cancel-button:hover:not(:disabled) {
    background-color: #5a6570;
  }

  input:disabled, button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  h1 {
    text-align: center;
    margin-bottom: 1.5rem;
  }

  input.error {
    border-color: #ff6b6b;
  }
</style>
