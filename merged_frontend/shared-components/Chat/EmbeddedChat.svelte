<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { i18nStore, initializeI18n } from '../utils/i18n.js';

  import { writable } from 'svelte/store';
  import { logout , isAuthenticated } from '../utils/auth.js';
  import { httpCall } from '../utils/httpCall.js';

  import Header from '../Header/Header.svelte';

  export let isEmbedded = true;

  export const catalogsStore = writable([]);

  // Change to a map of catalog ID -> messages array
  export const messagesByCatalog = writable({});
  export let userInput = '';

  let selectedCatalogId = null;
  let messagesContainer;

  async function loadConversationMessages(catalogId) {
    try {
      const response = await httpCall(`/api/conversations/${catalogId}`, {
        credentials: 'include'
      });

      if (response.ok) {
        const messages = await response.json();
        
        // Convert timestamps and add proper message structure
        const formattedMessages = messages.map(msg => ({
          id: msg.id,
          type: msg.type,
          content: msg.content,
          timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date()
        }));

        // If no messages exist, add welcome message
        if (formattedMessages.length === 0) {
          formattedMessages.push({
            id: 1,
            type: 'system',
            content: $i18nStore?.t('ai_welcome') || 'Welcome! How can I help you today?',
            timestamp: new Date(Date.now() - 60000)
          });
        }

        messagesByCatalog.update(msgs => ({
          ...msgs,
          [catalogId]: formattedMessages
        }));

        // Scroll to bottom after messages are loaded, but only for the currently selected catalog
        if (catalogId === selectedCatalogId) {
          setTimeout(scrollToBottom, 100);
        }
      } else {
        console.error('Error loading conversation messages:', response.status);
        // Fallback to welcome message
        const welcomeMessage = {
          id: 1,
          type: 'system',
          content: $i18nStore?.t('ai_welcome') || 'Welcome! How can I help you today?',
          timestamp: new Date(Date.now() - 60000)
        };

        messagesByCatalog.update(msgs => ({
          ...msgs,
          [catalogId]: [welcomeMessage]
        }));

        // Scroll to bottom after welcome message, but only for the currently selected catalog
        if (catalogId === selectedCatalogId) {
          setTimeout(scrollToBottom, 100);
        }
      }
    } catch (error) {
      console.error('Error loading conversation messages:', error);
      // Fallback to welcome message
      const welcomeMessage = {
        id: 1,
        type: 'system',
        content: $i18nStore?.t('ai_welcome') || 'Welcome! How can I help you today?',
        timestamp: new Date(Date.now() - 60000)
      };

      messagesByCatalog.update(msgs => ({
        ...msgs,
        [catalogId]: [welcomeMessage]
      }));

      // Scroll to bottom after welcome message, but only for the currently selected catalog
      if (catalogId === selectedCatalogId) {
        setTimeout(scrollToBottom, 100);
      }
    }
  }

  function selectCatalog(id) {
    selectedCatalogId = id;
    // Load conversation messages for this catalog if they don't exist
    if (!$messagesByCatalog[id]) {
      loadConversationMessages(id);
    } else {
      // If messages already exist, scroll to bottom immediately
      setTimeout(scrollToBottom, 50);
    }
  }

  // Initialize the first catalog when data loads and preload conversations for all catalogs
  $: if ($catalogsStore.length && selectedCatalogId === null) {
    // Select the first catalog
    selectCatalog($catalogsStore[0]?.id);
    
    // Preload conversation messages for all catalogs asynchronously
    $catalogsStore.forEach(catalog => {
      if (!$messagesByCatalog[catalog.id]) {
        loadConversationMessages(catalog.id);
      }
    });
  }

  // Current messages for the selected catalog
  $: currentMessages = selectedCatalogId ? ($messagesByCatalog[selectedCatalogId] || []) : [];

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
    if (!userInput.trim() || !selectedCatalogId) return;

    // Generate a temporary ID for optimistic updates (will be replaced by real DB ID)
    const tempId = Date.now();
    const userMessage = {
      id: tempId,
      type: 'user',
      content: userInput,
      timestamp: new Date()
    };

    // Optimistically add user message to UI
    messagesByCatalog.update(msgs => ({
      ...msgs,
      [selectedCatalogId]: [...(msgs[selectedCatalogId] || []), userMessage]
    }));

    const messageToSend = userInput;
    userInput = '';

    setTimeout(scrollToBottom, 0);

    try {
      const requestBody = {
        conversation: -1,
        message: messageToSend,
        catalogId: selectedCatalogId
      };

      const response = await httpCall('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody),
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();

        // Add AI response
        const aiMessage = {
          id: Date.now() + 1, // Temporary ID
          type: 'system',
          content: data.response,
          timestamp: new Date()
        };

        messagesByCatalog.update(msgs => {
          const catalogMessages = msgs[selectedCatalogId] || [];
          return {
            ...msgs,
            [selectedCatalogId]: [...catalogMessages, aiMessage]
          };
        });

        setTimeout(scrollToBottom, 0);
        
        // Reload conversation to get real IDs from database
        setTimeout(() => {
          loadConversationMessages(selectedCatalogId);
        }, 100);
        
      } else if (response.status === 401) {
        push('/embedded/login');
      } else {
        console.error('Error from chat API:', response.status);

        let fallbackResponse = $i18nStore.t('chat_connection_error') ||
                "I'm having trouble connecting to the server. Please try again later.";

        const errorMessage = {
          id: Date.now() + 1,
          type: 'system',
          content: fallbackResponse,
          timestamp: new Date()
        };

        messagesByCatalog.update(msgs => {
          const catalogMessages = msgs[selectedCatalogId] || [];
          return {
            ...msgs,
            [selectedCatalogId]: [...catalogMessages, errorMessage]
          };
        });

        setTimeout(scrollToBottom, 0);
      }
    } catch (error) {
      console.error('Network error when calling chat API:', error);

      let errorMessage = $i18nStore.t('chat_connection_error') ||
              "I'm having trouble connecting to the server. Please try again later.";

      const errorMsg = {
        id: Date.now() + 1,
        type: 'system',
        content: errorMessage,
        timestamp: new Date()
      };

      messagesByCatalog.update(msgs => {
        const catalogMessages = msgs[selectedCatalogId] || [];
        return {
          ...msgs,
          [selectedCatalogId]: [...catalogMessages, errorMsg]
        };
      });

      setTimeout(scrollToBottom, 0);
    }
  }

  function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  onMount(async () => {
    console.log('EmbeddedChat mounted');

    try {
      // Load catalogs and conversations asynchronously
      const catalogsResponse = await httpCall('/api/catalogs', {
        credentials: 'include'
      });

      if (catalogsResponse.ok) {
        const catalogs = await catalogsResponse.json();
        catalogsStore.set(catalogs);
        
        // The reactive statement will handle catalog selection and conversation loading
      } else {
        console.error('Error fetching catalogs:', catalogsResponse.status, catalogsResponse.statusText);
      }
    } catch (error) {
      console.error('Error in onMount:', error);
    }

    setTimeout(scrollToBottom, 0);
  });
