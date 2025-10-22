<script>
  import { createEventDispatcher } from 'svelte';
  import { i18nStore } from '../utils/i18n.js';
  import { httpCall } from '../utils/httpCall.js';

  export let isLoading = false;
  export let errorMessage = '';

  const dispatch = createEventDispatcher();

  let step = 1; // 1: email input, 2: verification code + new password
  let email = '';
  let verificationCode = '';
  let newPassword = '';
  let confirmPassword = '';
  let successMessage = '';

  async function handleSendCode() {
    if (!email) {
      errorMessage = 'Email is required';
      return;
    }

    isLoading = true;
    errorMessage = '';
    successMessage = '';

    try {
      const response = await httpCall('/api/forgot-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: email
        })
      });

      const result = await response.json();

      if (response.ok && result.success) {
        successMessage = result.message;
        step = 2;
      } else {
        errorMessage = result.error || 'Failed to send reset code';
      }
    } catch (error) {
      errorMessage = 'Network error. Please try again.';
    } finally {
      isLoading = false;
    }
  }

  async function handleResetPassword() {
    if (!verificationCode || !newPassword || !confirmPassword) {
      errorMessage = 'All fields are required';
      return;
    }

    if (newPassword !== confirmPassword) {
      errorMessage = 'Passwords do not match';
      return;
    }

    isLoading = true;
    errorMessage = '';

    try {
      const response = await httpCall('/api/confirm-forgot-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: email,
          verificationCode: verificationCode,
          newPassword: newPassword
        })
      });

      const result = await response.json();

      if (response.ok && result.success) {
        successMessage = result.message;
        // Dispatch success event to parent
        dispatch('passwordReset', { success: true, message: result.message });
      } else {
        errorMessage = result.error || 'Failed to reset password';
      }
    } catch (error) {
      errorMessage = 'Network error. Please try again.';
    } finally {
      isLoading = false;
    }
  }

  function handleCancel() {
    dispatch('cancel');
  }

  function goBackToStep1() {
    step = 1;
    verificationCode = '';
    newPassword = '';
    confirmPassword = '';
    errorMessage = '';
    successMessage = '';
  }
</script>

<div class="forgot-password-container">
  <h2>{$i18nStore?.t('forgot_password_title') || 'Reset Password'}</h2>

  {#if step === 1}
    <!-- Step 1: Email Input -->
    <p class="instructions">
      {$i18nStore?.t('forgot_password_instructions') || 'Enter your email address and we\'ll send you a verification code to reset your password.'}
    </p>

    <form on:submit|preventDefault={handleSendCode}>
      {#if errorMessage}
        <div class="error">{errorMessage}</div>
      {/if}

      {#if successMessage}
        <div class="success">{successMessage}</div>
      {/if}

      <div class="form-group">
        <label for="email">{$i18nStore?.t('email_label') || 'Email'}</label>
        <input
          type="email"
          id="email"
          bind:value={email}
          required
          disabled={isLoading}
          placeholder="Enter your email address"
        />
      </div>

      <div class="button-group">
        <button type="button" class="cancel-button" on:click={handleCancel} disabled={isLoading}>
          {$i18nStore?.t('cancel_button') || 'Cancel'}
        </button>
        <button type="submit" class="submit-button" disabled={isLoading}>
          {isLoading ? 'Sending...' : ($i18nStore?.t('send_code_button') || 'Send Code')}
        </button>
      </div>
    </form>

  {:else}
    <!-- Step 2: Verification Code + New Password -->
    <p class="instructions">
      {$i18nStore?.t('enter_code_instructions') || 'Enter the verification code sent to your email and your new password.'}
    </p>

    <form on:submit|preventDefault={handleResetPassword}>
      {#if errorMessage}
        <div class="error">{errorMessage}</div>
      {/if}

      {#if successMessage}
        <div class="success">{successMessage}</div>
      {/if}

      <div class="form-group">
        <label for="verification-code">{$i18nStore?.t('verification_code') || 'Verification Code'}</label>
        <input
          type="text"
          id="verification-code"
          bind:value={verificationCode}
          required
          disabled={isLoading}
          placeholder="Enter verification code"
          maxlength="6"
        />
      </div>

      <div class="form-group">
        <label for="new-password">{$i18nStore?.t('new_password') || 'New Password'}</label>
        <input
          type="password"
          id="new-password"
          bind:value={newPassword}
          required
          disabled={isLoading}
          placeholder="Enter new password"
        />
      </div>

      <div class="form-group">
        <label for="confirm-password">{$i18nStore?.t('confirm_password') || 'Confirm Password'}</label>
        <input
          type="password"
          id="confirm-password"
          bind:value={confirmPassword}
          required
          disabled={isLoading}
          placeholder="Confirm new password"
        />
      </div>

      <div class="button-group">
        <button type="button" class="back-button" on:click={goBackToStep1} disabled={isLoading}>
          {$i18nStore?.t('back_button') || 'Back'}
        </button>
        <button type="submit" class="submit-button" disabled={isLoading}>
          {isLoading ? 'Resetting...' : ($i18nStore?.t('reset_password_button') || 'Reset Password')}
        </button>
      </div>
    </form>
  {/if}
</div>

<style>
  .forgot-password-container {
    max-width: 400px;
    margin: 0 auto;
    padding: 2rem;
    background-color: #4a5568;
    color: white;
    border-radius: 8px;
  }

  h2 {
    margin-top: 0;
    margin-bottom: 1.5rem;
    text-align: center;
    color: white;
  }

  .instructions {
    margin-bottom: 1.5rem;
    color: #e2e8f0;
    line-height: 1.5;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    color: white;
  }

  input {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #718096;
    border-radius: 4px;
    background-color: #032b36;
    color: white;
    font-size: 1rem;
    box-sizing: border-box;
  }

  input:focus {
    outline: none;
    border-color: #4299e1;
    box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
  }

  input:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  input::placeholder {
    color: #a0aec0;
  }

  .button-group {
    display: flex;
    gap: 1rem;
    margin-top: 1.5rem;
  }

  .cancel-button,
  .back-button {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #718096;
    background-color: transparent;
    color: white;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
  }

  .cancel-button:hover,
  .back-button:hover {
    background-color: #718096;
  }

  .submit-button {
    flex: 1;
    padding: 0.75rem;
    border: none;
    background-color: #4299e1;
    color: white;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    font-weight: 500;
  }

  .submit-button:hover {
    background-color: #3182ce;
  }

  .cancel-button:disabled,
  .back-button:disabled,
  .submit-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .error {
    background-color: #fed7d7;
    color: #9b2c2c;
    padding: 0.75rem;
    border-radius: 4px;
    margin-bottom: 1rem;
    border: 1px solid #feb2b2;
  }

  .success {
    background-color: #c6f6d5;
    color: #276749;
    padding: 0.75rem;
    border-radius: 4px;
    margin-bottom: 1rem;
    border: 1px solid #9ae6b4;
  }
</style>
