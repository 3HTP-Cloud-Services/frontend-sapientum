<script>
  import { i18nStore } from '../lib/i18n.js';
  import { onMount, beforeUpdate, afterUpdate } from 'svelte';
  import {
    selectedCatalogStore,
    catalogFilesStore,
    loadingCatalogStore,
    loadingFilesStore,
    catalogErrorStore,
    filesErrorStore,
    fetchCatalog,
    fetchCatalogFiles
  } from './stores.js';
  import UploadModal from './UploadModal.svelte';

  export let switchSection;
  export let activeSectionStore;

  // State for upload modal
  let showUploadModal = false;
  let currentCatalogName = '';

  // For tracking updates
  let updateCount = 0;

  onMount(() => {
    console.log("CatalogDetail component mounted, selectedCatalog:", $selectedCatalogStore);
    updateCount++;
  });

  beforeUpdate(() => {
    console.log(`Before update #${updateCount}, selectedCatalog:`, $selectedCatalogStore);
  });

  afterUpdate(() => {
    updateCount++;
    console.log(`After update #${updateCount}, selectedCatalog:`, $selectedCatalogStore);
  });

  function viewCatalogPermissions(id) {
    // Use a custom event to pass the catalog ID to parent components
    const event = new CustomEvent('viewPermissions', {
      detail: { catalogId: id }
    });
    window.dispatchEvent(event);

    switchSection('catalog-permissions');
  }

  function backToCatalogs() {
    selectedCatalogStore.set(null);
    switchSection('catalogs');
  }

  // Store catalog ID for upload modal
  let uploadCatalogId = null;

  function uploadDocument(id) {
    if ($selectedCatalogStore) {
      uploadCatalogId = id || $selectedCatalogStore.id;
      currentCatalogName = $selectedCatalogStore.catalog_name;
      showUploadModal = true;
    }
  }

  function closeUploadModal() {
    showUploadModal = false;
    uploadCatalogId = null;
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
      if ($selectedCatalogStore) {
        // Use the catalog ID instead of name
        fetchCatalogFiles($selectedCatalogStore.id);
      }
    }
  }

  // Debug reactive statements
  $: console.log("REACTIVE: selectedCatalog changed to:", $selectedCatalogStore, "update count:", updateCount);
  $: console.log("REACTIVE: catalogFiles changed to:", $catalogFilesStore.length, "files");
</script>

<div class="section-header">
  <button class="back-button" on:click={backToCatalogs}>← {$i18nStore.t('back_to_catalogs')}</button>
  <button class="sap_button upload-document-button" on:click={() => uploadDocument($selectedCatalogStore?.id)}>
    <img src="./images/upload-white.png" alt="Upload" class="upload-icon"/>
    {$i18nStore.t('upload_document')}
  </button>
