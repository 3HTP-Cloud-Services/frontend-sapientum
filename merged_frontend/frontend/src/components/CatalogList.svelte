<script>
  import { push } from 'svelte-spa-router';
  import { fade } from 'svelte/transition';
  import { i18nStore } from '../../../shared-components/utils/i18n.js';
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import { httpCall } from '../../../shared-components/utils/httpCall.js';
  import {
    catalogsStore,
    loadingStore,
    errorStore,
    fetchCatalogs,
    selectedCatalogStore
  } from './stores.js';
  import UploadModal from './UploadModal.svelte';

  // State for catalog modal
  let showCatalogModal = false;
  let catalogTypes = [];
  let isCreatingCatalog = false;
  let catalogCreationError = '';
  let newCatalog = {
    catalog_name: '',
    description: '',
    type: 'general'
  };

  // State for upload modal
  let showUploadModal = false;
  let currentCatalogId = null;
  let currentCatalogName = '';

  // Polling state
  let statusPollingTimeout = null;
  let currentPollingDelay = 5000; // Start at 5 seconds

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

      const response = await httpCall(`/api/catalogs/${event.detail.catalogId}/upload`, {
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
      const response = await httpCall('/api/catalog-types', {
        credentials: 'include'
      });

      if (response.ok) {
        catalogTypes = await response.json();
      } else {
        console.error('Error fetching catalog types:', response.status);
        catalogTypes = [
          {id: 'general', name: 'General'},
          {id: 'legal', name: 'Legal'},
          {id: 'technical', name: 'Manuales Tecnicos'},
          {id: 'administrative', name: 'Procedimientos Administrativos'}
        ];
      }
    } catch (err) {
      console.error('Catalog types fetch error:', err);
      catalogTypes = [
        {id: 'general', name: 'General'},
        {id: 'legal', name: 'Legal'},
        {id: 'technical', name: 'Manuales Tecnicos'},
        {id: 'administrative', name: 'Procedimientos Administrativos'}
      ];
    }
  }

  function closeCatalogModal() {
    showCatalogModal = false;
    catalogCreationError = '';
    newCatalog = {
      catalog_name: '',
      description: '',
      type: 'general'
    };
  }

  function validateCatalogName(name) {
    const catalogNamePattern = /^[a-z0-9][a-z0-9_-]{0,99}$/;
    return catalogNamePattern.test(name);
  }

  async function submitNewCatalog() {
    console.log("Creating new catalog:", newCatalog);

    // Validate catalog name on frontend before sending to backend
    if (!newCatalog.catalog_name) {
      catalogCreationError = 'Catalog name is required';
      return;
    }

    if (!validateCatalogName(newCatalog.catalog_name)) {
      catalogCreationError = 'Invalid catalog name. Must start with lowercase letter or digit, contain only lowercase letters, digits, underscores, and hyphens, and be 1-100 characters long.';
      return;
    }

    isCreatingCatalog = true;
    catalogCreationError = '';

    try {
      const response = await httpCall('/api/catalogs', {
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
        catalogCreationError = errorData.error || response.statusText;
      }
    } catch (error) {
      console.error("Error creating catalog:", error);
      catalogCreationError = error.message;
    } finally {
      isCreatingCatalog = false;
    }
  }

  function getCatalogTypeName(typeId) {
    const type = catalogTypes.find(t => t.id === typeId);
    return type ? type.name : typeId;
  }

  function calculateCatalogState(statusData) {
    const has_kb = statusData.knowledge_base_id !== null && String(statusData.knowledge_base_id).trim() !== '';
    const has_ds = statusData.data_source_id !== null && String(statusData.data_source_id).trim() !== '';
    const has_agent = statusData.agent_id !== null && String(statusData.agent_id).trim() !== '';
    const has_agent_alias = statusData.agent_version_id !== null && String(statusData.agent_version_id).trim() !== '';

    const field_count = [has_kb, has_ds, has_agent, has_agent_alias].filter(Boolean).length;

    if (field_count === 4) return 'ready';
    if (field_count === 0) return 'created';
    return 'in_preparation';
  }

  async function pollCatalogsBatch(catalogIds) {
    try {
      console.log(`[POLL] Polling batch of ${catalogIds.length} catalogs`);

      const response = await httpCall('/api/catalogs/status/batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ ids: catalogIds })
      });

      if (response.ok) {
        const statusData = await response.json();
        console.log('[POLL] Batch status received:', statusData);

        // Update catalog store with new statuses
        catalogsStore.update(catalogs => {
          return catalogs.map(catalog => {
            const status = statusData[String(catalog.id)];
            if (status) {
              return {
                ...catalog,
                knowledge_base_id: status.knowledge_base_id,
                data_source_id: status.data_source_id,
                agent_id: status.agent_id,
                agent_version_id: status.agent_version_id,
                state: calculateCatalogState(status)
              };
            }
            return catalog;
          });
        });
      } else {
        console.error('[POLL] Failed to get batch status:', response.status);
      }
    } catch (error) {
      console.error('[POLL] Error polling batch:', error);
    }
  }

  async function pollAllNonReadyCatalogs() {
    // Get all non-ready catalogs
    const nonReadyCatalogs = $catalogsStore.filter(c => c.state !== 'ready');

    if (nonReadyCatalogs.length === 0) {
      console.log('[POLL] No non-ready catalogs to poll');
      scheduleNextPollRound();
      return;
    }

    console.log(`[POLL] Polling ${nonReadyCatalogs.length} non-ready catalogs`);

    // Split into batches of 20
    const batches = [];
    for (let i = 0; i < nonReadyCatalogs.length; i += 20) {
      batches.push(nonReadyCatalogs.slice(i, i + 20).map(c => c.id));
    }

    // Poll first batch immediately
    await pollCatalogsBatch(batches[0]);

    // Poll remaining batches with 1 second delay between them
    for (let i = 1; i < batches.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await pollCatalogsBatch(batches[i]);
    }

    // Schedule next poll round with increasing delay
    scheduleNextPollRound();
  }

  function scheduleNextPollRound() {
    console.log(`[POLL] Scheduling next poll round in ${currentPollingDelay / 1000} seconds`);

    statusPollingTimeout = setTimeout(() => {
      pollAllNonReadyCatalogs();
    }, currentPollingDelay);

    // Increase delay by 1 second for next round
    currentPollingDelay += 1000;
  }

  function startStatusPolling() {
    if (statusPollingTimeout) {
      clearTimeout(statusPollingTimeout);
    }

    // Reset delay to 5 seconds
    currentPollingDelay = 5000;

    console.log('[POLL] Starting status polling for catalog list');

    // Poll immediately
    pollAllNonReadyCatalogs();
  }

  function stopStatusPolling() {
    if (statusPollingTimeout) {
      console.log('[POLL] Stopping status polling');
      clearTimeout(statusPollingTimeout);
      statusPollingTimeout = null;
    }
  }

  onMount(() => {
    console.log("CatalogList component mounted");
    fetchCatalogTypes();
    if ($activeSectionStore === 'catalogs') {
      console.log("Catalogs section is active, fetching catalogs");
      fetchCatalogs();
    }
  });

  onDestroy(() => {
    stopStatusPolling();
  });

  $: if ($activeSectionStore === 'catalogs' && !$selectedCatalogStore) {
    console.log("Catalogs section is now active and no catalog selected");
    fetchCatalogs();
    startStatusPolling();
  } else {
    console.log("Stopping list polling - either not in catalogs section or catalog detail is open");
    stopStatusPolling();
  }
