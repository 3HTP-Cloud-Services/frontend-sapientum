<script>
  import { link } from 'svelte-spa-router';
  import { logout, isAuthenticated } from '../lib/auth.js';
  import { push } from 'svelte-spa-router';
  import { onMount, onDestroy } from 'svelte';
  import { i18nStore } from '../lib/i18n.js';
  import { writable } from 'svelte/store';
  import { fade, fly } from 'svelte/transition';

  // Import component modules
  import Documents from '../components/Documents.svelte';
  import Permissions from '../components/Permissions.svelte';
  import Chat from '../components/Chat.svelte';

  $: i18n = $i18nStore;
  function setLocale(locale) {
    if ($i18nStore) {
      $i18nStore.locale = locale;
    }
  }

  // Create active section store to share with components
  const activeSectionStore = writable('documents');
  // Active section state
  let activeSection = 'documents';

  // Keep store and local variable in sync
  $: {
    $activeSectionStore = activeSection;
    // When activeSection changes, make sure the components get the memo
    console.log(`Active section changed to ${activeSection}`);
  }

  // Document data
  let documents = [];
  let loading = true;
  let error = '';

  // Document detail data
  let selectedDocument = null;
  let loadingDocument = false;
  let documentError = '';

  // Permissions data
  let users = [];
  let loadingUsers = false;
  let usersError = '';
  let editingUser = null;
  let showUserModal = false;

  // Chat data
  let messages = [
    {
      id: 1,
      type: 'system',
      content: 'Bienvenido al Asistente de IA. ¿Cómo puedo ayudarte hoy?',
      timestamp: new Date(Date.now() - 60000)
    }
  ];
  let userInput = '';
  let chatContainer;
  let messagesContainer;

  // Sidebar state
  let sidebarCollapsed = false;
  let isMobile = false;

  // Check if device is mobile
  function checkMobile() {
    isMobile = window.innerWidth <= 768;
    // On mobile, start with sidebar in collapsed state
    if (isMobile && !sidebarCollapsed) {
      sidebarCollapsed = true;
    }
  }

  // Toggle sidebar visibility
  function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
  }

  // Handle logout
  async function handleLogout() {
    await logout();
    push('/login');
  }

  // Handle section change - just update the section state
  function switchSection(section) {
    console.log(`Switching to section: ${section}`);
    
    // Update section state - components will react to this change
    activeSection = section;
    $activeSectionStore = section;
    
    // No additional logic needed - components handle their own state and data loading
  }

  // Component references
  let documentsComponent;
  let permissionsComponent;
  let chatComponent;

  // No longer fetching data in parent component - each component handles its own data loading

  function scrollToBottom() {
    try {
      if (chatComponent && typeof chatComponent.scrollToBottom === 'function') {
        chatComponent.scrollToBottom();
      } else if (messagesContainer) {
        // Direct access to the container as a fallback
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }
    } catch (err) {
      console.warn('Could not scroll chat to bottom:', err);
    }
  }

  onMount(() => {
    if ($isAuthenticated) {
      // Set initial section (we don't need to fetch data here - components will do it)
      
      // Check if we should activate a specific section (e.g. from redirect)
      const savedSection = localStorage.getItem('activeConsoleSection');
      if (savedSection) {
        activeSection = savedSection;
        $activeSectionStore = savedSection;
        localStorage.removeItem('activeConsoleSection'); // Clear after use
      }
    }

    // Check if mobile on initial load
    checkMobile();

    // Add resize event listener
    window.addEventListener('resize', checkMobile);

    // Cleanup function
    return () => {
      window.removeEventListener('resize', checkMobile);
    };
  });
</script>

