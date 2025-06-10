<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { i18nStore } from '../../../shared-components/utils/i18n.js';
  import UserModal from './UserModal.svelte';
  import { httpCall } from '../../../shared-components/utils/httpCall.js';

  export let switchSection;
  export let activeSectionStore;
  export let currentCatalogId = null;

  let users = [];
  let loading = true;
  let error = null;
  let showUserModal = false;
  let editingUser = null;

  onMount(async () => {
    console.log('Catalog_Permissions mounted with catalogId:', currentCatalogId);
    if (currentCatalogId) {
      await loadUsers();
    }
  });

  async function loadUsers() {
    loading = true;
    error = null;

    try {
      const response = await httpCall(`/api/catalogs/${currentCatalogId}/users`, {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }

      users = await response.json();
    } catch (err) {
      error = err.message;
      console.error('Error loading users:', err);
    } finally {
      loading = false;
    }
  }

  function editUser(user) {
    editingUser = {
      id: user.id,
      email: user.email,
      permission: user.permission
    };
    showUserModal = true;
  }

  function addNewUser() {
    editingUser = {
      id: null,
      userId: null,
      email: '',
      permission: 'permission-read-only'
    };
    showUserModal = true;
  }

  function closeUserModal() {
    showUserModal = false;
    editingUser = null;
  }

  async function saveUser(event) {
    const userData = event.detail;
    console.log('Saving user data:', userData);

    try {
      const userId = userData.id || userData.user_id;
      console.log('Using user_id:', userId);

      const url = `/api/catalogs/${currentCatalogId}/users`;
      const response = await httpCall(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          user_id: userId,
          permission: userData.permission
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Error saving user permission');
      }

      closeUserModal();
      await loadUsers();
    } catch (err) {
      error = err.message;
      console.error('Error saving user permission:', err);
    }
  }

  async function removeUser(userId) {
    if (confirm($i18nStore.t('confirm_remove_user'))) {
      try {
        const response = await httpCall(`/api/catalogs/${currentCatalogId}/users/${userId}`, {
          method: 'DELETE',
          credentials: 'include'
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Error removing user');
        }

        await loadUsers();
      } catch (err) {
        error = err.message;
        console.error('Error removing user:', err);
      }
    }
  }

  function backToCatalogDetail() {
    switchSection('catalog-detail');
  }

  function getPermissionText(permission) {
    return $i18nStore.t(permission);
  }
</script>

<div class="section-header">
  <h2>{$i18nStore.t('catalog_permissions')}</h2>
  <button class="back-button" on:click={backToCatalogDetail}>← {$i18nStore.t('back_to_catalog_details')}</button>
</div>

<div class="catalog-permissions-section">
  <div class="add-user-container">
    <button class="add-user-button" on:click={addNewUser}>
      {$i18nStore.t('add_user_button')}
    </button>
  </div>

  {#if loading}
    <p>{$i18nStore.t('loading_users')}</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else if users.length === 0}
    <p>{$i18nStore.t('no_users')}</p>
  {:else}
    <table class="users-table">
      <thead>
        <tr>
          <th>{$i18nStore.t('email_label')}</th>
          <th>{$i18nStore.t('doc_access_label')}</th>
          <th>{$i18nStore.t('actions_column')}</th>
        </tr>
      </thead>
      <tbody>
        {#each users as user (user.id)}
          <tr in:fade={{ duration: 200 }}>
            <td>{user.email}</td>
            <td><span class="permission-badge {user.permission}">{getPermissionText(user.permission)}</span></td>
            <td class="action-buttons">
              <button class="edit-button" on:click={() => editUser(user)}>
                {$i18nStore.t('edit_button')}
              </button>
              <button class="delete-button" on:click={() => removeUser(user.id)}>
                {$i18nStore.t('delete_button')}
              </button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</div>

<UserModal
  show={showUserModal}
  user={editingUser}
  catalogMode={true}
  catalogId={currentCatalogId}
  on:close={closeUserModal}
  on:save={saveUser}
/>

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

  .add-user-container {
    margin-bottom: 1rem;
  }

  .add-user-button {
    background-color: #4299e1;
    color: white;
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
    font-weight: 500;
  }

  .add-user-button:hover {
    background-color: #3182ce;
  }

  .users-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 1rem;
  }

  .users-table th, .users-table td {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
  }

  .users-table th {
    background-color: #f7fafc;
    font-weight: 600;
  }

  .action-buttons {
    display: flex;
    gap: 0.5rem;
  }

  .edit-button, .delete-button {
    padding: 0.25rem 0.5rem;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
    font-size: 0.75rem;
  }

  .edit-button {
    background-color: #4299e1;
    color: white;
  }

  .delete-button {
    background-color: #e53e3e;
    color: white;
  }

  .edit-button:hover {
    background-color: #3182ce;
  }

  .delete-button:hover {
    background-color: #c53030;
  }

  .error {
    color: #e53e3e;
  }

  .permission-badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .permission-not-allowed {
    background-color: #fed7d7;
    color: #c53030;
  }

  .permission-read-only {
    background-color: #feebc8;
    color: #c05621;
  }

  .permission-full {
    background-color: #c6f6d5;
    color: #276749;
  }
</style>
