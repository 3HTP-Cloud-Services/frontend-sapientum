<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { i18nStore } from '../lib/i18n.js';

  export let show = false;
  export let user;
  export let catalogMode = false;
  export let catalogId = null;
  export let errorMessage = '';

  let availableUsers = [];
  let loading = false;
  let error = '';

  const dispatch = createEventDispatcher();

  let previouslyLoaded = false;
  
  $: if (show && catalogMode && catalogId && !user.id && !previouslyLoaded) {
    previouslyLoaded = true;
    loadAvailableUsers();
  }
  
  $: if (!show) {
    previouslyLoaded = false;
  }

  async function loadAvailableUsers() {
    if (!catalogId) {
      console.error('No catalogId provided when loading available users');
      return;
    }

    console.log('Loading available users for catalog ID:', catalogId);
    loading = true;
    error = '';

    try {
      const url = `/api/catalogs/${catalogId}/available-users`;
      console.log('Fetching from URL:', url);
      
      const response = await fetch(url, {
        credentials: 'include'
      });

      if (response.ok) {
        availableUsers = await response.json();
        console.log('Available users loaded:', availableUsers);
        
        if (availableUsers.length > 0) {
          // Only set the user ID and email if they haven't been set yet
          if (!user.userId) {
            user.userId = availableUsers[0].id;
            user.email = availableUsers[0].email;
            console.log('Set initial user selection to:', user.userId, user.email);
          }
        }
      } else {
        console.error('Error response when fetching available users:', response.status);
        error = 'Error fetching available users';
      }
    } catch (err) {
      console.error('Exception when loading available users:', err);
      error = 'Error loading users';
    } finally {
      loading = false;
    }
  }

  function close() {
    dispatch('close');
  }

  function save() {
    if (catalogMode && !user.id) {
      // For new user being added to catalog
      dispatch('save', {
        ...user,
        user_id: user.userId,
        permission: user.permission
      });
    } else {
      dispatch('save', user);
    }
  }

  function handleUserSelect(event) {
    const userId = parseInt(event.target.value);
    const selectedUser = availableUsers.find(u => u.id === userId);
    if (selectedUser) {
      user.userId = selectedUser.id;
      user.email = selectedUser.email;
      user.fullName = selectedUser.email;
    }
  }
</script>

{#if show}
  <div class="modal-backdrop">
    <div class="modal">
      <h2>{user.id ? $i18nStore.t('edit_user') : $i18nStore.t('add_new_user')}</h2>

      {#if errorMessage}
        <p class="error">{errorMessage}</p>
      {/if}

      {#if catalogMode && !user.id}
        {#if loading}
          <p>{$i18nStore.t('loading_users')}</p>
        {:else if error}
          <p class="error">{error}</p>
        {:else if availableUsers.length === 0}
          <p>{$i18nStore.t('no_users')}</p>
        {:else}
          <div class="form-group">
            <label for="userId">{$i18nStore.t('user_column')}</label>
            <select id="userId" bind:value={user.userId} on:change={handleUserSelect}>
              {#each availableUsers as availableUser}
                <option value={availableUser.id}>{availableUser.email}</option>
              {/each}
            </select>
          </div>

          <div class="form-group">
            <label for="permission">{$i18nStore.t('doc_access_label')}</label>
            <select id="permission" bind:value={user.permission}>
              <option value="permission-not-allowed">{$i18nStore.t('permission-not-allowed')}</option>
              <option value="permission-read-only">{$i18nStore.t('permission-read-only')}</option>
              <option value="permission-full">{$i18nStore.t('permission-full')}</option>
            </select>
          </div>
        {/if}
      {:else if catalogMode && user.id}
        <div class="form-group">
          <label for="email">{$i18nStore.t('email_label')}</label>
          <input type="email" id="email" value={user.email} disabled readonly />
        </div>

        <div class="form-group">
          <label for="permission">{$i18nStore.t('doc_access_label')}</label>
          <select id="permission" bind:value={user.permission}>
            <option value="permission-not-allowed">{$i18nStore.t('permission-not-allowed')}</option>
            <option value="permission-read-only">{$i18nStore.t('permission-read-only')}</option>
            <option value="permission-full">{$i18nStore.t('permission-full')}</option>
          </select>
        </div>
      {:else}
        <div class="form-group">
          <label for="email">{$i18nStore.t('email_label')}</label>
          <input type="email" id="email" bind:value={user.email} required />
        </div>

        <div class="form-group checkbox">
          <label>
            <input type="checkbox" bind:checked={user.chatAccess} />
            {$i18nStore.t('enable_chat_access')}
          </label>
        </div>

        <div class="form-group checkbox">
          <label>
            <input type="checkbox" bind:checked={user.isAdmin} />
            {$i18nStore.t('admin_rights')}
          </label>
        </div>
      {/if}

      <div class="modal-actions">
        <button class="cancel-button" on:click={close}>{$i18nStore.t('cancel_button')}</button>
        <button class="save-button" on:click={save}>{$i18nStore.t('save_button')}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 100;
  }

  .modal {
    background-color: white;
    border-radius: 8px;
    padding: 2rem;
    width: 100%;
    max-width: 500px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .modal h2 {
    margin-top: 0;
    color: #2d3748;
    margin-bottom: 1.5rem;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #4a5568;
  }

  .form-group.checkbox label {
    display: flex;
    align-items: center;
    font-weight: normal;
  }

  .form-group.checkbox input {
    margin-right: 0.5rem;
  }

  input[type="email"],
  input[type="text"],
  select {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    font-size: 1rem;
  }

  input:disabled {
    background-color: #f7fafc;
    cursor: not-allowed;
  }

  .error {
    color: #e53e3e;
    margin-bottom: 1rem;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 1.5rem;
  }

  .cancel-button {
    background-color: #e2e8f0;
    color: #4a5568;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
  }

  .save-button {
    background-color: #4299e1;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
  }
</style>
