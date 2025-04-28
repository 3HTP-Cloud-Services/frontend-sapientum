<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { i18nStore } from '../lib/i18n.js';

  export let switchSection;
  export let activeSectionStore;
  export let currentCatalogId = null;

  function backToCatalogDetail() {
    switchSection('catalog-detail');
  }
</script>

<div class="section-header">
  <h2>{$i18nStore.t('catalog_permissions')}</h2>
  <button class="back-button" on:click={backToCatalogDetail}>← {$i18nStore.t('back_to_catalog_details')}</button>
</div>

<div class="catalog-permissions-section">
  <p>{$i18nStore.t('catalog_permissions_coming_soon')}</p>
</div>

<style>
  .catalog-permissions-section {
    margin-bottom: 2rem;
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
</style>