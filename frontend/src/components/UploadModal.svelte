<script>
  import { createEventDispatcher } from 'svelte';
  
  export let show = false;
  export let catalogId = null;
  export let catalogName = '';
  export let i18nStore;
  
  let selectedFiles = [];
  let dragActive = false;
  
  const dispatch = createEventDispatcher();
  
  function closeModal() {
    dispatch('close');
  }
  
  function handleDragEnter(e) {
    e.preventDefault();
    e.stopPropagation();
    dragActive = true;
  }
  
  function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    dragActive = false;
  }
  
  function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    dragActive = true;
  }
  
  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    dragActive = false;
    
    if (e.dataTransfer.files) {
      const fileArray = Array.from(e.dataTransfer.files);
      selectedFiles = [...selectedFiles, ...fileArray];
    }
  }
  
  function handleFileSelect(e) {
    if (e.target.files) {
      const fileArray = Array.from(e.target.files);
      selectedFiles = [...selectedFiles, ...fileArray];
    }
  }
  
  function removeFile(index) {
    selectedFiles = selectedFiles.filter((_, i) => i !== index);
  }
  
  function uploadFiles() {
    console.log("Uploading files to catalog:", catalogId, selectedFiles);
    dispatch('upload', { catalogId, files: selectedFiles });
  }
</script>

{#if show}
  <div class="modal-overlay" on:click={closeModal}>
    <div class="modal-content upload-modal" on:click|stopPropagation>
      <div class="modal-header">
        <h2>{i18nStore.t('upload_documents_title')}</h2>
        <button class="close-button" on:click={closeModal}>×</button>
      </div>
      
      <div class="modal-body">
        <p class="catalog-name-display">
          {catalogName}
        </p>
        
        <div 
          class="dropzone {dragActive ? 'active' : ''}"
          on:dragenter={handleDragEnter}
          on:dragleave={handleDragLeave}
          on:dragover={handleDragOver}
          on:drop={handleDrop}
        >
          <input 
            type="file" 
            id="file-upload" 
            multiple 
            on:change={handleFileSelect}
            style="display: none;"
          />
          <label for="file-upload" class="file-upload-label">
            <img src="./images/upload.png" alt="Upload" class="upload-icon-large"/>
            <p>{i18nStore.t('drop_files_here')}</p>
          </label>
        </div>
        
        <div class="selected-files-section">
          <h3>{i18nStore.t('selected_files')}</h3>
          
          {#if selectedFiles.length === 0}
            <p class="no-files">{i18nStore.t('no_files_selected')}</p>
          {:else}
            <ul class="file-list">
              {#each selectedFiles as file, index}
                <li class="file-item">
                  <span class="file-name">{file.name}</span>
                  <button class="remove-file" on:click={() => removeFile(index)}>×</button>
                </li>
              {/each}
            </ul>
          {/if}
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="cancel-button" on:click={closeModal}>{i18nStore.t('cancel_button')}</button>
        <button 
          class="save-button" 
          on:click={uploadFiles}
          disabled={selectedFiles.length === 0}
        >
          {i18nStore.t('upload_button')}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
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
  
  .upload-modal {
    max-width: 600px;
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
    color: #2d3748;
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
  
  .catalog-name-display {
    font-weight: 500;
    color: #2d3748;
    margin-bottom: 1rem;
    font-size: 1.1rem;
  }
  
  .dropzone {
    border: 2px dashed #cbd5e0;
    border-radius: 8px;
    padding: 2rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    margin-bottom: 1.5rem;
  }
  
  .dropzone.active {
    border-color: #5970ff;
    background-color: rgba(89, 112, 255, 0.05);
  }
  
  .file-upload-label {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    width: 100%;
    height: 100%;
  }
  
  .upload-icon-large {
    width: 48px;
    height: 48px;
    margin-bottom: 1rem;
  }
  
  .selected-files-section {
    margin-top: 1.5rem;
  }
  
  .selected-files-section h3 {
    margin-top: 0;
    margin-bottom: 0.75rem;
    color: #2d3748;
    font-size: 1rem;
  }
  
  .no-files {
    color: #718096;
    font-style: italic;
  }
  
  .file-list {
    list-style: none;
    padding: 0;
    margin: 0;
    max-height: 200px;
    overflow-y: auto;
  }
  
  .file-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem;
    border-bottom: 1px solid #e2e8f0;
  }
  
  .file-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-right: 0.5rem;
  }
  
  .remove-file {
    background: none;
    border: none;
    color: #718096;
    cursor: pointer;
    font-size: 1.25rem;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
  }
  
  .remove-file:hover {
    background-color: #e2e8f0;
    color: #e53e3e;
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