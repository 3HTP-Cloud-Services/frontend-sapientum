import { writable } from 'svelte/store';

// Create stores for shared state across components
export const catalogsStore = writable([]);
export const selectedCatalogStore = writable(null);
export const catalogFilesStore = writable([]);

// Loading and error states
export const loadingStore = writable(false);
export const loadingCatalogStore = writable(false);
export const loadingFilesStore = writable(false);
export const errorStore = writable('');
export const catalogErrorStore = writable('');
export const filesErrorStore = writable('');

// API functions that update the stores
export async function fetchCatalogs() {
  try {
    loadingStore.set(true);
    errorStore.set('');

    const response = await fetch('/api/catalogs', {
      credentials: 'include'
    });

    if (response.ok) {
      const data = await response.json();
      catalogsStore.set(data);
    } else if (response.status === 401) {
      window.location.href = '/#/login';
    } else {
      console.error('Error fetching catalogs:', response.status, response.statusText);
      errorStore.set('Error al cargar catálogos');
    }
  } catch (err) {
    console.error('Catalog fetch error:', err);
    errorStore.set('Error de conexión');
  } finally {
    loadingStore.set(false);
  }
}

export async function fetchCatalog(id) {
  try {
    loadingCatalogStore.set(true);
    catalogErrorStore.set('');
    selectedCatalogStore.set(null);

    const response = await fetch(`/api/catalogs/${id}`, {
      credentials: 'include'
    });

    if (response.ok) {
      const data = await response.json();
      console.log('Fetched catalog data:', data);
      selectedCatalogStore.set(data);

      // Fetch files after catalog is loaded
      fetchCatalogFiles(id);
    } else if (response.status === 401) {
      window.location.href = '/#/login';
    } else if (response.status === 404) {
      catalogErrorStore.set('Catálogo no encontrado');
    } else {
      console.error('Error fetching catalog:', response.status, response.statusText);
      catalogErrorStore.set('Error al cargar el catálogo');
    }
  } catch (err) {
    console.error('Catalog detail fetch error:', err);
    catalogErrorStore.set('Error de conexión');
  } finally {
    loadingCatalogStore.set(false);
  }
}

export async function fetchCatalogFiles(id) {
  try {
    loadingFilesStore.set(true);
    filesErrorStore.set('');
    catalogFilesStore.set([]);

    const response = await fetch(`/api/catalogs/${id}/files`, {
      credentials: 'include'
    });

    if (response.ok) {
      const files = await response.json();
      console.log('Files:', files);
      catalogFilesStore.set(files);
    } else if (response.status === 401) {
      window.location.href = '/#/login';
    } else if (response.status === 404) {
      filesErrorStore.set('Archivos no encontrados');
    } else {
      console.error('Error fetching catalog files:', response.status, response.statusText);
      filesErrorStore.set('Error al cargar los archivos');
    }
  } catch (err) {
    console.error('Catalog files fetch error:', err);
    filesErrorStore.set('Error de conexión');
  } finally {
    loadingFilesStore.set(false);
  }
}
