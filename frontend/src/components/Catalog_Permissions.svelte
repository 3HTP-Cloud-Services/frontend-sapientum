<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { i18nStore } from '../lib/i18n.js';

  export let switchSection;
  export let activeSectionStore;
  export let currentCatalogId = null;
  
  let users = [];
  let loading = true;
  let error = null;
  let showAddUserModal = false;
  let showEditUserModal = false;
  let editingUser = null;
  
  onMount(async () => {
    await loadUsers();
  });
  
  async function loadUsers() {
    loading = true;
    error = null;
    
    try {
      const response = await fetch(`/api/catalogs/${currentCatalogId}/users`, {
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
    editingUser = { ...user };
    showEditUserModal = true;
  }
  
  function openAddUserModal() {
    editingUser = { email: '', fullName: '', role: 'lector' };
    showAddUserModal = true;
  }
  
  function closeModals() {
    showAddUserModal = false;
    showEditUserModal = false;
  }
  
  async function saveUser() {
    // This would save to API in a real implementation
    closeModals();
    await loadUsers();
  }
  
  async function removeUser(userId) {
    if (confirm($i18nStore.t('confirm_remove_user'))) {
      // This would delete via API in a real implementation
      users = users.filter(user => user.id !== userId);
    }
  }

  function backToCatalogDetail() {
    switchSection('catalog-detail');
  }
</script>

<div class="section-header">
  <h2>{$i18nStore.t('catalog_permissions')}</h2>
  <button class="back-button" on:click={backToCatalogDetail}>← {$i18nStore.t('back_to_catalog_details')}</button>
</div>

<div class="catalog-permissions-section">
  <div class="add-user-container">
    <button class="add-user-button" on:click={openAddUserModal}>
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
          <th>{$i18nStore.t('user_column')}</th>
          <th>{$i18nStore.t('email_label')}</th>
          <th>Role</th>
          <th>{$i18nStore.t('actions_column')}</th>
        </tr>
      </thead>
      <tbody>
        {#each users as user (user.id)}
          <tr in:fade={{ duration: 200 }}>
            <td>{user.fullName}</td>
            <td>{user.email}</td>
            <td>{user.role}</td>
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
</style>