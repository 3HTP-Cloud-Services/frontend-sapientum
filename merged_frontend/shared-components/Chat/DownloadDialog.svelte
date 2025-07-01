<script>
  import { createEventDispatcher } from 'svelte';
  import { i18nStore } from '../utils/i18n.js';

  export let isVisible = false;
  export let catalogName = '';
  
  const dispatch = createEventDispatcher();
  
  let messageCount = 20;
  let isDownloading = false;
  let errorMessage = '';

  function closeDialog() {
    isVisible = false;
    messageCount = 20;
    errorMessage = '';
    dispatch('close');
  }

  function handleDownload() {
    if (messageCount <= 0) {
      errorMessage = $i18nStore?.t('download_error_positive') || 'Please enter a positive number';
      return;
    }
    
    errorMessage = '';
    isDownloading = true;
    
    dispatch('download', {
      messageCount: messageCount
    });
  }

  function handleKeydown(event) {
    if (event.key === 'Escape') {
      closeDialog();
    } else if (event.key === 'Enter') {
      handleDownload();
    }
  }

  export function setDownloading(downloading) {
    isDownloading = downloading;
  }

  export function setError(error) {
    errorMessage = error;
    isDownloading = false;
  }
</script>

{#if isVisible}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="modal-overlay" on:click={closeDialog}>
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="modal-content" on:click|stopPropagation>
      <div class="modal-header">
        <h3>{$i18nStore?.t('download_conversation') || 'Download Conversation'}</h3>
        <button class="close-button" on:click={closeDialog}>&times;</button>
      </div>
      
      <div class="modal-body">
        <p class="catalog-info">
          {$i18nStore?.t('downloading_from') || 'Downloading conversation from'}: 
          <strong>{catalogName}</strong>
        </p>
        
        <div class="input-group">
          <label for="messageCount">
            {$i18nStore?.t('number_of_messages') || 'Number of messages to include'}:
          </label>
          <input 
            id="messageCount"
            type="number" 
            bind:value={messageCount} 
            min="1" 
            max="1000"
            on:keydown={handleKeydown}
            disabled={isDownloading}
          />
          <small class="help-text">
            {$i18nStore?.t('download_help_text') || 'Enter the number of recent messages to include in the PDF (default: 20)'}
          </small>
        </div>
        
        {#if errorMessage}
          <div class="error-message">
            {errorMessage}
          </div>
        {/if}
      </div>
      
      <div class="modal-footer">
        <button class="cancel-button" on:click={closeDialog} disabled={isDownloading}>
          {$i18nStore?.t('cancel') || 'Cancel'}
        </button>
        <button class="download-button" on:click={handleDownload} disabled={isDownloading}>
          {#if isDownloading}
            <span class="spinner"></span>
            {$i18nStore?.t('downloading') || 'Downloading...'}
          {:else}
            {$i18nStore?.t('download') || 'Download PDF'}
          {/if}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
  }

  .modal-content {
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    max-width: 500px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #e2e8f0;
  }

  .modal-header h3 {
    margin: 0;
    color: #2d3748;
    font-size: 1.25rem;
  }

  .close-button {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #a0aec0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.2s ease;
  }

  .close-button:hover {
    background-color: #f7fafc;
    color: #4a5568;
  }

  .modal-body {
    padding: 1.5rem;
  }

  .catalog-info {
    margin-bottom: 1.5rem;
    color: #4a5568;
    font-size: 0.95rem;
  }

  .input-group {
    margin-bottom: 1rem;
  }

  .input-group label {
    display: block;
    margin-bottom: 0.5rem;
    color: #2d3748;
    font-weight: 500;
  }

  .input-group input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    font-size: 1rem;
    transition: border-color 0.2s ease;
  }

  .input-group input:focus {
    outline: none;
    border-color: #4299e1;
    box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
  }

  .input-group input:disabled {
    background-color: #f7fafc;
    color: #a0aec0;
    cursor: not-allowed;
  }

  .help-text {
    display: block;
    margin-top: 0.5rem;
    color: #718096;
    font-size: 0.875rem;
  }

  .error-message {
    background-color: #fed7d7;
    color: #c53030;
    padding: 0.75rem;
    border-radius: 4px;
    margin-top: 1rem;
    font-size: 0.875rem;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    padding: 1rem 1.5rem;
    border-top: 1px solid #e2e8f0;
    background-color: #f7fafc;
  }

  .cancel-button {
    padding: 0.75rem 1.5rem;
    background-color: #edf2f7;
    color: #4a5568;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.2s ease;
  }

  .cancel-button:hover:not(:disabled) {
    background-color: #e2e8f0;
  }

  .cancel-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .download-button {
    padding: 0.75rem 1.5rem;
    background-color: #4299e1;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: all 0.2s ease;
  }

  .download-button:hover:not(:disabled) {
    background-color: #3182ce;
  }

  .download-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid transparent;
    border-top: 2px solid currentColor;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
</style>