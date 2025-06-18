<script>
  import { link } from 'svelte-spa-router';
  import { logout, isAuthenticated, userRole } from '../../../shared-components/utils/auth.js';
  import { push } from 'svelte-spa-router';
  import { onMount, onDestroy } from 'svelte';
  import { i18nStore, setLocale } from '../../../shared-components/utils/i18n.js';
  import { writable } from 'svelte/store';
  import { fade, fly } from 'svelte/transition';

  // Import shared components
  import Header from '../../../shared-components/Header/Header.svelte'
  
  let headerComponent;

  // Store for passing catalog ID between components
  const currentCatalogIdStore = writable(null);

  import Catalog from '../components/Catalog.svelte';
  import Catalog_Permissions from '../components/Catalog_Permissions.svelte';
  import Permissions from '../components/Permissions.svelte';
  import ActivityLog from '../components/ActivityLog.svelte';
  import Chat from '../../../shared-components/Chat/EmbeddedChat.svelte';
  import { catalogsStore, loadingStore, errorStore, fetchCatalogs } from '../components/stores.js';

  $: i18n = $i18nStore;

  const activeSectionStore = writable('chat');
  // Active section state
  let activeSection = 'chat';

  $: {
    $activeSectionStore = activeSection;
    console.log(`Active section changed to ${activeSection}`);
  }

  // Flag to determine if catalog menu should be shown
  let showCatalogMenu = false;

  // Flag to track if user has explicitly selected a section
  let userSelectedSection = false;

  // Update showCatalogMenu when catalogs are loaded
  $: {
    if (!$loadingStore) {
      showCatalogMenu = $catalogsStore && $catalogsStore.length > 0;
      console.log(`Catalog menu visibility: ${showCatalogMenu} (${$catalogsStore.length} catalogs)`);

      // Only auto-switch to catalogs if user hasn't explicitly selected a section yet
      if (activeSection === 'chat' && !userSelectedSection && ($userRole === 'admin' || showCatalogMenu)) {
        activeSection = 'catalogs';
        $activeSectionStore = 'catalogs';
      }
    }
  }

  let catalogs = [];
  let loading = true;
  let error = '';

  let selectedCatalog = null;
  let loadingCatalog = false;
  let catalogError = '';

  let users = [];
  let loadingUsers = false;
  let usersError = '';
  let editingUser = null;
  let showUserModal = false;

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

  let sidebarCollapsed = false;
  let isMobile = false;

  function checkMobile() {
    isMobile = window.innerWidth <= 768;
    if (isMobile && !sidebarCollapsed) {
      sidebarCollapsed = true;
    }
  }

  function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
  }

  async function handleLogout() {
    await logout();
    push('/login');
  }

  function switchSection(section) {
    console.log(`Switching to section: ${section}`);

    // Mark that user has explicitly selected a section
    userSelectedSection = true;

    activeSection = section;
    $activeSectionStore = section;
  }

  function handleLogoUploaded() {
    // Refresh the header logo when logo is uploaded in permissions
    if (headerComponent) {
      headerComponent.refreshLogo();
    }
  }

  let catalogComponent;
  let catalogPermissionsComponent;
  let permissionsComponent;
  let chatComponent;
  let translationsComponent;


  function scrollToBottom() {
    try {
      if (chatComponent && typeof chatComponent.scrollToBottom === 'function') {
        chatComponent.scrollToBottom();
      } else if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }
    } catch (err) {
      console.warn('Could not scroll chat to bottom:', err);
    }
  }

  onMount(async () => {
    if ($isAuthenticated) {
        // For admin users, we can load the saved section immediately
        if ($userRole === 'admin') {
          const savedSection = localStorage.getItem('activeConsoleSection');
          if (savedSection) {
            activeSection = savedSection;
            $activeSectionStore = savedSection;
            userSelectedSection = true; // Consider saved section as user selection
            localStorage.removeItem('activeConsoleSection'); // Clear after use
          }
        }

        // Load catalogs to determine menu visibility
        // For non-admin users, we'll wait until catalogs are loaded to decide which section to show
        fetchCatalogs();
    }

    checkMobile();

    // Add event listener for catalog permissions
    window.addEventListener('viewPermissions', (event) => {
      const catalogId = event.detail.catalogId;
      console.log('Console received viewPermissions event with catalogId:', catalogId);
      $currentCatalogIdStore = catalogId;
    });

    window.addEventListener('resize', checkMobile);

    return () => {
      window.removeEventListener('resize', checkMobile);
      window.removeEventListener('viewPermissions', () => {});
    };
  });
</script>

