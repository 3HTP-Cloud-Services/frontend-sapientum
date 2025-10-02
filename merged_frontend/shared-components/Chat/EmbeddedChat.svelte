<script>
  import { push } from 'svelte-spa-router';
  import { onMount, afterUpdate, tick } from 'svelte';
  import { i18nStore, initializeI18n } from '../utils/i18n.js';

  import { writable } from 'svelte/store';
  import { logout , isAuthenticated } from '../utils/auth.js';
  import { httpCall } from '../utils/httpCall.js';

  import Header from '../Header/Header.svelte';
  import DownloadDialog from './DownloadDialog.svelte';

  export let isEmbedded = true;

  export const catalogsStore = writable([]);

  // Change to a map of catalog ID -> messages array
  export const messagesByCatalog = writable({});
  export let userInput = '';

  let selectedCatalogId = null;
  let messagesContainer;
  let downloadDialog;
  let showDownloadDialog = false;
  let lastScrollCatalogId = null;
  let lastScrollMessageCount = 0;

  let showTracePopup = false;
  let traceData = null;
  let loadingTrace = false;
  let traceError = null;

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
          timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
          has_trace: msg.has_trace || false
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

        console.log('Messages loaded for catalog', catalogId, 'count:', formattedMessages.length);

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

    }
  }

  function selectCatalog(id) {
    console.log('selectCatalog clicked', id, 'has messages:', !!$messagesByCatalog[id]);
    selectedCatalogId = id;
    if (!$messagesByCatalog[id]) {
      console.log('Loading messages for catalog', id);
      loadConversationMessages(id);
    } else {
      console.log('Catalog already has messages, count:', $messagesByCatalog[id].length);
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

  $: currentMessages = selectedCatalogId ? ($messagesByCatalog[selectedCatalogId] || []) : [];

  afterUpdate(() => {
    if (messagesContainer && currentMessages.length > 0) {
      const catalogChanged = lastScrollCatalogId !== selectedCatalogId;
      const messagesChanged = lastScrollMessageCount !== currentMessages.length;

      console.log('afterUpdate fired', {
        catalogChanged,
        messagesChanged,
        messageCount: currentMessages.length,
        scrollHeight: messagesContainer?.scrollHeight,
        scrollTop: messagesContainer?.scrollTop,
        selectedCatalogId
      });

      if (catalogChanged || messagesChanged) {
        lastScrollCatalogId = selectedCatalogId;
        lastScrollMessageCount = currentMessages.length;

        requestAnimationFrame(() => {
          console.log('Before scroll:', {
            scrollTop: messagesContainer.scrollTop,
            scrollHeight: messagesContainer.scrollHeight,
            clientHeight: messagesContainer.clientHeight,
            offsetHeight: messagesContainer.offsetHeight,
            maxScroll: messagesContainer.scrollHeight - messagesContainer.clientHeight
          });
          messagesContainer.scrollTop = messagesContainer.scrollHeight;
          console.log('After scroll:', {
            scrollTop: messagesContainer.scrollTop,
            scrollHeight: messagesContainer.scrollHeight
          });
        });
      }
    }
  });

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

  async function scrollToBottomAsync() {
    await tick();
    setTimeout(scrollToBottom, 50);
  }

  export { scrollToBottom };

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
    }
  }

  function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  async function showTrace(messageId) {
    showTracePopup = true;
    loadingTrace = true;
    traceError = null;
    traceData = null;

    try {
      const response = await httpCall(`/api/messages/${messageId}/trace`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        traceData = data.trace;
      } else {
        const errorData = await response.json();
        traceError = errorData.error || 'Failed to load trace data';
      }
    } catch (error) {
      console.error('Error fetching trace data:', error);
      traceError = 'Network error occurred while fetching trace data';
    } finally {
      loadingTrace = false;
    }
  }

  function closeTracePopup() {
    showTracePopup = false;
    traceData = null;
    traceError = null;
    loadingTrace = false;
  }

  function openDownloadDialog() {
    if (!selectedCatalogId) return;
    showDownloadDialog = true;
  }

  function closeDownloadDialog() {
    showDownloadDialog = false;
  }

  async function handleDownload(event) {
    const messageCount = event.detail.messageCount;

    try {
      const response = await httpCall(`/api/conversations/${selectedCatalogId}/download-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message_count: messageCount
        }),
        credentials: 'include'
      });

      if (response.ok) {
        // Get the filename from Content-Disposition header
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'conversation.pdf';
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="(.+)"/);
          if (filenameMatch) {
            filename = filenameMatch[1];
          }
        }

        // Create blob and download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(link);

        // Close dialog and reset download state
        downloadDialog.setDownloading(false);
        closeDownloadDialog();
      } else {
        const errorData = await response.json();
        downloadDialog.setError(errorData.error || 'Failed to download conversation');
      }
    } catch (error) {
      console.error('Error downloading conversation:', error);
      downloadDialog.setError('Network error occurred while downloading');
    }
  }

  // Get current catalog name for display
  $: currentCatalogName = selectedCatalogId ?
    ($catalogsStore.find(c => c.id === selectedCatalogId)?.name || 'Unknown Catalog') :
    '';

  onMount(async () => {
    console.log('EmbeddedChat mounted');

    try {
      // Load catalogs and conversations asynchronously
      const catalogsResponse = await httpCall('/api/catalogs?for_chat=true', {
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

  });
</script>

<div class={ isEmbedded? 'embedded-chat' : 'chat-wrapper' }>
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

  <div class="chat-messages" bind:this={messagesContainer}>
    {#if selectedCatalogId && $messagesByCatalog[selectedCatalogId]}
      {#each $messagesByCatalog[selectedCatalogId] as message (message.id)}
        <div class={`message ${message.type}`}>
          <div class="message-content">{@html message.content}</div>
          <div class="message-meta">
            <div class="message-time">{message.timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
            {#if message.has_trace}
              <div class="trace-indicator" title="Click to view trace data" on:click={() => showTrace(message.id)}>i</div>
            {/if}
          </div>
        </div>
      {/each}
    {:else}
      <div class="no-catalog-selected">
        {$i18nStore?.t('select_catalog') || 'Please select a catalog to start chatting'}
      </div>
    {/if}
  </div>

  <div class="chat-input">
    <div class="input-row">
      <textarea
              placeholder={$i18nStore?.t('chat_placeholder') || 'Type your message...'}
              bind:value={userInput}
              on:keydown={handleKeydown}
              disabled={!selectedCatalogId}
      ></textarea>
      <div class="button-column">
        <button class="send-button" on:click={sendMessage} disabled={!userInput.trim() || !selectedCatalogId}>
          {$i18nStore?.t('send_button') || 'Send'}
        </button>
        <button class="download-conversation-button" on:click={openDownloadDialog} disabled={!selectedCatalogId}>
          📄 {$i18nStore?.t('download_conversation') || 'Download Conversation'}
        </button>
      </div>
    </div>
  </div>
</div>

<!-- Download Dialog -->
<DownloadDialog
  bind:this={downloadDialog}
  bind:isVisible={showDownloadDialog}
  catalogName={currentCatalogName}
  on:close={closeDownloadDialog}
  on:download={handleDownload}
/>

<!-- Trace Popup -->
{#if showTracePopup}
  <div class="trace-popup-overlay" on:click={closeTracePopup}>
    <div class="trace-popup" on:click|stopPropagation>
      <div class="trace-popup-header">
        <h3>Trace Data</h3>
        <button class="close-button" on:click={closeTracePopup}>&times;</button>
      </div>
      <div class="trace-popup-content">
        {#if loadingTrace}
          <div class="trace-loading">Loading trace data...</div>
        {:else if traceError}
          <div class="trace-error">Error: {traceError}</div>
        {:else if traceData}
          <pre class="trace-data">{JSON.stringify(traceData, null, 2)}</pre>
        {/if}
      </div>
    </div>
  </div>
{/if}

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

  .chat-wrapper {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    background-color: #f8f9fa;
  }

  .chat-messages {
    flex: 1;
    padding: 1rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    background-color: #f8f9fa;
    min-height: 0;
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
    color: #032b36;
  }

  .message.user {
    align-self: flex-end;
    background-color: #4299e1;
    color: white;
  }

  .message-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 0.25rem;
  }

  .message-time {
    font-size: 0.75rem;
    opacity: 0.7;
  }

  .trace-indicator {
    font-size: 0.75rem;
    font-weight: bold;
    background-color: rgba(0, 0, 0, 0.1);
    color: #4a5568;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-style: italic;
    transition: background-color 0.2s ease;
  }

  .trace-indicator:hover {
    background-color: rgba(0, 0, 0, 0.2);
  }

  .message.system .trace-indicator {
    background-color: rgba(0, 0, 0, 0.1);
    color: #4a5568;
  }

  .message.user .trace-indicator {
    background-color: rgba(255, 255, 255, 0.2);
    color: white;
  }

  .message-content a {
    color: #2b6cb0;
    text-decoration: underline;
    font-weight: 500;
    transition: color 0.2s ease;
  }

  .message-content a:hover {
    color: #1a365d;
    text-decoration: none;
  }

  .message.user .message-content a {
    color: #bee3f8;
  }

  .message.user .message-content a:hover {
    color: #ffffff;
  }

  .chat-input {
    display: flex;
    flex-direction: column;
    padding: 1rem;
    background-color: #edf2f7;
    border-top: 1px solid #e2e8f0;
  }

  .input-row {
    display: flex;
    gap: 0.5rem;
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

  .button-column {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .download-conversation-button {
    background-color: #2fd66f;
    color: white;
    border: none;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 24px;
    text-decoration: none;
    font-size: 0.75rem;
    transition: background-color 0.2s ease;
    gap: 0.25rem;
    min-width: 80px;
  }

  .download-conversation-button:hover:not(:disabled) {
    background-color: #48bb78;
  }

  .download-conversation-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .send-button {
    background-color: #112fff;
    color: white;
    border: none;
    padding: 0 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 48px;
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

  /* Trace Popup Styles */
  .trace-popup-overlay {
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

  .trace-popup {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    width: 92vh;
    height: 92vh;
    display: flex;
    flex-direction: column;
  }

  .trace-popup-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid #e2e8f0;
    background-color: #f8f9fa;
    border-radius: 8px 8px 0 0;
  }

  .trace-popup-header h3 {
    margin: 0;
    color: #032b36;
    font-size: 1.25rem;
  }

  .close-button {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #718096;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: background-color 0.2s ease;
  }

  .close-button:hover {
    background-color: #e2e8f0;
    color: #4a5568;
  }

  .trace-popup-content {
    padding: 1rem;
    overflow: auto;
    flex: 1;
  }

  .trace-loading {
    text-align: center;
    color: #718096;
    padding: 2rem;
  }

  .trace-error {
    color: #e53e3e;
    padding: 1rem;
    background-color: #fed7d7;
    border: 1px solid #feb2b2;
    border-radius: 4px;
  }

  .trace-data {
    background-color: #f7fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 1rem;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-x: auto;
    margin: 0;
  }
</style>
