<script>
  import { push } from 'svelte-spa-router';
  import { writable } from 'svelte/store';
  import { fade } from 'svelte/transition';
  import { i18nStore } from '../lib/i18n.js';
  import { onMount, beforeUpdate, afterUpdate, tick } from 'svelte';

  // Try a simpler, more direct approach
  export let catalogs = [];
  export let loading = true;
  export let error = '';

  // Use a plain reactive variable
  export let selectedCatalog = null;
  export let loadingCatalog = false;
  export let catalogError = '';

  export let catalogFiles = [];
  export let loadingFiles = false;
  export let filesError = '';

  export let switchSection;
  export let activeSectionStore;

  // Flag to force re-rendering
  let updateTrigger = 0;

  // Force a component update
  function forceUpdate() {
    updateTrigger += 1;
    console.log("Forced update triggered:", updateTrigger);
  }

  onMount(() => {
    console.log("Component mounted, selectedCatalog:", selectedCatalog);
  });

  beforeUpdate(() => {
    console.log("Before update, selectedCatalog:", selectedCatalog, "trigger:", updateTrigger);
  });

  afterUpdate(() => {
    console.log("After update, selectedCatalog:", selectedCatalog, "trigger:", updateTrigger);
  });

  export async function fetchCatalogs() {
    try {
      loading = true;
      const response = await fetch('/api/catalogs', {
        credentials: 'include'
      });

      if (response.ok) {
        catalogs = await response.json();
      } else if (response.status === 401) {
        push('/login');
      } else {
        console.error('Error fetching catalogs:', response.status, response.statusText);
        error = 'Error al cargar catálogos';
      }
    } catch (err) {
      console.error('Catalog fetch error:', err);
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  export async function fetchCatalog(id) {
    try {
      loadingCatalog = true;
      catalogError = '';
      selectedCatalog = null; // Reset before fetching
      forceUpdate(); // Force update before fetching

      const response = await fetch(`/api/catalogs/${id}`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Fetched catalog data:', data);

        // Ensure UI is updated before changing data
        await tick();

        // Direct assignment to trigger reactivity
        selectedCatalog = data;
        console.log('After assignment, selectedCatalog:', selectedCatalog);

        // Force an update after data assignment
        forceUpdate();

        // Wait for UI to update again
        await tick();

        fetchCatalogFiles(id);
      } else if (response.status === 401) {
        console.log('fetchCatalog: 401');
        push('/login');
      } else if (response.status === 404) {
        console.log('fetchCatalog: 404');
        catalogError = 'Catálogo no encontrado';
      } else {
        console.error('Error fetching catalog:', response.status, response.statusText);
        catalogError = 'Error al cargar el catálogo';
      }
    } catch (err) {
      console.error('Catalog detail fetch error:', err);
      catalogError = 'Error de conexión';
    } finally {
      loadingCatalog = false;
      // Force one final update when we're done loading
      forceUpdate();
    }
  }

  export async function fetchCatalogFiles(id) {
    try {
      catalogFiles = [];
      loadingFiles = true;
      filesError = '';

      const response = await fetch(`/api/catalogs/${id}/files`, {
        credentials: 'include'
      });

      if (response.ok) {
        catalogFiles = await response.json();
        console.log('files:', catalogFiles);
      } else if (response.status === 401) {
        console.log('401:', response);
        push('/login');
      } else if (response.status === 404) {
        console.log('404:', response);
        filesError = 'Archivos no encontrados';
      } else {
        console.error('Error fetching catalog files:', response.status, response.statusText);
        filesError = 'Error al cargar los archivos';
      }
    } catch (err) {
      console.error('Catalog files fetch error:', err);
      filesError = 'Error de conexión';
    } finally {
      loadingFiles = false;
      forceUpdate(); // Force update after files load
    }
  }

  export function viewCatalog(id) {
    console.log('viewCatalog: ' + id);
    selectedCatalog = null; // Reset before view change
    forceUpdate(); // Force update when clearing
    switchSection('catalog-detail');
    fetchCatalog(id);
  }

  export function viewCatalogPermissions() {
    switchSection('catalog-permissions');
  }

  export function backToCatalogs() {
    selectedCatalog = null;
    catalogError = '';
    forceUpdate(); // Force update when clearing
    switchSection('catalogs');
  }

  export function uploadDocument(id) {
    console.log("Upload document for catalog", id);
  }

  $: if ($activeSectionStore === 'catalogs') {
    console.log("Catalogs section is now active");
    catalogs = [];
    loading = true;
    fetchCatalogs();
  }

  // This reactive statement will log whenever selectedCatalog changes
  $: console.log("REACTIVE: selectedCatalog changed to:", selectedCatalog, "trigger:", updateTrigger);
</script>

{#if $activeSectionStore === 'catalog-detail'}
  <div class="section-header">
    <h2>{$i18nStore.t('catalog_details')}</h2>
    <button class="back-button" on:click={backToCatalogs}>← {$i18nStore.t('back_to_catalogs')}</button>
  </div>
  <div class="catalog-detail-section">
    <div class="catalog-actions">
      <button class="catalog-permissions-button"
              on:click={viewCatalogPermissions}>{$i18nStore.t('catalog_permissions')}</button>
    </div>
    <div>
      <p>Debug info (update trigger: {updateTrigger}):</p>
      <pre>loadingCatalog: {loadingCatalog}</pre>
      <pre>catalogError: {catalogError}</pre>
      <pre>selectedCatalog type: {typeof selectedCatalog}</pre>
      <pre>selectedCatalog null check: {selectedCatalog === null ? 'IS NULL' : 'NOT NULL'}</pre>
      <pre>selectedCatalog undefined check: {selectedCatalog === undefined ? 'IS UNDEFINED' : 'NOT UNDEFINED'}</pre>
      <pre>selectedCatalog truthy check: {selectedCatalog ? 'IS TRUTHY' : 'IS FALSY'}</pre>

      {#if selectedCatalog !== null && selectedCatalog !== undefined}
        <p>RAW DATA: {JSON.stringify(selectedCatalog)}</p>
      {/if}

      <hr>

      {#if typeof selectedCatalog === 'object' && selectedCatalog !== null}
        <div style="color: green;">
          SELECTED OBJECT
          <p>Try to access: {selectedCatalog.catalog_name || 'No catalog_name property'}</p>
        </div>
      {:else}
        <div style="color: red;">NOT AN OBJECT OR NULL</div>
      {/if}
    </div>

    {#if loadingCatalog}
      <p>{$i18nStore.t('loading_catalog')}</p>
    {:else if catalogError}
      <p class="error">{catalogError}</p>
    {:else if selectedCatalog}
      <div class="catalog-detail">
        <h1>{selectedCatalog.catalog_name}</h1>
        <div class="catalog-content">
          {selectedCatalog.description}
        </div>
        <div class="catalog-type">
          Tipo: {selectedCatalog.type}
        </div>

        <h3>{$i18nStore.t('catalog_details')}</h3>
        {#if loadingFiles}
          <p>{$i18nStore.t('loading_catalog')}</p>
        {:else if filesError}
          <p class="error">{filesError}</p>
        {:else if catalogFiles.length === 0}
          <p>{$i18nStore.t('no_files')}</p>
        {:else}
          <div class="files-list">
            <table>
              <thead>
              <tr>
                <th>Nombre</th>
                <th>Tamaño</th>
                <th>Fecha de creación</th>
              </tr>
              </thead>
              <tbody>
              {#each catalogFiles as file}
                <tr>
                  <td>{file.name}</td>
                  <td>{file.size}</td>
                  <td>{new Date(file.created_at).toLocaleString()}</td>
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
{:else}
  <div class="section-header">
    <h2>{$i18nStore.t('sidebar_catalogs')}</h2>
  </div>
  <div class="catalogs-section">
    {#if loading}
      <p transition:fade={{ duration: 150 }}>{$i18nStore.t('loading_catalogs')}</p>
    {:else if error}
      <p class="error" transition:fade={{ duration: 150 }}>{error}</p>
    {:else if catalogs.length === 0 && !loading}
      <p transition:fade={{ duration: 150 }}>{$i18nStore.t('no_catalogs')}</p>
    {:else}
      <div class="catalog-cards" transition:fade={{ duration: 150 }}>
        {#each catalogs as catalog}
          <div class="catalog-card">
            <div class="catalog-info">
              <div class="catalog-header">
                <h3>{catalog.catalog_name}</h3>
                <div class="catalog-type">{catalog.type}</div>
              </div>
              <p>{catalog.description && catalog.description}</p>
            </div>
            <div class="catalog-actions">
              <button class="view-catalog-button" on:click={() => viewCatalog(catalog.catalog_name)}>
                {$i18nStore.t('view_catalog_documents', {count: catalog.document_count})}
              </button>
              <button class="upload-document-button" on:click={() => uploadDocument(catalog.id)}>
                <img src="./images/upload-white.png" alt="Upload" class="upload-icon"/>
                {$i18nStore.t('upload_document')}
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}
<style>
  /* Catalog detail */
  .catalog-detail-section {
    margin-bottom: 2rem;
  }

  .catalog-detail {
    background-color: white;
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .catalog-detail h1 {
    margin-top: 0;
    color: #2d3748;
    font-size: 1.5rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 0.75rem;
  }

  .catalog-detail h3 {
    margin-top: 2rem;
    color: #2d3748;
    font-size: 1.2rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 0.5rem;
  }

  .catalog-content {
    line-height: 1.6;
    color: #4a5568;
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
    margin: 0;
  }

  .catalog-permissions-button {
    background-color: #4299e1;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
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

  /* Catalogs  */
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

  .catalog-type {
    display: inline-block;
    background-color: #e2e8f0;
    color: #4a5568;
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    margin-bottom: 0.5rem;
  }
</style>