<div class="console hide-in-embed">
  <!-- Hide header and sidebar in embedded mode -->
    <Header
      title={$i18nStore.t('title')}
      handleLogout={handleLogout}
      bind:this={headerComponent}
    />

  <div class="console-container" class:embedded-mode={isEmbedded}>
      <nav class="sidebar" class:collapsed={sidebarCollapsed} class:mobile={isMobile}>
        <div class="sidebar-toggle" on:click={toggleSidebar}>
          <span class="toggle-icon">{sidebarCollapsed ? '→' : '←'}</span>
        </div>
        <ul>
          {#if showCatalogMenu || $userRole === 'admin'}
          <li class={activeSection === 'catalogs' || activeSection === 'catalog-detail' || activeSection === 'catalog-permissions' ? 'active' : ''}>
            <button on:click={() => switchSection('catalogs')}>
              <span class="icon">📄</span>
              <span class="text">{$i18nStore.t('sidebar_catalogs')}</span>
            </button>
          </li>
          {/if}
          {#if $userRole === 'admin'}
          <li class={activeSection === 'permissions' ? 'active' : ''}>
            <button on:click={() => switchSection('permissions')}>
              <span class="icon">🔒</span>
              <span class="text">{$i18nStore.t('sidebar_permissions')}</span>
            </button>
          </li>
          <li class={activeSection === 'activity-log' ? 'active' : ''}>
            <button on:click={() => switchSection('activity-log')}>
              <span class="icon">📋</span>
              <span class="text">{$i18nStore.t('activity_log') || 'Activity Log'}</span>
            </button>
          </li>
          {/if}
          <li class={activeSection === 'chat' ? 'active' : ''}>
            <button on:click={() => switchSection('chat')}>
              <span class="icon">💬</span>
              <span class="text">{$i18nStore.t('sidebar_chat')}</span>
            </button>
          </li>
        </ul>
      </nav>

    <main class="content" class:expanded={sidebarCollapsed}>
      {#key activeSection}
        <div
          class="section-wrapper {activeSection != 'chat' ? 'section-wrapper-not-chat' : ''}"
          in:fly={{ x: 150, duration: 250, delay: 100 }}
          out:fade={{ duration: 100 }}
        >
          {#if activeSection === 'catalogs' || activeSection === 'catalog-detail'}
            <Catalog
              catalogs={catalogs}
              {loading}
              {error}
              selectedCatalog={selectedCatalog}
              loadingCatalog={loadingCatalog}
              catalogError={catalogError}
              switchSection={switchSection}
              bind:this={catalogComponent}
              activeSectionStore={activeSectionStore}
            />
          {:else if activeSection === 'catalog-permissions'}
            {#if $userRole === 'admin'}
              <Catalog_Permissions
                switchSection={switchSection}
                activeSectionStore={activeSectionStore}
                currentCatalogId={$currentCatalogIdStore}
                bind:this={catalogPermissionsComponent}
              />
              {#if $currentCatalogIdStore}
                <div style="display: none;">Current ID: {$currentCatalogIdStore}</div>
              {/if}
            {:else}
              <div class="unauthorized-section">
                <h2>{$i18nStore.t('access_denied') || 'Access Denied'}</h2>
                <p>{$i18nStore.t('admin_rights_required') || 'You need administrator rights to access this section.'}</p>
                <button class="back-button" on:click={() => switchSection('catalog-detail')}>
                  {$i18nStore.t('back_to_catalog_details') || 'Back to Catalog Details'}
                </button>
              </div>
            {/if}
          {:else if activeSection === 'permissions'}
            {#if $userRole === 'admin'}
              <Permissions
                {users}
                {loadingUsers}
                {usersError}
                {editingUser}
                {showUserModal}
                bind:this={permissionsComponent}
                {activeSectionStore}
                on:logoUploaded={handleLogoUploaded}
              />
            {:else}
              <div class="unauthorized-section">
                <h2>{$i18nStore.t('access_denied') || 'Access Denied'}</h2>
                <p>{$i18nStore.t('admin_rights_required') || 'You need administrator rights to access this section.'}</p>
                <button class="back-button" on:click={() => switchSection('catalogs')}>
                  {$i18nStore.t('back_to_catalogs') || 'Back to Catalogs'}
                </button>
              </div>
            {/if}
          {:else if activeSection === 'activity-log'}
            {#if $userRole === 'admin'}
              <ActivityLog
                {activeSectionStore}
              />
            {:else}
              <div class="unauthorized-section">
                <h2>{$i18nStore.t('access_denied') || 'Access Denied'}</h2>
                <p>{$i18nStore.t('admin_rights_required') || 'You need administrator rights to access this section.'}</p>
                <button class="back-button" on:click={() => switchSection('catalogs')}>
                  {$i18nStore.t('back_to_catalogs') || 'Back to Catalogs'}
                </button>
              </div>
            {/if}
          {:else if activeSection === 'chat'}
            <Chat isEmbedded={false}
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
  .logout_container {
    min-width: 150px;
  }
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

  .section-wrapper-not-chat {
    padding: 2rem;
  }
  .section-wrapper {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    overflow: auto;
    background-color: #f7fafc;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }

  .content.expanded {
    margin-left: 0; /* Don't use negative margin which causes horizontal scroll */
  }

  /* Styles for embedded mode */
  .embedded-mode .content {
    margin-left: 0 !important;
    padding: 0 !important;
    height: 100vh;
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

  .unauthorized-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    text-align: center;
  }

  .unauthorized-section h2 {
    color: #e53e3e;
    margin-bottom: 1rem;
  }

  .unauthorized-section p {
    margin-bottom: 2rem;
    color: #4a5568;
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
