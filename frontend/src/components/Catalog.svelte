<script>
  import { onMount } from 'svelte';
  import CatalogList from './CatalogList.svelte';
  import CatalogDetail from './CatalogDetail.svelte';
  import { selectedCatalogStore, fetchCatalog } from './stores.js';

  export let switchSection;
  export let activeSectionStore;
  
  // Will be used in stores to keep track of the selected catalog ID
  let selectedCatalogId = null;

  // Event handler for when a catalog is selected
  function handleViewCatalog(event) {
    const id = event.detail;
    console.log('Parent received viewCatalog event with id:', id);
    
    // Set the selected catalog ID
    selectedCatalogId = id;

    // First change the section
    switchSection('catalog-detail');

    // Then fetch the catalog data
    // Slight delay to ensure component is mounted
    setTimeout(() => {
      console.log('Fetching catalog with ID:', id);
      fetchCatalog(id);
    }, 50);
  }

  onMount(() => {
    console.log("Catalog parent component mounted, active section:", $activeSectionStore);
  });

  // Debug tracking for selected catalog changes
  $: console.log("Parent - selectedCatalog value:", $selectedCatalogStore);
</script>

{#if $activeSectionStore === 'catalog-detail'}
  <CatalogDetail
          {switchSection}
          {activeSectionStore}
  />
{:else}
  <CatalogList
          {switchSection}
          {activeSectionStore}
          on:viewCatalog={handleViewCatalog}
  />
{/if}
