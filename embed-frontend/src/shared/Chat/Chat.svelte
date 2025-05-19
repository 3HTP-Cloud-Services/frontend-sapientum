<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { i18nStore } from '../utils/i18n.js';
  
  // Props to control behavior
  export let isEmbedded = false; // Whether in embedded mode or not
  export let showHeader = true;  // Whether to show the section header
  export let redirectPath = '/login'; // Path to redirect to if unauthorized

  // The actual chat data
  export let messages = [];
  export let userInput = '';
  
  // Binding targets
  let messagesContainer;
  export let activeSectionStore = null;

  // Initialize with welcome message if empty
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

  export function scrollToBottom() {
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  export async function sendMessage() {
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
        push(redirectPath);
      } else {
        console.error('Error from chat API:', response.status);

        let fallbackResponse = $i18nStore?.t('chat_connection_error') || 
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

      let errorMessage = $i18nStore?.t('chat_connection_error') || 
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

  export function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  onMount(() => {
    setTimeout(scrollToBottom, 0);
  });

  // Respond to section changes if we're using activeSectionStore
  $: if (activeSectionStore && $activeSectionStore === 'chat') {
    console.log("Chat section is now active");
    setTimeout(scrollToBottom, 300);
  }
</script>

{#if showHeader && !isEmbedded}
  <!-- In normal mode, show header with title and clear button -->
  <div class="section-header">
    <h2>{$i18nStore?.t('chat_title') || 'Chat'}</h2>
    <div class="chat-buttons">
      <button on:click={() => {messages = [
        {
          id: 1,
          type: 'system',
          content: $i18nStore?.t('ai_welcome') || 'Welcome! How can I help you today?',
          timestamp: new Date()
        }
      ]}} class="clear-button">{$i18nStore?.t('clear_chat') || 'Clear'}</button>
    </div>
  </div>
{/if}

<div class="chat-section" class:embedded-chat={isEmbedded}>
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
  .chat-container {
    display: flex;
    flex-direction: column;
    height: 500px;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .chat-section {
    margin-bottom: 2rem;
  }

  .chat-messages {
    flex: 1;
    padding: 1rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
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

  .chat-buttons {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .clear-button {
    background-color: #a0aec0;
    color: white;
    border: none;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
  }

  /* Section header styling */
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .section-header h2 {
    margin: 0;
    color: #2d3748;
  }
  
  /* Styles for embedded mode */
  .embedded-chat {
    height: 100vh;
    margin: 0;
    padding: 0;
  }
  
  .embedded-chat .chat-container {
    height: 100vh;
    border-radius: 0;
    box-shadow: none;
  }
</style>