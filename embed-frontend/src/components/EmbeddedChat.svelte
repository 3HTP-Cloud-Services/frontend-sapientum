<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { i18nStore, initializeI18n } from '@shared/utils/i18n.js';

  import { writable } from 'svelte/store';
  import { logout , isAuthenticated } from '../lib/auth.js';

  export let messages = [];
  export let userInput = '';
  let messagesContainer;

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

  export let handleLogout = async () => {
    try {
      // Create and dispatch a custom event before logging out
      const logoutEvent = new CustomEvent('app-logout');
      window.dispatchEvent(logoutEvent);
      
      // Perform the actual logout API call
      await logout();
      
      // Use window.location for a hard redirect
      window.location.hash = '/login';
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  function setLocale(locale) {
    if ($i18nStore) {
      $i18nStore.locale = locale;
    }
  }

  function scrollToBottom() {
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
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
      // Simple request with just the message
      const requestBody = {
        message: messageToSend
      };

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

  onMount(() => {
    console.log('EmbeddedChat mounted');
    setTimeout(scrollToBottom, 0);
  });
</script>

<div class="embedded-chat">
  <div class="chat-header">
    <h2>{$i18nStore?.t('chat_title') || 'Chat'}</h2>

    <div class="language-selector">
      <button class={`locale-button ${$i18nStore.locale === 'en' ? 'selected' : ''}`}
              on:click={() => setLocale('en')}>English</button>
      <button class={`locale-button ${$i18nStore.locale === 'es' ? 'selected' : ''}`}
              on:click={() => setLocale('es')}>Español</button>
    </div>
    <div class="logout-container">
      <button class="logout-button" on:click={handleLogout}>{$i18nStore?.t('logout') || 'Logout'}</button>
    </div>
  </div>

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
  .chat-header {
    display: flex;
    flex-direction: row;
    align-items: center;
    background-color: #4a5568;
    padding: 0.75rem 1rem;
    color: white;
  }

  .chat-header h2 {
    margin: 0;
    font-size: 1.25rem;
    flex: 1;
  }

  .language-selector {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0;
    margin-right: 1rem;
  }

  .logout-container {
    min-width: 150px; /* Adjust this value based on your largest text */
  }

  .logout-button {
    background-color: #e53e3e;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
  }

  .locale-button {
    margin: 0 4px;
    color: white;
    background-color: #718096;
    padding: 0.5rem 0.75rem;
    border: 2px solid transparent;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .locale-button.selected {
    background-color: #4a72b3;
    border: 2px solid white;
  }

  .locale-button:hover {
    opacity: 0.9;
  }

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
