<script>
  import { onMount } from 'svelte';
  import { i18nStore, currentLocale, t, updateTranslations, setLocale } from '../lib/i18n.js';

  let translations = {};
  let keys = [];
  let editingKey = null;
  let currentEditValue = '';
  let saveStatus = { success: true, message: '' };
  let isLoading = true;
  let selectedLanguage = 'en';

  i18nStore.subscribe(i18n => {
    if (i18n) {
      const i18nTranslations = i18n.translations;
      translations = i18nTranslations;

      if (i18nTranslations.en) {
        keys = Object.keys(i18nTranslations.en).sort();
      }

      isLoading = false;
    }
  });

  currentLocale.subscribe(locale => {
    selectedLanguage = locale;
  });

  function startEditing(key) {
    editingKey = key;
    currentEditValue = translations[selectedLanguage][key];
  }

  function cancelEditing() {
    editingKey = null;
    currentEditValue = '';
  }

  async function saveEdit() {
    if (!editingKey) return;

    saveStatus = { success: false, message: 'Saving...' };

    const updates = {
      [editingKey]: currentEditValue
    };

    const result = await updateTranslations(selectedLanguage, updates);

    if (result.success) {
      saveStatus = { success: true, message: 'Translation saved successfully!' };
      setTimeout(() => {
        saveStatus.message = '';
      }, 3000);
    } else {
      saveStatus = { success: false, message: `Error: ${result.error}` };
    }

    editingKey = null;
  }

  function changeLanguage(lang) {
    setLocale(lang);
  }
</script>

<div class="translations-container">
  <h2>{t('translations_title', 'Translation Management')}</h2>

  <div class="language-selector">
    <button class={selectedLanguage === 'en' ? 'active' : ''} on:click={() => changeLanguage('en')}>
      English
    </button>
    <button class={selectedLanguage === 'es' ? 'active' : ''} on:click={() => changeLanguage('es')}>
      Español
    </button>
  </div>

  {#if saveStatus.message}
    <div class="status-message" class:error={!saveStatus.success}>
      {saveStatus.message}
    </div>
  {/if}

  {#if isLoading}
    <p>{t('loading_translations', 'Loading translations...')}</p>
  {:else}
    <div class="translations-table">
      <table>
        <thead>
          <tr>
            <th>{t('key_column')}</th>
            <th>{t('value_column')}</th>
            <th>{t('actions_column')}</th>
          </tr>
        </thead>
        <tbody>
          {#each keys as key}
            <tr>
              <td>{key}</td>
              <td>
                {#if editingKey === key}
                  <input type="text" bind:value={currentEditValue} />
                {:else}
                  {translations[selectedLanguage][key]}
                {/if}
              </td>
              <td>
                {#if editingKey === key}
                  <button on:click={saveEdit} class="save-btn">{t('save_button')}</button>
                  <button on:click={cancelEditing} class="cancel-btn">{t('cancel_button')}</button>
                {:else}
                  <button on:click={() => startEditing(key)} class="edit-btn">{t('edit_button')}</button>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  .translations-container {
    padding: 1rem;
  }

  .language-selector {
    margin-bottom: 1rem;
    display: flex;
    gap: 0.5rem;
  }

  .language-selector button {
    padding: 0.5rem 1rem;
    border: 1px solid #ccc;
    background-color: #f5f5f5;
    cursor: pointer;
  }

  .language-selector button.active {
    background-color: #007bff;
    color: white;
    border-color: #0056b3;
  }

  .translations-table {
    width: 100%;
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th, td {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid #ddd;
  }

  th {
    background-color: #f2f2f2;
    font-weight: bold;
  }

  input {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #ccc;
    border-radius: 4px;
  }

  button {
    padding: 0.25rem 0.5rem;
    margin-right: 0.25rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }

  .edit-btn {
    background-color: #6c757d;
    color: white;
  }

  .save-btn {
    background-color: #28a745;
    color: white;
  }

  .cancel-btn {
    background-color: #dc3545;
    color: white;
  }

  .status-message {
    padding: 0.5rem;
    margin: 0.5rem 0;
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    border-radius: 4px;
    color: #155724;
  }

  .status-message.error {
    background-color: #f8d7da;
    border-color: #f5c6cb;
    color: #721c24;
  }
</style>
