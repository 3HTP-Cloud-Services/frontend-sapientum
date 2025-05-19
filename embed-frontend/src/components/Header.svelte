<script>
  import { i18nStore, setLocale, currentLocale } from '@shared/utils/i18n.js';
  
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
      
      <button class="logout-button" on:click={handleLogout}>
        {$i18nStore?.t('logout') || 'Logout'}
      </button>
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
  
  .locale-button {
    background-color: transparent;
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 4px;
    padding: 0.25rem 0.5rem;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .locale-button.selected {
    background-color: rgba(255, 255, 255, 0.2);
    border-color: white;
  }
  
  .locale-button:hover {
    background-color: rgba(255, 255, 255, 0.1);
  }
  
  .logout-button {
    background-color: rgba(255, 255, 255, 0.2);
    color: white;
    border: none;
    border-radius: 4px;
    padding: 0.4rem 0.8rem;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .logout-button:hover {
    background-color: rgba(255, 255, 255, 0.3);
  }
</style>