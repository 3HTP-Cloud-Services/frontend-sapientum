<script>
  import { i18nStore, setLocale, currentLocale } from '../utils/i18n.js';

  export let handleLogout;
  export let title = 'Sapientum AI';
</script>

<header class="header">
  <div class="header-content">
    <h1 class="header-title">{title}</h1>

    <div class="header-actions">
      <div class="language-selector">
        <button class={`locale-button ${$currentLocale === 'en' ? 'selected' : ''}`}
                on:click={() => setLocale('en')}>
          English
        </button>
        <button class={`locale-button ${$currentLocale === 'es' ? 'selected' : ''}`}
                on:click={() => setLocale('es')}>
          Español
        </button>
      </div>
      <div class="logout-container">
        <button class="logout-button" on:click={handleLogout}>
          {$i18nStore?.t('logout') || 'Logout'}
        </button>
      </div>
    </div>
  </div>
</header>

<style>
  .header {
    background-color: #4a5568;
    color: white;
    padding: 0 1rem;
    height: 60px;
    position: sticky;
    top: 0;
    z-index: 100;
    width: 100%;
  }

  .header-content {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 100%;
  }

  .header-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .language-selector {
    display: flex;
    gap: 0.5rem;
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

  .logout-container {
    min-width: 150px;
  }
  .locale-button.selected {
    background-color: #4a72b3;
    border: 2px solid white;
  }

  .logout-button:hover {
    background-color: #f54e4e;
  }
</style>