</script>

<div class={ isEmbedded? 'embedded-chat' : '' }>
  {#if isEmbedded}
  <Header handleLogout={handleLogout} title="Sapientum Chat" />
  {/if}

  <div class="catalog-list">
    {#each $catalogsStore as catalog (catalog.id)}
      <div class="catalog {selectedCatalogId === catalog.id ? 'active' : ''}"
           on:click={() => selectCatalog(catalog.id)}
      >
        {catalog.name}
      </div>
    {/each}
  </div>

  <div class="chat-container">
    <!-- Show messages only for the selected catalog -->
    <div class="chat-messages" bind:this={messagesContainer}>
      {#if selectedCatalogId && $messagesByCatalog[selectedCatalogId]}
        {#each $messagesByCatalog[selectedCatalogId] as message (message.id)}
          <div class={`message ${message.type}`}>
            <div class="message-content">{message.content}</div>
            <div class="message-time">{message.timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
          </div>
        {/each}
      {:else}
        <div class="no-catalog-selected">
          {$i18nStore?.t('select_catalog') || 'Please select a catalog to start chatting'}
        </div>
      {/if}
    </div>
    <div class="chat-input">
      <textarea
              placeholder={$i18nStore?.t('chat_placeholder') || 'Type your message...'}
              bind:value={userInput}
              on:keydown={handleKeydown}
              disabled={!selectedCatalogId}
      ></textarea>
      <button class="send-button" on:click={sendMessage} disabled={!userInput.trim() || !selectedCatalogId}>
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
  .catalog-list {
    padding-left: 0.7rem;
    display: flex;
    /* background-color: #556072; */
    background: linear-gradient(to bottom, #4A5568, #556072);
    border-bottom: 1px solid #e2e8f0;
    overflow-x: auto;
    padding-top: 0.7rem;
  }

  .catalog {
    padding: 0.5rem 1rem;
    margin-right: 0.25rem;
    border-radius: 0.25rem 0.25rem 0 0;
    cursor: pointer;
    background-color: #718096;
    color: white;
    transition: background-color 0.2s ease;
    white-space: nowrap;
    user-select: none;
  }

  .catalog:hover {
    background-color: #606A8B;
  }

  .catalog.active {
    background-color: #4a72b3;
    color: white;
    border: 1px solid #e2e8f0;
    border-bottom: none;
    position: relative;
  }

  .catalog.active::after {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 0;
    right: 0;
    height: 1px;
    background-color: #fff;
  }

  .no-catalog-selected {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #a0aec0;
    font-style: italic;
  }
</style>
