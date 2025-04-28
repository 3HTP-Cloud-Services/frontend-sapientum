<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';
  import { fade } from 'svelte/transition';
  import { i18nStore } from '../lib/i18n.js';

  export let catalogs = [];
  export let loading = true;
  export let error = '';

  export let selectedCatalog = null;
  export let loadingCatalog = false;
  export let catalogError = '';

  export let switchSection;
  export let activeSectionStore;

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
      selectedCatalog = null;
      loadingCatalog = true;
      catalogError = '';

      const response = await fetch(`/api/catalogs/${id}`, {
        credentials: 'include'
      });

      if (response.ok) {
        selectedCatalog = await response.json();
      } else if (response.status === 401) {
        push('/login');
      } else if (response.status === 404) {
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
    }
  }

  export function viewCatalog(id) {
    fetchCatalog(id);
    switchSection('catalog-detail');
  }

  export function viewCatalogPermissions() {
    switchSection('catalog-permissions');
  }

  export function backToCatalogs() {
    selectedCatalog = null;
    catalogError = '';
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
</script>

{#if $activeSectionStore === 'catalog-detail'}
  <div class="section-header">
    <h2>{$i18nStore.t('catalog_details')}</h2>
    <button class="back-button" on:click={backToCatalogs}>← {$i18nStore.t('back_to_catalogs')}</button>
  </div>
  <div class="catalog-detail-section">
    <div class="catalog-actions">
      <button class="catalog-permissions-button" on:click={viewCatalogPermissions}>{$i18nStore.t('catalog_permissions')}</button>
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
              <button class="view-catalog-button" on:click={() => viewCatalog(catalog.id)}>
                {$i18nStore.t('view_catalog_documents', { count: catalog.document_count })}
              </button>
              <button class="upload-document-button" on:click={() => uploadDocument(catalog.id)}>
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
  /* Catalog detail view */
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

  .catalog-content {
    line-height: 1.6;
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

  /* Catalogs section */
  .catalog-cards {
    display: grid;
    grid-template-columns: 1fr;  /* Single column */
    gap: 1.5rem;
  }

  .catalog-card {
    display: flex;
    justify-content: space-between;
    align-items: center; /* This will center the action buttons vertically */
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
    display: inline-block;
    color: #68D391;
    background: none;
    border: 1px solid #68D391;
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