</script>

<div class="section-header">
  <h2>{$i18nStore.t('sidebar_catalogs')}</h2>
  <button class="add-catalog-button" on:click={addNewCatalog}>
    {$i18nStore.t('add_catalog_button')}
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
              <div class="catalog-type">{getCatalogTypeName(catalog.type)}</div>
              {#if catalog.type === 'general'}
                <div class="catalog-badge">S3</div>
              {/if}
              {#if catalog.state}
                <div class="catalog-state catalog-state-{catalog.state}">
                  {$i18nStore.t(`catalog_state_${catalog.state}`)}
                </div>
              {/if}
            </div>
            <p>{catalog.description && catalog.description}</p>
          </div>
          <div class="catalog-actions">
            <button class="view-catalog-button" on:click={() => viewCatalog(catalog.id)}>
              {$i18nStore.t('view_catalog_documents', {count: catalog.document_count})}
            </button>
            <button
              class="sap_button upload-document-button"
              on:click={() => uploadDocument(catalog.id, catalog.catalog_name)}
              disabled={catalog.state && catalog.state !== 'ready'}
            >
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
        {#if catalogCreationError}
          <div class="error-message">
            {catalogCreationError}
          </div>
        {/if}

        <div class="form-group">
          <label for="catalog-name">{$i18nStore.t('catalog_name')}</label>
          <input
            type="text"
            id="catalog-name"
            bind:value={newCatalog.catalog_name}
            placeholder={$i18nStore.t('catalog_name')}
            disabled={isCreatingCatalog}
          />
        </div>

        <div class="form-group">
          <label for="catalog-description">{$i18nStore.t('catalog_description')}</label>
          <textarea
            id="catalog-description"
            bind:value={newCatalog.description}
            placeholder={$i18nStore.t('catalog_description')}
            disabled={isCreatingCatalog}
          ></textarea>
        </div>

        <div class="form-group">
          <label for="catalog-type">{$i18nStore.t('catalog_type')}</label>
          <select id="catalog-type" bind:value={newCatalog.type} disabled={isCreatingCatalog}>
            {#each catalogTypes as type}
              <option value={type.id}>{type.name}</option>
            {/each}
          </select>
        </div>
      </div>

      <div class="modal-footer">
        <button class="cancel-button" on:click={closeCatalogModal} disabled={isCreatingCatalog}>{$i18nStore.t('cancel_button')}</button>
        <button class="save-button" on:click={submitNewCatalog} disabled={isCreatingCatalog}>
          {#if isCreatingCatalog}
            Creating...
          {:else}
            {$i18nStore.t('save_button')}
          {/if}
        </button>
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

  .upload-document-button:hover:not(:disabled) {
    background-color: #68D391;
    color: white;
  }

  .upload-document-button:disabled {
    background-color: #a0aec0;
    cursor: not-allowed;
    opacity: 0.6;
  }

  .upload-icon {
    width: 16px;
    height: 16px;
  }

  .catalog-card h3 {
    margin-top: 0;
    color: #032b36;
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

  .catalog-state {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    margin-left: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .catalog-state-ready {
    background-color: #48bb78;
    color: white;
  }

  .catalog-state-created {
    background-color: #cbd5e0;
    color: #2d3748;
  }

  .catalog-state-in_preparation {
    background-color: #ed8936;
    color: white;
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
    color: #032b36;
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

  .error-message {
    background-color: #fed7d7;
    color: #c53030;
    padding: 0.75rem;
    border-radius: 4px;
    margin-bottom: 1rem;
    font-size: 0.875rem;
    border: 1px solid #fc8181;
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
