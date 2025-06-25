<script>
  import { i18nStore } from '../../../shared-components/utils/i18n.js';
  import { onMount, beforeUpdate, afterUpdate } from 'svelte';
  import { httpCall } from '../../../shared-components/utils/httpCall.js';
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
  import EditModal from './EditModal.svelte';
  import { userRole } from '../../../shared-components/utils/auth.js';

  export let switchSection;
  export let activeSectionStore;

  // State for upload modal
  let showUploadModal = false;
  let currentCatalogName = '';
  let currentFile = null;
  let isNewVersion = false;

  let showEditModal = false;
  let fileToEdit = null;

  // For tracking updates
  let updateCount = 0;
  
  // For checking catalog permissions
  let canManagePermissions = false;
  let permissionCheckResult = null;
  let permissionCheckError = null;
  let dbPermissionInfo = null;
  
  // Check if user can manage permissions for this catalog
  $: if ($selectedCatalogStore && $selectedCatalogStore.id) {
    checkCanManagePermissions($selectedCatalogStore.id);
    fetchDbPermissionInfo($selectedCatalogStore.id);
  }
  
  async function checkCanManagePermissions(catalogId) {
    try {
      const response = await httpCall(`/api/catalogs/${catalogId}/can-manage-permissions`, 'GET');
      const data = await response.json();
      permissionCheckResult = data;
      permissionCheckError = null;
      console.log('Permission check response:', data);
      if (data && data.can_manage) {
        canManagePermissions = true;
      } else {
        canManagePermissions = false;
      }
    } catch (error) {
      console.error('Error checking catalog permissions:', error);
      permissionCheckError = error.message || error.toString();
      permissionCheckResult = null;
      canManagePermissions = false;
    }
  }
  
  async function fetchDbPermissionInfo(catalogId) {
    try {
      const response = await httpCall(`/api/catalogs/${catalogId}/my-permission`, 'GET');
      const data = await response.json();
      dbPermissionInfo = data;
      console.log('DB Permission info:', data);
    } catch (error) {
      console.error('Error fetching DB permission info:', error);
      dbPermissionInfo = { error: error.message || error.toString() };
    }
  }

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
    console.log('viewCatalogPermissions called with ID:', id);

    // Use a custom event to pass the catalog ID to parent components
    const event = new CustomEvent('viewPermissions', {
      detail: { catalogId: id }
    });
    window.dispatchEvent(event);
    console.log('Dispatched viewPermissions event with catalogId:', id);

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
      currentFile = null;
      isNewVersion = false;
      showUploadModal = true;
    }
  }

  function uploadNewVersion(file) {
    if ($selectedCatalogStore) {
      uploadCatalogId = $selectedCatalogStore.id;
      currentCatalogName = $selectedCatalogStore.catalog_name;
      currentFile = file;
      isNewVersion = true;
      showUploadModal = true;
    }
  }

  function closeUploadModal() {
    showUploadModal = false;
    uploadCatalogId = null;
    currentCatalogName = '';
    currentFile = null;
    isNewVersion = false;
  }

  function editFile(file) {
    // Create a proper copy of the file to avoid reference issues
    // Always rebuild the fileToEdit object from scratch
    fileToEdit = null;
    setTimeout(() => {
      fileToEdit = JSON.parse(JSON.stringify(file));
      showEditModal = true;
    }, 0);
  }

  function closeEditModal() {
    showEditModal = false;
    // Reset fileToEdit on close
    setTimeout(() => {
      fileToEdit = null;
    }, 100);
  }

  async function handleUpload(event) {
    console.log("Uploading files:", event.detail);
    const onComplete = event.detail.onComplete;
    let success = false;

    try {
      const formData = new FormData();

      for (const file of event.detail.files) {
        formData.append('file', file);
      }

      let url;
      if (event.detail.isNewVersion && event.detail.existingFileId) {
        // Upload a new version of an existing file
        url = `/api/files/${event.detail.existingFileId}/version`;
      } else {
        // Upload a new file to the catalog
        url = `/api/catalogs/${event.detail.catalogId}/upload`;
      }

      const response = await httpCall(url, {
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
        fetchCatalogFiles($selectedCatalogStore.id);
      }
    }
  }

  async function downloadFile(fileId, fallbackFilename = 'download') {
    try {
      const downloadUrl = `/api/files/${fileId}/download`;

      // Use httpCall to include JWT authentication
      const response = await httpCall(downloadUrl, {
        method: 'GET'
      });

      if (response.ok) {
        // Get the file as a blob
        const blob = await response.blob();

        // Get filename from headers (check both cases due to AWS Lambda normalization)
        let contentDisposition = response.headers.get('Content-Disposition') || response.headers.get('content-disposition');
        console.log('Content-Disposition header:', contentDisposition);

        let filename = fallbackFilename;
        if (contentDisposition) {
          console.log('Raw Content-Disposition:', JSON.stringify(contentDisposition));
          // Try multiple patterns to extract filename
          let filenameMatch = contentDisposition.match(/filename\*?="?([^"]+)"?/);
          if (!filenameMatch) {
            filenameMatch = contentDisposition.match(/filename\*?=([^;\s]+)/);
          }
          if (filenameMatch) {
            const rawFilename = filenameMatch[1].replace(/"/g, '');
            filename = decodeURIComponent(rawFilename);
            console.log('Extracted filename from header:', filename);
          }
        }
        
        // Also check for X-Suggested-Filename header as fallback
        if (filename === fallbackFilename) {
          const suggestedFilename = response.headers.get('X-Suggested-Filename') || response.headers.get('x-suggested-filename');
          if (suggestedFilename) {
            filename = suggestedFilename;
            console.log('Using X-Suggested-Filename:', filename);
          }
        }

        // Create download link
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        console.log('filename:', filename);
        link.download = filename;
        console.log('link:', link);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      } else {
        console.error("Download failed:", response.status, response.statusText);
        alert("Error downloading file. Please try again.");
      }
    } catch (error) {
      console.error("Download error:", error);
      alert("Error downloading file. Please try again.");
    }
  }

  async function handleFileUpdate(event) {
    const { id, description, status, confidentiality } = event.detail;

    try {
      const response = await httpCall(`/api/files/${id}`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ description, status, confidentiality })
      });

      if (response.ok) {
        const result = await response.json();
        console.log("File update successful:", result);

        if ($selectedCatalogStore) {
          await fetchCatalogFiles($selectedCatalogStore.id);
        }

        // After success, close the modal
        setTimeout(() => {
          closeEditModal();
        }, 500); // Small delay to show the success state
      } else {
        console.error("File update failed:", response.status, response.statusText);
        const errorData = await response.json();
        console.error("Error details:", errorData);
        alert("Error updating file. Please try again.");
        closeEditModal(); // Close on error too
      }
    } catch (error) {
      console.error("File update error:", error);
      alert("Error updating file. Please try again.");
      closeEditModal(); // Close on error too
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
        
        <!-- DEBUG INFO - HIDDEN FOR NOW -->
        <!-- 
        <div style="background: #f0f0f0; padding: 10px; margin: 10px 0; border: 1px solid #ccc;">
          <h4>DEBUG - Catalog Permissions Info:</h4>
          <p><strong>User Role:</strong> {$userRole}</p>
          <p><strong>Can Manage Permissions:</strong> {canManagePermissions}</p>
          <p><strong>Selected Catalog ID:</strong> {$selectedCatalogStore?.id}</p>
          
          <h5>Database Permission (catalog_users table):</h5>
          {#if dbPermissionInfo}
            {#if dbPermissionInfo.has_permission_row}
              <p><strong>Database Permission:</strong> {dbPermissionInfo.permission}</p>
              <p><strong>User ID:</strong> {dbPermissionInfo.user_id}</p>
              <p><strong>User Email:</strong> {dbPermissionInfo.user_email}</p>
              <p><strong>User Is Admin:</strong> {dbPermissionInfo.user_is_admin}</p>
            {:else}
              <p><strong>Database Permission:</strong> NO ROW</p>
              <p><strong>User ID:</strong> {dbPermissionInfo.user_id}</p>
              <p><strong>User Email:</strong> {dbPermissionInfo.user_email}</p>
              <p><strong>User Is Admin:</strong> {dbPermissionInfo.user_is_admin}</p>
            {/if}
          {:else}
            <p><strong>Database Permission:</strong> Loading...</p>
          {/if}
          
          <h5>Permission Check API Result:</h5>
          <p><strong>Permission Check Result:</strong> {JSON.stringify(permissionCheckResult, null, 2)}</p>
          <p><strong>Permission Check Error:</strong> {permissionCheckError}</p>
          <p><strong>API URL:</strong> {$selectedCatalogStore?.id ? `/api/catalogs/${$selectedCatalogStore.id}/can-manage-permissions` : 'No catalog ID'}</p>
        </div>
        -->
        
        {#if canManagePermissions}
        <button class="lock-button" on:click={() => {console.log('Catalog ID:', $selectedCatalogStore.id);viewCatalogPermissions($selectedCatalogStore.id)}}>
          <span class="lock-lock">🔒</span> {$i18nStore.t('catalog_permissions')}</button>
        {/if}
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
              <th>{$i18nStore.t('document_upload_date')}</th>
              <th>{$i18nStore.t('document_status')}</th>
              <th>{$i18nStore.t('document_version')}</th>
              <th>{$i18nStore.t('document_size')}</th>
              <th>{$i18nStore.t('document_confidentiality')}</th>
              <th colspan="3">{$i18nStore.t('actions_column')}</th>
            </tr>
            </thead>
            <tbody>
            {#each $catalogFilesStore as file}
              <tr>
                <td class="file-info-cell">
                  <div class="file-name">{file.name || ''}</div>
                  {#if file.summary || file.description}
                    <div class="file-description">{file.summary || file.description || ''}</div>
                  {/if}
                </td>
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
                  <span class="confidentiality-badge {file.confidentiality ? 'confidential' : 'public'}">
                    {file.confidentiality ? $i18nStore.t('confidential') || 'Confidential' : $i18nStore.t('public') || 'Public'}
                  </span>
                </td>
                <td>
                  <button class="icon-button edit-button" on:click={() => editFile(file)} title={$i18nStore.t('edit_document')}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                      <path d="M12.854.146a.5.5 0 0 0-.707 0L10.5 1.793 14.207 5.5l1.647-1.646a.5.5 0 0 0 0-.708l-3-3zm.646 6.061L9.793 2.5 3.293 9H3.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.207l6.5-6.5zm-7.468 7.468A.5.5 0 0 1 6 13.5V13h-.5a.5.5 0 0 1-.5-.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.5-.5V10h-.5a.499.499 0 0 1-.175-.032l-.179.178a.5.5 0 0 0-.11.168l-2 5a.5.5 0 0 0 .65.65l5-2a.5.5 0 0 0 .168-.11l.178-.178z"/>
                    </svg>
                  </button>
                </td>
                <td>
                <button class="icon-button upload-button" on:click={() => uploadNewVersion(file)} title={$i18nStore.t('upload_new_version') || 'Upload new version'}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                      <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
                      <path d="M7.646 1.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 2.707V11.5a.5.5 0 0 1-1 0V2.707L5.354 4.854a.5.5 0 1 1-.708-.708l3-3z"/>
                    </svg>
                  </button>
                </td>
                <td>
                  <button class="icon-button download-button" on:click={() => downloadFile(file.id, file.name)} title={$i18nStore.t('download_file') || 'Download file'}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                      <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
                      <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"/>
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
  isNewVersion={isNewVersion}
  existingFile={currentFile}
  on:close={closeUploadModal}
  on:upload={handleUpload}
/>

<EditModal
  show={showEditModal}
  file={fileToEdit}
  i18nStore={$i18nStore}
  on:close={closeEditModal}
  on:update={handleFileUpdate}
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

  .download-button {
    color: #3182ce;
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

  .confidentiality-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 500;
    text-align: center;
  }

  .confidentiality-badge.confidential {
    background-color: #fed7d7;
    color: #c53030;
  }

  .confidentiality-badge.public {
    background-color: #c6f6d5;
    color: #276749;
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

  .file-info-cell {
    min-width: 200px;
    max-width: 300px;
  }

  .file-name {
    font-weight: 600;
    color: #2d3748;
    margin-bottom: 4px;
    word-wrap: break-word;
  }

  .file-description {
    font-size: 0.875rem;
    color: #718096;
    line-height: 1.4;
    word-wrap: break-word;
  }

</style>