<div class="console">
  <header class="console-header">
    <h1>{$i18nStore.t('title')}</h1>
    <div class="header-controls">
      <div>
        <button class={`locale_button en_button ${$i18nStore.locale === 'en' ? 'selected' : ''}`}
                on:click={() => setLocale('en')}>English</button>
        <button class={`locale_button es_button ${$i18nStore.locale === 'es' ? 'selected' : ''}`}
                on:click={() => setLocale('es')}>Español</button>
      </div>
      <button class="logout-button" on:click={handleLogout}>Cerrar Sesión</button>
    </div>
  </header>

  <div class="console-container">
    <nav class="sidebar" class:collapsed={sidebarCollapsed} class:mobile={isMobile}>
      <div class="sidebar-toggle" on:click={toggleSidebar}>
        <span class="toggle-icon">{sidebarCollapsed ? '→' : '←'}</span>
      </div>
      <ul>
        <li class={activeSection === 'documents' || activeSection === 'document-detail' ? 'active' : ''}>
          <button on:click={() => switchSection('documents')}>
            <span class="icon">📄</span>
            <span class="text">Documentos</span>
          </button>
        </li>
        <li class={activeSection === 'permissions' ? 'active' : ''}>
          <button on:click={() => switchSection('permissions')}>
            <span class="icon">🔒</span>
            <span class="text">Permisos</span>
          </button>
        </li>
        <li class={activeSection === 'chat' ? 'active' : ''}>
          <button on:click={() => switchSection('chat')}>
            <span class="icon">💬</span>
            <span class="text">Chat</span>
          </button>
        </li>
      </ul>
    </nav>

    <main class="content" class:expanded={sidebarCollapsed}>
      {#key activeSection}
        <div 
          class="section-wrapper" 
          in:fly={{ x: 150, duration: 250, delay: 100 }} 
          out:fade={{ duration: 100 }}
        >
          {#if activeSection === 'documents' || activeSection === 'document-detail'}
            <Documents
              {documents}
              {loading}
              {error}
              {selectedDocument}
              {loadingDocument}
              {documentError}
              switchSection={switchSection}
              bind:this={documentsComponent}
              activeSectionStore={activeSectionStore}
            />
          {:else if activeSection === 'permissions'}
            <Permissions
              {users}
              {loadingUsers}
              {usersError}
              {editingUser}
              {showUserModal}
              bind:this={permissionsComponent}
              {activeSectionStore}
            />
          {:else if activeSection === 'chat'}
            <Chat
              {messages}
              {userInput}
              {chatContainer}
              {messagesContainer}
              bind:this={chatComponent}
              {activeSectionStore}
            />
          {/if}
        </div>
      {/key}
    </main>
  </div>
</div>

<style>
  .error {
    color: #ff6b6b;
    padding: 1rem;
    background-color: #fee;
    border-radius: 4px;
    margin-bottom: 1rem;
  }

  .console {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    color: #333;
  }
  .console-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
    background-color: #4a5568;
    color: white;
  }

  .console-header h1 {
    margin: 0;
    font-size: 1.5rem;
    margin-right: auto; /* This pushes everything else to the right */
  }

  /* Create a container for the right-aligned elements */
  .console-header .header-controls {
    display: flex;
    align-items: center;
    gap: 12px; /* Space between language buttons and logout */
  }

  /* Base style for locale buttons */
  .locale_button {
    margin: 0 4px;
    color: white;
    background-color: #718096;
    padding: 0.5rem 0.75rem;
    border: 2px solid transparent;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .locale_button.selected {
    background-color: #4a72b3;
    border: 2px solid white;
  }

  .locale_button:hover {
    opacity: 0.9;
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

  .console-container {
    display: flex;
    flex: 1;
    background-color: #f7fafc;
    position: relative;
    overflow-x: hidden; /* Prevent horizontal scrolling */
  }

  .sidebar {
    width: 250px;
    background-color: #2d3748;
    color: white;
    padding: 1rem 0;
    position: relative;
    transition: all 0.3s ease;
  }

  .sidebar.collapsed {
    width: 60px;
  }

  /* Mobile sidebar specific styles */
  .sidebar.mobile {
    position: absolute;
    height: 100%;
    z-index: 100;
  }

  .sidebar.mobile.collapsed {
    width: 60px; /* On mobile, collapsed should be narrow but visible */
    padding: 1rem 0;
    overflow: visible;
  }

  .sidebar-toggle {
    position: absolute;
    top: 10px;
    right: -15px;
    width: 30px;
    height: 30px;
    background-color: #4a5568;
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    box-shadow: 0 0 5px rgba(0, 0, 0, 0.2);
    z-index: 10;
    color: white;
  }

  .toggle-icon {
    font-size: 16px;
    font-weight: bold;
  }

  .sidebar ul {
    list-style-type: none;
    padding: 0;
    margin: 0;
    margin-top: 20px;
  }

  .sidebar li {
    padding: 0;
  }

  .sidebar li button {
    display: flex;
    align-items: center;
    width: 100%;
    text-align: left;
    padding: 0.75rem 1.5rem;
    background: none;
    border: none;
    color: #e2e8f0;
    cursor: pointer;
    font-size: 1rem;
    transition: background-color 0.2s;
    overflow: hidden;
    white-space: nowrap;
  }

  .sidebar li button .icon {
    margin-right: 12px;
    font-size: 1.2rem;
    min-width: 20px;
  }

  .sidebar.collapsed li button .text {
    opacity: 0;
    width: 0;
    display: none;
  }

  .sidebar.collapsed li button {
    padding: 0.75rem;
    justify-content: center;
  }

  .sidebar.collapsed li button .icon {
    margin-right: 0;
    font-size: 1.5rem;
  }

  .sidebar li.active button {
    background-color: #4a5568;
    color: white;
    font-weight: bold;
  }

  .sidebar li button:hover {
    background-color: #4a5568;
  }

  .content {
    flex: 1;
    padding: 2rem;
    overflow: auto;
    transition: all 0.3s ease;
    position: relative;
  }
  
  .section-wrapper {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    padding: 2rem;
    overflow: auto;
    background-color: #f7fafc;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }

  .content.expanded {
    margin-left: 0; /* Don't use negative margin which causes horizontal scroll */
  }

  @media (max-width: 768px) {
    .content.expanded {
      margin-left: 0;
      padding-left: 70px; /* Add padding to avoid content being hidden under sidebar */
    }
  }

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

  .view-all {
    color: #4299e1;
    text-decoration: none;
  }
  /* Mobile optimizations */
  @media (max-width: 768px) {
    .console-header {
      padding: 1rem;
    }

    .console-header h1 {
      font-size: 1.2rem;
    }

    .content {
      padding: 1rem;
    }
  }
</style>
