<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { i18nStore, initializeI18n } from '@shared/utils/i18n.js';
  import { catalogs } from './stores.js';
  import { writable } from 'svelte/store';

  // Track selected catalog
  const selectedCatalog = writable(null);

  export let messages = [];
  export let userInput = '';
  let messagesContainer;
  let catalogsLoaded = false;
  let loadingCatalogs = false;

  $: if (!messages.length && $i18nStore) {
    messages = [
      {
        id: 1,
        type: 'system',
        content: $i18nStore?.t('ai_welcome') || 'Welcome! How can I help you today?',
        timestamp: new Date(Date.now() - 60000)
      }
    ];
  }

  function scrollToBottom() {
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  async function fetchCatalogs() {
    if (catalogsLoaded || loadingCatalogs) return;
    
    loadingCatalogs = true;
    try {
      const response = await fetch('/api/catalogs', {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        catalogs.set(data.catalogs || []);
        
        // Select first catalog by default if available
        if (data.catalogs && data.catalogs.length > 0) {
          selectedCatalog.set(data.catalogs[0]);
        }
        
        catalogsLoaded = true;
      } else if (response.status === 401) {
        push('/embedded/login');
      } else {
        console.error('Error fetching catalogs:', await response.text());
      }
    } catch (error) {
      console.error('Failed to fetch catalogs:', error);
    } finally {
      loadingCatalogs = false;
    }
  }

  async function sendMessage() {
    if (!userInput.trim()) return;

    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      content: userInput,
      timestamp: new Date()
    };

    messages = [...messages, userMessage];

    const messageToSend = userInput;
    userInput = '';

    setTimeout(scrollToBottom, 0);

    try {
      // Include selected catalog in the chat request if available
      const requestBody = { 
        message: messageToSend
      };
      
      const currentCatalog = $selectedCatalog;
      if (currentCatalog) {
        requestBody.catalog_id = currentCatalog.id;
      }
      
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody),
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();

        messages = [...messages, {
          id: messages.length + 1,
          type: 'system',
          content: data.response,
          timestamp: new Date()
        }];

        setTimeout(scrollToBottom, 0);
      } else if (response.status === 401) {
        push('/embedded/login');
      } else {
        console.error('Error from chat API:', response.status);

        let fallbackResponse = $i18nStore.t('chat_connection_error') || 
          "I'm having trouble connecting to the server. Please try again later.";

        messages = [...messages, {
          id: messages.length + 1,
          type: 'system',
          content: fallbackResponse,
          timestamp: new Date()
        }];

        setTimeout(scrollToBottom, 0);
      }
    } catch (error) {
      console.error('Network error when calling chat API:', error);

      let errorMessage = $i18nStore.t('chat_connection_error') || 
        "I'm having trouble connecting to the server. Please try again later.";
      
      messages = [...messages, {
        id: messages.length + 1,
        type: 'system',
        content: errorMessage,
        timestamp: new Date()
      }];

      setTimeout(scrollToBottom, 0);
    }
  }

  function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  function selectCatalog(catalog) {
    selectedCatalog.set(catalog);
    
    // Clear messages and add welcome message when changing catalogs
    messages = [
      {
        id: 1,
        type: 'system',
        content: $i18nStore?.t('ai_welcome') || 'Welcome! How can I help you today?',
        timestamp: new Date()
      }
    ];
  }

  onMount(() => {
    console.log('EmbeddedChat mounted');
    
    fetchCatalogs();
    setTimeout(scrollToBottom, 0);
  });
</script>

<div class="embedded-chat">
  <!-- Catalog tabs -->
  <div class="catalog-tabs">
    {#if loadingCatalogs}
      <div class="loading-catalogs">{$i18nStore?.t('loading') || 'Loading catalogs...'}</div>
    {:else if $catalogs && $catalogs.length > 0}
      {#each $catalogs as catalog}
        <button 
          class="catalog-tab {$selectedCatalog?.id === catalog.id ? 'active' : ''}"
          on:click={() => selectCatalog(catalog)}
        >
          {catalog.name}
        </button>
      {/each}
    {:else}
      <div class="no-catalogs">{$i18nStore?.t('no_catalogs') || 'No catalogs available'}</div>
    {/if}
  </div>

  <!-- Chat interface -->
  <div class="chat-container">
    <div class="chat-messages" bind:this={messagesContainer}>
      {#each messages as message (message.id)}
        <div class={`message ${message.type}`}>
          <div class="message-content">{message.content}</div>
          <div class="message-time">{message.timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
        </div>
      {/each}
    </div>
    <div class="chat-input">
      <textarea
        placeholder={$i18nStore?.t('chat_placeholder') || 'Type your message...'}
        bind:value={userInput}
        on:keydown={handleKeydown}
      ></textarea>
      <button class="send-button" on:click={sendMessage} disabled={!userInput.trim()}>
        {$i18nStore?.t('send_button') || 'Send'}
      </button>
    </div>
  </div>
</div>

<style>
  .embedded-chat {
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100%;
    background-color: #f8f9fa;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 9999;
  }

  .catalog-tabs {
    display: flex;
    overflow-x: auto;
    background-color: #4a5568;
    padding: 0.5rem 0.5rem 0;
    gap: 0.25rem;
  }

  .catalog-tab {
    background-color: #718096;
    color: white;
    border: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    padding: 0.5rem 1rem;
    cursor: pointer;
    white-space: nowrap;
    border-bottom: 2px solid transparent;
  }

  .catalog-tab.active {
    background-color: #f8f9fa;
    color: #2d3748;
    font-weight: bold;
  }

  .loading-catalogs, .no-catalogs {
    color: white;
    padding: 0.5rem 1rem;
    font-style: italic;
  }

  .chat-container {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
  }

  .chat-messages {
    flex: 1;
    padding: 1rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    background-color: #f8f9fa;
  }

  .message {
    max-width: 80%;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    position: relative;
    margin-bottom: 0.5rem;
  }

  .message.system {
    align-self: flex-start;
    background-color: #edf2f7;
    color: #2d3748;
  }

  .message.user {
    align-self: flex-end;
    background-color: #4299e1;
    color: white;
  }

  .message-time {
    font-size: 0.75rem;
    margin-top: 0.25rem;
    opacity: 0.7;
    text-align: right;
  }

  .chat-input {
    display: flex;
    padding: 1rem;
    background-color: #edf2f7;
    border-top: 1px solid #e2e8f0;
  }

  .chat-input textarea {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    resize: none;
    height: 40px;
    font-family: inherit;
  }

  .send-button {
    margin-left: 0.5rem;
    background-color: #4299e1;
    color: white;
    border: none;
    padding: 0 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 40px;
    text-decoration: none;
    min-width: 80px;
  }

  .send-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  
  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    width: 100%;
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