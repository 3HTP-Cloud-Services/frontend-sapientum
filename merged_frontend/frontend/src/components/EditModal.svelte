<script>
  import { createEventDispatcher, onMount } from 'svelte';

  export let show = false;
  export let file = null;
  export let i18nStore;

  let fileData = {
    id: null,
    description: '',
    status: 'Published',
    confidentiality: false
  };

  let isSaving = false;

  $: if (show && file) {
    // Reset saving state whenever modal is opened
    isSaving = false;

    // Only update data if it's a new file
    if (file !== fileData.originalFile) {
      fileData = {
        id: file.id,
        description: file.summary || file.description || '',
        status: file.status || 'Published',
        confidentiality: file.confidentiality === true,
        originalFile: file
      };
    }
  }

  const dispatch = createEventDispatcher();

  function closeModal() {
    if (isSaving) return;
    dispatch('close');
  }

  function saveChanges() {
    isSaving = true;
    dispatch('update', {
      id: fileData.id,
      description: fileData.description,
      status: fileData.status,
      confidentiality: fileData.confidentiality
    });
  }
</script>

{#if show && file}
  <div class="modal-overlay" on:click={closeModal}>
    <div class="modal-content edit-modal" on:click|stopPropagation>
      <div class="modal-header">
        <h2>{i18nStore.t('edit_document') || 'Edit Document'}</h2>
        <button class="close-button" on:click={closeModal}>×</button>
      </div>

      <div class="modal-body">
        <form id="editFileForm">
          <div class="form-group">
            <label for="fileName">{i18nStore.t('document_name') || 'Document Name'}</label>
            <input id="fileName" type="text" value={file.name} disabled />
          </div>

          <div class="form-group">
            <label for="fileDescription">{i18nStore.t('document_description') || 'Description'}</label>
            <textarea id="fileDescription" bind:value={fileData.description} disabled={isSaving}></textarea>
          </div>

          <div class="form-group">
            <label for="fileStatus">{i18nStore.t('document_status') || 'Status'}</label>
            <select id="fileStatus" bind:value={fileData.status} disabled={isSaving}>
              <option value="Draft">Draft</option>
              <option value="For Review">For Review</option>
              <option value="Published">Published</option>
              <option value="Deprecated">Deprecated</option>
            </select>
          </div>

          <div class="form-group">
            <label for="fileConfidentiality">{i18nStore.t('document_confidentiality') || 'Confidentiality'}</label>
            <div class="toggle-container">
              <label class="toggle" class:disabled={isSaving}>
                <input
                  type="checkbox"
                  id="fileConfidentiality"
                  bind:checked={fileData.confidentiality}
                  disabled={isSaving}
                >
                <span class="toggle-slider"></span>
                <span class="toggle-label">
                  {fileData.confidentiality ?
                    (i18nStore.t('confidential') || 'Confidential') :
                    (i18nStore.t('public') || 'Public')}
                </span>
              </label>
            </div>
          </div>
        </form>
      </div>

      <div class="modal-footer">
        <button class="cancel-button" on:click={closeModal} disabled={isSaving}>{i18nStore.t('cancel_button') || 'Cancel'}</button>
        <button class="save-button" on:click={saveChanges} disabled={isSaving}>
          {isSaving ? (i18nStore.t('saving') || 'Saving...') : (i18nStore.t('save_button') || 'Save')}
        </button>
      </div>

      {#if isSaving}
        <div class="saving-overlay">
          <div class="spinner"></div>
          <p>{i18nStore.t('saving') || 'Saving...'}</p>
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
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

  .edit-modal {
    max-width: 500px;
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
    color: #032b36;
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

  .form-group {
    margin-bottom: 1.5rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #032b36;
  }

  .form-group input[type="text"],
  .form-group textarea,
  .form-group select {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #cbd5e0;
    border-radius: 4px;
    font-size: 1rem;
  }

  .form-group input[disabled] {
    background-color: #edf2f7;
    cursor: not-allowed;
  }

  .form-group textarea {
    min-height: 100px;
    resize: vertical;
  }

  .toggle-container {
    display: flex;
    align-items: center;
  }

  .toggle {
    position: relative;
    display: inline-flex;
    align-items: center;
    cursor: pointer;
  }

  .toggle input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-slider {
    position: relative;
    display: inline-block;
    width: 48px;
    height: 24px;
    background-color: #cbd5e0;
    border-radius: 24px;
    transition: 0.4s;
    margin-right: 10px;
  }

  .toggle-slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    border-radius: 50%;
    transition: 0.4s;
  }

  input:checked + .toggle-slider {
    background-color: #c53030;
  }

  input:checked + .toggle-slider:before {
    transform: translateX(24px);
  }

  .toggle-label {
    font-size: 0.875rem;
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
    background-color: #4a5ee2;
  }

  .saving-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.8);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    z-index: 10;
    border-radius: 8px;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #5970ff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
</style>
