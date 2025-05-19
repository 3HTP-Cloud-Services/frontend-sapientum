<script>
  import { i18nStore } from '../utils/i18n.js';
  import { logout } from '../utils/auth.js';
  import { push } from 'svelte-spa-router';

  // Props to control what's shown
  export let showAdminControls = false;
  export let handleLogout = async () => {
    await logout();
    push('/login');
  };
  export let title = "Sapientum";
  
  function setLocale(locale) {
    if ($i18nStore) {
      $i18nStore.locale = locale;
    }
  }
</script>

<header class="console-header">
  <h1>{$i18nStore?.t('title') || title}</h1>
  <div class="header-controls">
    <div>
      <button class={`locale-button ${$i18nStore?.locale === 'en' ? 'selected' : ''}`}
              on:click={() => setLocale('en')}>English</button>
      <button class={`locale-button ${$i18nStore?.locale === 'es' ? 'selected' : ''}`}
              on:click={() => setLocale('es')}>Español</button>
    </div>
    <div class="logout-container">
      <button class="logout-button" on:click={handleLogout}>{$i18nStore?.t('logout') || 'Logout'}</button>
    </div>
  </div>
</header>

<style>
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
    margin-right: auto; /* Pushes everything else to the right */
  }

  .header-controls {
    display: flex;
    align-items: center;
    gap: 12px; /* Space between language buttons and logout */
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

  .logout-container {
    min-width: 150px;
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

  /* Mobile optimizations */
  @media (max-width: 768px) {
    .console-header {
      padding: 1rem;
    }

    .console-header h1 {
      font-size: 1.2rem;
    }
  }
</style>