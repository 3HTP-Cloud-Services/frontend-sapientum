<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';
  import { fade } from 'svelte/transition';
  import { i18nStore } from '../lib/i18n.js';

  export let documents = [];
  export let loading = true;
  export let error = '';

  export let selectedDocument = null;
  export let loadingDocument = false;
  export let documentError = '';

  export let switchSection;
  export let activeSectionStore;

  export async function fetchDocuments() {
    try {
      loading = true;
      const response = await fetch('/api/catalogs', {
        credentials: 'include'
      });

      if (response.ok) {
        documents = await response.json();
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

  export async function fetchDocument(id) {
    try {
      // Clear any previous document
      selectedDocument = null;
      loadingDocument = true;
      documentError = '';

      const response = await fetch(`/api/catalogs/${id}`, {
        credentials: 'include'
      });

      if (response.ok) {
        selectedDocument = await response.json();
      } else if (response.status === 401) {
        // User is not authenticated
        push('/login');
      } else if (response.status === 404) {
        documentError = 'Catálogo no encontrado';
      } else {
        console.error('Error fetching catalog:', response.status, response.statusText);
        documentError = 'Error al cargar el catálogo';
      }
    } catch (err) {
      console.error('Catalog detail fetch error:', err);
      documentError = 'Error de conexión';
    } finally {
      loadingDocument = false;
    }
  }

  export function viewDocument(id) {
    fetchDocument(id);
    switchSection('document-detail');
  }

  export function backToDocuments() {
    selectedDocument = null;
    documentError = '';
    switchSection('documents');
  }

  $: if ($activeSectionStore === 'documents') {
    console.log("Documents section is now active");
    documents = [];
    loading = true;
    fetchDocuments();
  }
</script>

{#if $activeSectionStore === 'document-detail'}
  <div class="section-header">
    <h2>{$i18nStore.t('document_details')}</h2>
    <button class="back-button" on:click={backToDocuments}>← {$i18nStore.t('back_to_documents')}</button>
  </div>
  <div class="document-detail-section">
    {#if loadingDocument}
      <p>{$i18nStore.t('loading_document')}</p>
    {:else if documentError}
      <p class="error">{documentError}</p>
    {:else if selectedDocument}
      <div class="document-detail">
        <h1>{selectedDocument.catalog_name}</h1>
        <div class="document-content">
          {selectedDocument.description}
        </div>
        <div class="document-type">
          Tipo: {selectedDocument.type}
        </div>
      </div>
    {:else}
      <p>{$i18nStore.t('select_document')}</p>
    {/if}
  </div>
{:else}
  <div class="section-header">
    <h2>{$i18nStore.t('sidebar_documents')}</h2>
  </div>
  <div class="documents-section">
    {#if loading}
      <p transition:fade={{ duration: 150 }}>{$i18nStore.t('loading_documents')}</p>
    {:else if error}
      <p class="error" transition:fade={{ duration: 150 }}>{error}</p>
    {:else if documents.length === 0 && !loading}
      <p transition:fade={{ duration: 150 }}>{$i18nStore.t('no_documents')}</p>
    {:else}
      <div class="document-cards" transition:fade={{ duration: 150 }}>
        {#each documents as doc}
          <div class="document-card">
            <h3>{doc.catalog_name}</h3>
            <p>{doc.description && doc.description.substring(0, 100)}...</p>
            <div class="catalog-type">{doc.type}</div>
            <button class="view-document-button" on:click={() => viewDocument(doc.id)}>{$i18nStore.t('view_document')}</button>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}
<style>
  /* Document detail view */
  .document-detail-section {
    margin-bottom: 2rem;
  }

  .document-detail {
    background-color: white;
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .document-detail h1 {
    margin-top: 0;
    color: #2d3748;
    font-size: 1.5rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 0.75rem;
  }

  .document-content {
    line-height: 1.6;
    color: #4a5568;
  }

  .document-type {
    margin-top: 1.5rem;
    font-size: 0.875rem;
    color: #718096;
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

  /* Documents section */
  .document-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
  }

  .document-card {
    background-color: white;
    border-radius: 8px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .document-card h3 {
    margin-top: 0;
    color: #2d3748;
  }

  .document-card .view-document-button {
    display: inline-block;
    margin-top: 1rem;
    color: #4299e1;
    background: none;
    border: 1px solid #4299e1;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  .document-card .view-document-button:hover {
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
