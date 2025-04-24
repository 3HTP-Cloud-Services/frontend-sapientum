<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { i18nStore } from '../lib/i18n.js';

  // Chat data - initialize with translated welcome message
  export let messages = [];
  
  $: if (!messages.length && $i18nStore) {
    messages = [
      {
        id: 1,
        type: 'system',
        content: $i18nStore.t('ai_welcome'),
        timestamp: new Date(Date.now() - 60000)
      }
    ];
  }
  export let userInput = '';
  export let chatContainer;
  export let messagesContainer;
  export let activeSectionStore;

  // Function to scroll chat to bottom
  export function scrollToBottom() {
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  // Function to send a chat message
  export async function sendMessage() {
    if (!userInput.trim()) return;

    // Add user message
    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      content: userInput,
      timestamp: new Date()
    };

    messages = [...messages, userMessage];

    // Clear input and store the message for sending
    const messageToSend = userInput;
    userInput = '';

    // Scroll to bottom after rendering user message
    setTimeout(scrollToBottom, 0);

    try {
      // Call the backend API
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: messageToSend }),
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();

        // Add AI response
        messages = [...messages, {
          id: messages.length + 1,
          type: 'system',
          content: data.response,
          timestamp: new Date()
        }];

        // Scroll to bottom after rendering AI response
        setTimeout(scrollToBottom, 0);
      } else if (response.status === 401) {
        // User is not authenticated
        push('/login');
      } else {
        // Fall back to client-side response if API fails
        console.error('Error from chat API:', response.status);

        // Use fallback responses
        let fallbackResponse = "Estoy teniendo problemas para conectarme al servidor. Por favor, inténtalo más tarde.";

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

      // Handle network errors with fallback
      messages = [...messages, {
        id: messages.length + 1,
        type: 'system',
        content: "Estoy teniendo problemas para conectarme al servidor. Por favor, inténtalo más tarde.",
        timestamp: new Date()
      }];

      setTimeout(scrollToBottom, 0);
    }
  }

  // Handle key press for chat input
  export function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  onMount(() => {
    // Scroll chat to bottom on initial load
    setTimeout(scrollToBottom, 0);
  });
  
  // Watch for section changes to scroll chat to bottom when active
  $: if ($activeSectionStore === 'chat') {
    console.log("Chat section is now active");
    setTimeout(scrollToBottom, 300);
  }
</script>

<div class="section-header">
  <h2>{$i18nStore.t('chat_title')}</h2>
  <div class="chat-buttons">
    <button on:click={() => {messages = [
      {
        id: 1,
        type: 'system',
        content: $i18nStore.t('ai_welcome'),
        timestamp: new Date()
      }
    ]}} class="clear-button">{$i18nStore.t('clear_chat')}</button>
  </div>
</div>
<div class="chat-section">
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
        placeholder={$i18nStore.t('chat_placeholder')}
        bind:value={userInput}
        on:keydown={handleKeydown}
      ></textarea>
      <button class="send-button" on:click={sendMessage} disabled={!userInput.trim()}>{$i18nStore.t('send_button')}</button>
    </div>
  </div>
</div>
<style>

  /* Chat section */
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

</style>
