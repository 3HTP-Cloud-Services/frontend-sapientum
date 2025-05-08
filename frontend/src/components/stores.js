import { writable, get } from 'svelte/store';

export const catalogsStore = writable([]);
export const selectedCatalogStore = writable(null);
export const catalogFilesStore = writable([]);

export const loadingStore = writable(false);
export const loadingCatalogStore = writable(false);
export const loadingFilesStore = writable(false);
export const errorStore = writable('');
export const catalogErrorStore = writable('');
export const filesErrorStore = writable('');

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

    const catalogs = get(catalogsStore);
    // First try to find by id, then by name for backward compatibility
    const catalogFromStore = catalogs.find(c => c.id === parseInt(id) || c.catalog_name === id);

    if (catalogFromStore) {
      console.log('Using catalog from store:', catalogFromStore);
      selectedCatalogStore.set(catalogFromStore);

      fetchCatalogFiles(catalogFromStore.id);
      loadingCatalogStore.set(false);
      return;
    }

    const response = await fetch(`/api/catalogs/${id}`, {
      credentials: 'include'
    });

    if (response.ok) {
      const data = await response.json();
      console.log('Fetched catalog data:', data);
      selectedCatalogStore.set(data);

      fetchCatalogFiles(data.id);
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

      const processedFiles = files.map(file => {
        try {
          // Try to convert uploadDate to a Date object
          const dateStr = file.uploadDate || file.uploaded_at;
          const uploadDate = dateStr ? new Date(dateStr) : new Date();
          
          return {
            ...file,
            // Make sure we have all required fields with correct names
            id: file.id || file.s3Id || '',
            name: file.name || '',
            description: file.description || file.summary || '',
            uploadDate: uploadDate,
            status: file.status || 'Published',
            version: file.version || '1.0',
            size: file.size || file.size_formatted || '0 B'
          };
        } catch (error) {
          console.error('Error processing file data:', error, file);
          return {
            ...file,
            uploadDate: new Date(), // Default to current date if parsing fails
            status: file.status || 'Published',
            version: file.version || '1.0'
          };
        }
      });

      catalogFilesStore.set(processedFiles);
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
