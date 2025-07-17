<script>
  import { i18nStore, setLocale, currentLocale } from '../utils/i18n.js';
  import { loadLogo } from '../utils/logo.js';
  import { onMount } from 'svelte';

  export let handleLogout;
  export let title = 'Sapientum AI';
  
  let logoUrl = null;
  let showLanguageDropdown = false;

  async function loadCompanyLogo() {
    logoUrl = await loadLogo();
  }

  onMount(() => {
    loadCompanyLogo();
    
    function handleClickOutside(event) {
      if (showLanguageDropdown && !event.target.closest('.language-dropdown')) {
        showLanguageDropdown = false;
      }
    }
    
    document.addEventListener('click', handleClickOutside);
    
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  });

  // Public function to refresh logo (called from parent when logo is uploaded)
  export function refreshLogo() {
    loadCompanyLogo();
  }

  function toggleLanguageDropdown() {
    showLanguageDropdown = !showLanguageDropdown;
  }

  function selectLanguage(locale) {
    setLocale(locale);
    showLanguageDropdown = false;
  }

  $: languageLabel = (() => {
    switch ($currentLocale) {
      case 'es': return 'Idiomas';
      case 'pt': return 'Idiomas';
      default: return 'Languages';
    }
  })();

  function getLanguageName(locale) {
    switch (locale) {
      case 'en': return 'English';
      case 'es': return 'Español';
      case 'pt': return 'Português';
      default: return locale;
    }
  }
</script>

<header class="header">
  <div class="header-content">
    <div class="header-left">
      <div class="logo-placeholder">
        {#if logoUrl}
          <img src={logoUrl} alt="Company Logo" class="header-logo" />
        {/if}
      </div>
      <h1 class="header-title">{title}</h1>
    </div>

    <div class="header-actions">
      <div class="language-selector">
        <div class="language-dropdown">
          <button class="language-button" on:click={toggleLanguageDropdown}>
            {languageLabel}
            <span class="dropdown-arrow" class:rotated={showLanguageDropdown}>▼</span>
          </button>
          {#if showLanguageDropdown}
            <div class="language-menu">
              <button class={`language-option ${$currentLocale === 'en' ? 'selected' : ''}`}
                      on:click={() => selectLanguage('en')}>
                English
              </button>
              <button class={`language-option ${$currentLocale === 'es' ? 'selected' : ''}`}
                      on:click={() => selectLanguage('es')}>
                Español
              </button>
              <button class={`language-option ${$currentLocale === 'pt' ? 'selected' : ''}`}
                      on:click={() => selectLanguage('pt')}>
                Português
              </button>
            </div>
          {/if}
        </div>
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
    padding: 0 1rem;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .logo-placeholder {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .header-logo {
    max-height: 40px;
    max-width: 40px;
    width: auto;
    height: auto;
    object-fit: contain;
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
    position: relative;
  }

  .language-dropdown {
    position: relative;
  }

  .language-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: white;
    background-color: #718096;
    padding: 0.5rem 0.75rem;
    border: 2px solid transparent;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s ease;
    min-width: 100px;
    justify-content: space-between;
  }

  .language-button:hover {
    background-color: #4a72b3;
    border: 2px solid white;
  }

  .dropdown-arrow {
    transition: transform 0.2s ease;
    font-size: 0.8rem;
  }

  .dropdown-arrow.rotated {
    transform: rotate(180deg);
  }

  .language-menu {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background-color: #718096;
    border: 2px solid #4a5568;
    border-radius: 4px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    z-index: 1000;
    margin-top: 2px;
  }

  .language-option {
    display: block;
    width: 100%;
    color: white;
    background-color: transparent;
    padding: 0.5rem 0.75rem;
    border: none;
    cursor: pointer;
    transition: background-color 0.2s ease;
    text-align: left;
  }

  .language-option:hover {
    background-color: #4a72b3;
  }

  .language-option.selected {
    background-color: #4a72b3;
    font-weight: bold;
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

  .logout-container {
    min-width: 150px;
  }

  .logout-button:hover {
    background-color: #f54e4e;
  }
</style>