</div>
<div class="catalog-detail-section">
  {#if $loadingCatalogStore}
    <p>{$i18nStore.t('loading_catalog')}</p>
  {:else if $catalogErrorStore}
    <p class="error">{$catalogErrorStore}</p>
  {:else if $selectedCatalogStore}
    <div class="catalog-detail">
      <div class="catalog-detail-header">
        <h1>{$selectedCatalogStore.name}</h1>
        <div class="catalog-content">
          {$selectedCatalogStore.description}
        </div>
        <div class="catalog-type">
          Tipo: {$selectedCatalogStore.type}
          {#if $selectedCatalogStore.type === 's3_folder'}
            <span class="s3-badge">S3</span>
          {/if}
        </div>
        <button class="lock-button" on:click={() => {console.log('Catalog ID:', $selectedCatalogStore.id);viewCatalogPermissions($selectedCatalogStore.id)}}>
          <span class="lock-lock">🔒</span> {$i18nStore.t('catalog_permissions')}</button>
      </div>

      <h3>{$i18nStore.t('documents_title')}</h3>
      {#if $loadingFilesStore}
        <p>{$i18nStore.t('loading_catalog')}</p>
      {:else if $filesErrorStore}
        <p class="error">{$filesErrorStore}</p>
      {:else if $catalogFilesStore.length === 0}
        <p>{$i18nStore.t('no_files')}</p>
      {:else}
        <div class="files-list">
          <table>
            <thead>
            <tr>
              <th>{$i18nStore.t('document_name')}</th>
              <th>{$i18nStore.t('document_description')}</th>
              <th>{$i18nStore.t('document_upload_date')}</th>
              <th>{$i18nStore.t('document_status')}</th>
              <th>{$i18nStore.t('document_version')}</th>
              <th>{$i18nStore.t('document_size')}</th>
              <th colspan="2">{$i18nStore.t('actions_column')}</th>
            </tr>
            </thead>
            <tbody>
            {#each $catalogFilesStore as file}
              <tr>
                <td>{file.name || ''}</td>
                <td class="description-cell">{file.description || ''}</td>
                <td>
                  {#if file.uploadDate}
                    {(() => {
                      try {
                        return typeof file.uploadDate.toLocaleDateString === 'function'
                          ? file.uploadDate.toLocaleDateString()
                          : new Date(file.uploadDate).toLocaleDateString();
                      } catch (e) {
                        console.error('Date parse error:', e);
                        return 'Invalid date';
                      }
                    })()}
                  {:else}
                    N/A
                  {/if}
                </td>
                <td>
                  <span class="status-badge status-{(file.status || '').toLowerCase().replace(' ', '-')}">{file.status || 'Published'}</span>
                </td>
                <td>{file.version || '1.0'}</td>
                <td>{file.size || '0 B'}</td>
                <td>
                  <button class="icon-button edit-button" title={$i18nStore.t('edit_document')}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                      <path d="M12.854.146a.5.5 0 0 0-.707 0L10.5 1.793 14.207 5.5l1.647-1.646a.5.5 0 0 0 0-.708l-3-3zm.646 6.061L9.793 2.5 3.293 9H3.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.207l6.5-6.5zm-7.468 7.468A.5.5 0 0 1 6 13.5V13h-.5a.5.5 0 0 1-.5-.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.5-.5V10h-.5a.499.499 0 0 1-.175-.032l-.179.178a.5.5 0 0 0-.11.168l-2 5a.5.5 0 0 0 .65.65l5-2a.5.5 0 0 0 .168-.11l.178-.178z"/>
                    </svg>
                  </button>
                </td>
                <td>
                <button class="icon-button upload-button" title={$i18nStore.t('upload_new_version')}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                      <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
                      <path d="M7.646 1.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 2.707V11.5a.5.5 0 0 1-1 0V2.707L5.354 4.854a.5.5 0 1 1-.708-.708l3-3z"/>
                    </svg>
                  </button>
                </td>
              </tr>
            {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {:else}
    <p>{$i18nStore.t('select_catalog')}</p>
  {/if}
</div>

<UploadModal
  show={showUploadModal}
  catalogId={uploadCatalogId}
  catalogName={currentCatalogName}
  i18nStore={$i18nStore}
  on:close={closeUploadModal}
  on:upload={handleUpload}
/>

<style>
  .catalog-detail-section {
    margin-bottom: 2rem;
    position: relative;
  }

  .catalog-detail {
    background-color: white;
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    position: relative;
  }

  .catalog-detail-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 0.75rem;
  }

  .catalog-content {
    line-height: 1.6;
    color: #4a5568;
    margin-top: 0.4rem;
  }

  .catalog-type {
    display: inline-block;
    background-color: #e2e8f0;
    color: #4a5568;
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    margin: 0;
    margin-top: 0.4rem;
  }

  .s3-badge {
    display: inline-block;
    background-color: #3182ce;
    color: white;
    font-size: 0.75rem;
    font-weight: bold;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    margin-left: 0.5rem;
  }

  .catalog-detail h1 {
    margin-top: 0;
    color: #2d3748;
    font-size: 1.5rem;
    margin-bottom: 0;
  }
  .lock-lock {
    font-size: 1.4rem;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
  }

  .lock-button {
    display: flex;
    justify-content: center;
    align-items: center;
    min-width: 220px;
    height: 40px;
    background-color: #4299e1;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1.1rem;
    padding: 0;
    text-shadow: 2px 2px 3px rgba(0, 0, 0, 0.4);
    transition: background-color 0.2s ease;
  }

  .lock-button:hover {
    background-color: #3182ce;
  }

  .catalog-detail h3 {
    margin-top: 2rem;
    color: #2d3748;
    font-size: 1.2rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 0.5rem;
  }

  .files-list {
    margin-top: 1rem;
  }

  .files-list table {
    width: 100%;
    border-collapse: collapse;
  }

  .files-list th {
    text-align: left;
    padding: 0.75rem;
    background-color: #f7fafc;
    border-bottom: 1px solid #e2e8f0;
    font-weight: 600;
    color: #4a5568;
  }

  .files-list td {
    padding: 0.75rem;
    border-bottom: 1px solid #e2e8f0;
    color: #4a5568;
  }

  .description-cell {
    max-width: 200px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .actions-cell {
    display: flex;
    gap: 5px;
  }

  .icon-button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 5px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.2s ease;
  }

  .icon-button:hover {
    background-color: #edf2f7;
  }

  .edit-button {
    color: #4299e1;
  }

  .info-button {
    color: #805ad5;
  }

  .upload-button {
    color: #38a169;
  }

  .status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 500;
    text-align: center;
  }

  .status-draft {
    background-color: #e2e8f0;
    color: #4a5568;
  }

  .status-for-review {
    background-color: #feebc8;
    color: #c05621;
  }

  .status-published {
    background-color: #c6f6d5;
    color: #276749;
  }

  .status-deprecated {
    background-color: #fed7d7;
    color: #c53030;
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

  .back-button {
    display: inline-flex;
    align-items: center;
    color: #4299e1;
    background: none;
    border: none;
    padding: 0.5rem 0;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }

  .upload-document-button {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: #eeeeee;
    background-color: #5970ff;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
    padding: 20px 30px;
    margin: 1rem;
    font-size: 1.2em;
  }

  .upload-icon {
    width: 24px;
    height: 24px;
  }

</style>
