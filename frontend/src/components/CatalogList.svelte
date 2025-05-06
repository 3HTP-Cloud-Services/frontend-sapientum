<script>
  import { push } from 'svelte-spa-router';
  import { fade } from 'svelte/transition';
  import { i18nStore } from '../lib/i18n.js';
  import { createEventDispatcher, onMount } from 'svelte';
  import {
    catalogsStore,
    loadingStore,
    errorStore,
    fetchCatalogs
  } from './stores.js';
  import UploadModal from './UploadModal.svelte';

  // State for catalog modal
  let showCatalogModal = false;
  let catalogTypes = [];
  let newCatalog = {
    catalog_name: '',
    description: '',
    type: 'manual'
  };

  // State for upload modal
  let showUploadModal = false;
  let currentCatalogId = null;
  let currentCatalogName = '';

  const dispatch = createEventDispatcher();

  export let switchSection;
  export let activeSectionStore;

  function viewCatalog(id) {
    console.log('viewCatalog: ' + id);
    dispatch('viewCatalog', id);
  }

  function uploadDocument(id, catalog_name) {
    const catalog = $catalogsStore.find(c => c.id === id);
    currentCatalogId = id;
    currentCatalogName = catalog_name;
    showUploadModal = true;
  }

  function closeUploadModal() {
    showUploadModal = false;
    currentCatalogId = null;
    currentCatalogName = '';
  }

  async function handleUpload(event) {
    console.log("Uploading files to catalog:", event.detail.catalogId, event.detail.files);
    const onComplete = event.detail.onComplete;
    let success = false;
    
    try {
      const formData = new FormData();
      
      for (const file of event.detail.files) {
        formData.append('file', file);
      }
      
      const response = await fetch(`/api/catalogs/${event.detail.catalogId}/upload`, {
        method: 'POST',
        credentials: 'include',
        body: formData
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log("Upload successful:", result);
        fetchCatalogs();
        success = true;
      } else {
        console.error("Upload failed:", response.status, response.statusText);
        const errorData = await response.json();
        console.error("Error details:", errorData);
      }
    } catch (error) {
      console.error("Upload error:", error);
    } finally {
      if (onComplete) onComplete(success);
      closeUploadModal();
    }
  }

  function addNewCatalog() {
    console.log("Opening add catalog modal");
    fetchCatalogTypes();
    showCatalogModal = true;
  }

  async function fetchCatalogTypes() {
    try {
      const response = await fetch('/api/catalog-types', {
        credentials: 'include'
      });

      if (response.ok) {
        catalogTypes = await response.json();
      } else {
        console.error('Error fetching catalog types:', response.status);
        catalogTypes = [
          {id: 'manual', name: 'manual'},
          {id: 'contract', name: 'contract'}
        ];
      }
    } catch (err) {
      console.error('Catalog types fetch error:', err);
      catalogTypes = [
        {id: 'manual', name: 'manual'},
        {id: 'contract', name: 'contract'}
      ];
    }
  }

  function closeCatalogModal() {
    showCatalogModal = false;
    newCatalog = {
      catalog_name: '',
      description: '',
      type: 'manual'
    };
  }

  async function submitNewCatalog() {
    console.log("Creating new catalog:", newCatalog);
    
    try {
      const response = await fetch('/api/catalogs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(newCatalog)
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log("Created catalog:", result);
        closeCatalogModal();
        fetchCatalogs();
      } else {
        console.error("Failed to create catalog:", response.status, response.statusText);
        const errorData = await response.json();
        console.error("Error details:", errorData);
      }
    } catch (error) {
      console.error("Error creating catalog:", error);
    }
  }

  onMount(() => {
    console.log("CatalogList component mounted");
    if ($activeSectionStore === 'catalogs') {
      console.log("Catalogs section is active, fetching catalogs");
      fetchCatalogs();
    }
  });

  $: if ($activeSectionStore === 'catalogs') {
    console.log("Catalogs section is now active");
    fetchCatalogs();
  }
</script>

<div class="section-header">
  <h2>{$i18nStore.t('sidebar_catalogs')}</h2>
  <button class="add-catalog-button" on:click={addNewCatalog}>
    {$i18nStore.t('add_user_button').replace('User', 'Catalog')}
  </button>
</div>
<div class="catalogs-section">
  {#if $loadingStore}
    <p transition:fade={{ duration: 150 }}>{$i18nStore.t('loading_catalogs')}</p>
  {:else if $errorStore}
    <p class="error" transition:fade={{ duration: 150 }}>{$errorStore}</p>
  {:else if $catalogsStore.length === 0 && !$loadingStore}
    <p transition:fade={{ duration: 150 }}>{$i18nStore.t('no_catalogs')}</p>
  {:else}
    <div class="catalog-cards" transition:fade={{ duration: 150 }}>
      {#each $catalogsStore as catalog}
        <div class="catalog-card">
          <div class="catalog-info">
            <div class="catalog-header">
              <h3>{catalog.catalog_name}</h3>
              <div class="catalog-type">{catalog.type}</div>
              {#if catalog.type === 's3_folder'}
                <div class="catalog-badge">S3</div>
              {/if}
            </div>
            <p>{catalog.description && catalog.description}</p>
          </div>
          <div class="catalog-actions">
            <button class="view-catalog-button" on:click={() => viewCatalog(catalog.catalog_name)}>
              {$i18nStore.t('view_catalog_documents', {count: catalog.document_count})}
            </button>
            <button class="sap_button upload-document-button" on:click={() => uploadDocument(catalog.id, catalog.catalog_name)}>
              <img src="./images/upload-white.png" alt="Upload" class="upload-icon"/>
              {$i18nStore.t('upload_document')}
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

{#if showCatalogModal}
  <div class="modal-overlay" on:click={closeCatalogModal}>
    <div class="modal-content" on:click|stopPropagation>
      <div class="modal-header">
        <h2>{$i18nStore.t('add_catalog_button')}</h2>
        <button class="close-button" on:click={closeCatalogModal}>×</button>
      </div>

      <div class="modal-body">
        <div class="form-group">
          <label for="catalog-name">{$i18nStore.t('catalog_name')}</label>
          <input
            type="text"
            id="catalog-name"
            bind:value={newCatalog.catalog_name}
            placeholder={$i18nStore.t('catalog_name')}
          />
        </div>

        <div class="form-group">
          <label for="catalog-description">{$i18nStore.t('catalog_description')}</label>
          <textarea
            id="catalog-description"
            bind:value={newCatalog.description}
            placeholder={$i18nStore.t('catalog_description')}
          ></textarea>
        </div>

        <div class="form-group">
          <label for="catalog-type">{$i18nStore.t('catalog_type')}</label>
          <select id="catalog-type" bind:value={newCatalog.type}>
            {#each catalogTypes as type}
              <option value={type.id}>{type.name}</option>
            {/each}
          </select>
        </div>
      </div>

      <div class="modal-footer">
        <button class="cancel-button" on:click={closeCatalogModal}>{$i18nStore.t('cancel_button')}</button>
        <button class="save-button" on:click={submitNewCatalog}>{$i18nStore.t('save_button')}</button>
      </div>
    </div>
  </div>
{/if}

<UploadModal
  show={showUploadModal}
  catalogId={currentCatalogId}
  catalogName={currentCatalogName}
  i18nStore={$i18nStore}
  on:close={closeUploadModal}
  on:upload={handleUpload}
/>

<style>
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .add-catalog-button {
    background-color: #5970ff;
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  .add-catalog-button:hover {
    background-color: #68D391;
  }

  .catalog-cards {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .catalog-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: white;
    border-radius: 8px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .catalog-info {
    flex: 1;
  }

  .catalog-actions {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-left: 1rem;
    align-self: center;
    flex-shrink: 0;
  }

  .upload-document-button {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: #eeeeee;
    background-color: #5970ff;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  .upload-document-button:hover {
    background-color: #68D391;
    color: white;
  }

  .upload-icon {
    width: 16px;
    height: 16px;
  }

  .catalog-card h3 {
    margin-top: 0;
    color: #2d3748;
  }

  .catalog-card .view-catalog-button {
    display: inline-block;
    color: #4299e1;
    background: none;
    border: 1px solid #4299e1;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  .catalog-card .view-catalog-button:hover {
    background-color: #4299e1;
    color: white;
  }

  .catalog-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.5rem;
  }

  .catalog-header h3 {
    margin: 0;
  }

  .catalog-type {
    display: inline-block;
    background-color: #e2e8f0;
    color: #4a5568;
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    margin-bottom: 0.5rem;
  }

  .catalog-badge {
    display: inline-block;
    background-color: #3182ce;
    color: white;
    font-size: 0.75rem;
    font-weight: bold;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    margin-left: 0.5rem;
    margin-bottom: 0.5rem;
  }

  /* Modal Styles */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
  }

  .modal-content {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    width: 90%;
    max-width: 500px;
    max-height: 90vh;
    overflow-y: auto;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #e2e8f0;
  }

  .modal-header h2 {
    margin: 0;
    font-size: 1.25rem;
    color: #2d3748;
  }

  .close-button {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #718096;
  }

  .modal-body {
    padding: 1.5rem;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #4a5568;
  }

  .form-group input,
  .form-group textarea,
  .form-group select {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #cbd5e0;
    border-radius: 4px;
    font-size: 1rem;
  }

  .form-group textarea {
    min-height: 100px;
    resize: vertical;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    padding: 1rem 1.5rem;
    border-top: 1px solid #e2e8f0;
  }

  .cancel-button {
    background-color: #e2e8f0;
    color: #4a5568;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    border: none;
    cursor: pointer;
    font-size: 0.875rem;
  }

  .save-button {
    background-color: #5970ff;
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    border: none;
    cursor: pointer;
    font-size: 0.875rem;
  }

  .save-button:hover {
    background-color: #68D391;
  }

  .save-button:disabled {
    background-color: #a0aec0;
    cursor: not-allowed;
  }
</style>
