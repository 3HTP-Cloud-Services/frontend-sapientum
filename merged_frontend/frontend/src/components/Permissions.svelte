<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { i18nStore } from '../../../shared-components/utils/i18n.js';
  import UserModal from './UserModal.svelte';

  export let users = [];
  export let domains = [];
  export let loadingUsers = false;
  export let usersError = '';
  export let successMessage = '';
  export let editingUser = null;
  export let showUserModal = false;
  export let activeSectionStore;
  export let allowedDomains = [{ 'id': -1, 'name': '' }];
  export let domainsError = '';

  // Track which toggles are currently being processed
  let togglesInFlight = {};

  // Get current user from auth store to check if switching own admin flag
  import { userEmail } from '../../../shared-components/utils/auth.js';

  export async function fetchUsers() {
    try {
      loadingUsers = true;
      usersError = '';
      const response = await fetch('/api/users', {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        users = data.users;
        allowedDomains = data.domains;
        console.log('allowedDomains', allowedDomains);
      } else if (response.status === 401) {
        // User is not authenticated
        push('/login');
      } else if (response.status === 403) {
        // User does not have admin permissions
        usersError = $i18nStore.t('access_denied_admin_required') || 'Access denied. Admin permissions required.';

        const errorData = await response.json().catch(() => ({}));
        if (errorData && errorData.error) {
          usersError = errorData.error;
        }
      } else {
        console.error('Error fetching users:', response.status, response.statusText);
        usersError = 'Error al cargar usuarios';
      }
    } catch (err) {
      console.error('Users fetch error:', err);
      usersError = 'Error de conexión';
    } finally {
      loadingUsers = false;
    }
  }

  export function editUser(user) {
    editingUser = { ...user };
    showUserModal = true;
  }

  export function addNewUser() {
    editingUser = {
      id: null,
      email: '',
      documentAccess: 'Lectura',
      chatAccess: false,
      isAdmin: false
    };
    showUserModal = true;
  }

  export async function saveUser() {
    usersError = '';
    try {
      if (editingUser.id) {
        const response = await fetch(`/api/users/${editingUser.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(editingUser),
          credentials: 'include'
        });

        if (response.ok) {
          const updatedUser = await response.json();
          const index = users.findIndex(u => u.id === updatedUser.id);
          if (index !== -1) {
            users[index] = updatedUser;
            users = [...users]; // Trigger reactivity
          }
        } else {
          console.error('Error updating user:', response.status);
          usersError = 'Error al actualizar usuario';
        }
      } else {
        const response = await fetch('/api/users', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(editingUser),
          credentials: 'include'
        });

        if (response.ok) {
          const newUser = await response.json();
          users = [...users, newUser]; // Add to local data
        } else {
          console.error('Error creating user:', response.status);
          const errorData = await response.json().catch(() => ({}));

          if (errorData && errorData.error) {
            if (errorData.error === 'invalid_email_error') {
              usersError = $i18nStore.t('invalid_email_error') || 'Invalid email. Must contain a valid domain';
            } else if (errorData.error === 'no_allowed_domains_error') {
              usersError = $i18nStore.t('no_allowed_domains_error') || 'No allowed domains are configured';
            } else if (errorData.error === 'domain_not_allowed_error') {
              usersError = $i18nStore.t('domain_not_allowed_error') || 'The domain is not in the list of allowed domains';
              if (errorData.domain) {
                usersError += `: ${errorData.domain}`;
              }
            } else {
              usersError = errorData.error;
            }
          } else {
            usersError = 'Error al crear usuario';
          }

        }
      }

      closeUserModal();
    } catch (err) {
      console.error('Error saving user:', err);
      usersError = 'Error de conexión al guardar usuario';
    }
  }

  export async function deleteUser(userId) {
    if (!confirm('¿Estás seguro de que quieres eliminar este usuario?')) {
      return;
    }

    try {
      const response = await fetch(`/api/users/${userId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.ok) {
        users = users.filter(u => u.id !== userId);
      } else {
        console.error('Error deleting user:', response.status);
        usersError = 'Error al eliminar usuario';
      }
    } catch (err) {
      console.error('Error deleting user:', err);
      usersError = 'Error de conexión al eliminar usuario';
    }
  }

  export async function toggleUserProperty(userId, property) {
    try {
      // Create a unique key for this toggle
      const toggleKey = `${userId}-${property}`;

      // Mark this toggle as in flight
      togglesInFlight = { ...togglesInFlight, [toggleKey]: true };

      usersError = '';
      successMessage = '';
      const response = await fetch(`/api/users/${userId}/toggle/${property}`, {
        method: 'PUT',
        credentials: 'include'
      });

      if (response.ok) {
        const updatedUser = await response.json();
        const index = users.findIndex(u => u.id === updatedUser.id);
        if (index !== -1) {
          users[index] = updatedUser;
          users = [...users]; // Trigger reactivity

          // Show success message
          successMessage = $i18nStore.t('saved_successfully') || 'Changes saved successfully';

          // Clear success message after 3 seconds
          setTimeout(() => {
            successMessage = '';
          }, 3000);
        }
      } else {
        console.error(`Error toggling ${property}:`, response.status);
        const errorData = await response.json().catch(() => ({}));

        if (response.status === 403) {
          // Check if it's a specific error message or a general access denied
          if (errorData.error === 'cannot_remove_own_admin') {
            usersError = $i18nStore.t('cannot_remove_own_admin') || 'You cannot remove your own administrator permissions.';
          } else {
            usersError = errorData.error || $i18nStore.t('access_denied_admin_required') || 'Access denied. Administrator permissions required.';
          }
        } else {
          usersError = errorData.error || `Error al cambiar ${property}`;
        }
      }
    } catch (err) {
      console.error(`Error toggling ${property}:`, err);
      usersError = `Error de conexión al cambiar ${property}`;
    } finally {
      // Remove this toggle from in flight regardless of success or failure
      const toggleKey = `${userId}-${property}`;
      const { [toggleKey]: _, ...rest } = togglesInFlight;
      togglesInFlight = rest;
    }
  }

  export function closeUserModal() {
    showUserModal = false;
    editingUser = null;
    usersError = '';
  }

  function handleSave(event) {
    editingUser = event.detail;
    saveUser();
  }

  function addDomain() {
    console.log('adding domain');
    allowedDomains = [...allowedDomains, {name: '', id: -1}];
  }

  async function removeDomain(i) {
    console.log('remove domain', i);
    const domain = allowedDomains[i];

    // Only call the API if this is an existing domain with a valid ID
    if (domain && domain.id && domain.id > 0) {
      try {
        domainsError = '';
        const response = await fetch(`/api/allowed-domains/${domain.id}`, {
          method: 'DELETE',
          credentials: 'include'
        });

        if (!response.ok) {
          console.error('Error deleting domain:', response.status);

          if (response.status === 403) {
            domainsError = $i18nStore.t('access_denied_admin_required') || 'Access denied. Admin permissions required.';
          } else {
            domainsError = 'Error deleting domain';
          }

          const errorData = await response.json().catch(() => ({}));
          if (errorData && errorData.error) {
            if (errorData.error === 'domain_in_use_error') {
              domainsError = $i18nStore.t('domain_in_use_error') || 'Cannot delete domain because there are users associated with it';
              if (errorData.users && errorData.users.length > 0) {
                domainsError += `: ${errorData.users.join(', ')}`;
              }
            } else {
              domainsError = errorData.error;
            }
          }
          return; // Don't update local state if API call failed
        }

        // Display success message
        successMessage = $i18nStore.t('domain_deleted_successfully') || 'Domain deleted successfully';
        setTimeout(() => {
          successMessage = '';
        }, 3000);
      } catch (err) {
        console.error('Error deleting domain:', err);
        domainsError = 'Connection error while deleting domain';
        return; // Don't update local state if API call failed
      }
    }

    // Update local state
    allowedDomains = allowedDomains.filter((_, index) => index !== i);
  }

  function editDomain(index, value) {
    const updatedDomains = [...allowedDomains];
    updatedDomains[index].name = value;
    allowedDomains = updatedDomains;
  }

  async function saveDomains() {
    try {
      domainsError = '';
      // Filter out empty domains
      const domainsToSave = allowedDomains.filter(domain => domain.name.trim() !== '');

      // This would be replaced with an actual API call when backend is ready
      const response = await fetch('/api/allowed-domains', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ domains: domainsToSave }),
        credentials: 'include'
      });

      if (!response.ok) {
        console.error('Error saving domains:', response.status);

        if (response.status === 403) {
          domainsError = $i18nStore.t('access_denied_admin_required') || 'Access denied. Admin permissions required.';
        } else {
          domainsError = 'Error saving domains';
        }

        const errorData = await response.json().catch(() => ({}));
        if (errorData && errorData.error) {
          domainsError = errorData.error;
        }
      }
    } catch (err) {
      console.error('Error saving domains:', err);
      domainsError = 'Connection error while saving domains';
    }
  }

  $: if ($activeSectionStore === 'permissions') {
    console.log("Permissions section is now active");
    users = [];
    loadingUsers = true;
    fetchUsers();
  }
</script>

<div class="section-header">
  <h2>{$i18nStore.t('sidebar_permissions')}</h2>
  {#if successMessage}
    <div class="success-message" transition:fade={{ duration: 150 }}>
      {successMessage}
    </div>
  {/if}
</div>
<div class="permissions-section">
  <div class="permissions-table">
    {#if loadingUsers}
      <p transition:fade={{ duration: 150 }}>{$i18nStore.t('loading_users')}</p>
    {:else if usersError}
      <p class="error" transition:fade={{ duration: 150 }}>{usersError}</p>
    {:else if users.length === 0 && !loadingUsers}
      <p transition:fade={{ duration: 150 }}>{$i18nStore.t('no_users')}</p>
    {:else}
      <div transition:fade={{ duration: 150 }}>
        <table>
          <thead>
          <tr>
            <th>{$i18nStore.t('user_column') || 'User'}</th>
            <th>{$i18nStore.t('admin_rights_column') || 'Admin'}</th>
            <th>{$i18nStore.t('catalog_editor_column') || 'Catalog Editor'}</th>
            <th>{$i18nStore.t('chat_access_column') || 'Chat Access'}</th>
            <th>{$i18nStore.t('actions_column') || 'Actions'}</th>
          </tr>
          </thead>
          <tbody>
          {#each users as user}
            <tr>
              <td>{user.email}</td>
              <td>
                <label class="toggle-switch" class:disabled={user.email === $userEmail && user.isAdmin || togglesInFlight[`${user.id}-isAdmin`]}>
                  <input
                    type="checkbox"
                    checked={user.isAdmin}
                    on:change={() => toggleUserProperty(user.id, 'isAdmin')}
                    disabled={user.email === $userEmail && user.isAdmin || togglesInFlight[`${user.id}-isAdmin`]}
                    title={user.email === $userEmail && user.isAdmin ? ($i18nStore.t('cannot_remove_own_admin') || 'You cannot remove your own administrator permissions.') : togglesInFlight[`${user.id}-isAdmin`] ? 'Updating...' : ''}
                  >
                  <span class="toggle-slider round"></span>
                </label>
              </td>
              <td>
                <label class="toggle-switch" class:disabled={togglesInFlight[`${user.id}-isCatalogEditor`]}>
                  <input
                    type="checkbox"
                    checked={user.isCatalogEditor}
                    on:change={() => toggleUserProperty(user.id, 'isCatalogEditor')}
                    disabled={togglesInFlight[`${user.id}-isCatalogEditor`]}
                    title={togglesInFlight[`${user.id}-isCatalogEditor`] ? 'Updating...' : ''}
                  >
                  <span class="toggle-slider round"></span>
                </label>
              </td>
              <td>
                <label class="toggle-switch" class:disabled={togglesInFlight[`${user.id}-chatAccess`]}>
                  <input
                    type="checkbox"
                    checked={user.chatAccess}
                    on:change={() => toggleUserProperty(user.id, 'chatAccess')}
                    disabled={togglesInFlight[`${user.id}-chatAccess`]}
                    title={togglesInFlight[`${user.id}-chatAccess`] ? 'Updating...' : ''}
                  >
                  <span class="toggle-slider round"></span>
                </label>
              </td>
              <td>
                <!-- button class="edit-button" on:click={() => editUser(user)}>{$i18nStore.t('edit_button') || 'Edit'}</button -->
                <button class="delete-button" on:click={() => deleteUser(user.id)}>{$i18nStore.t('delete_button') || 'Delete'}</button>
              </td>
            </tr>
          {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
  <button class="sap_button add_user_button" on:click={addNewUser}>
    {$i18nStore.t('add_user_button')}
  </button>
</div>

<div class="domains-section">
  <h3>{$i18nStore.t('allowed_domains')}</h3>
  {#if domainsError}
    <p class="error">{domainsError}</p>
  {/if}
  <div class="domains-container">
    <table style="width:300px">
    {#each allowedDomains as domain, i}
      <tr>
        <td class="domain_td">
          <div class="domain-item">
            <input class="domain_input"
              type="text"
              value={domain.name}
              placeholder={$i18nStore.t('domain_placeholder')}
              on:input={(e) => editDomain(i, e.target.value)}
            />
          </div>
        </td><td class="domain_td">
          <button class="sap_button remove_button" on:click={() => removeDomain(i)}>{$i18nStore.t('remove_domain_button')}</button>
        </td>
      </tr>
    {/each}
    </table>
  </div>
  <div class="domains-actions">
    <button class="sap_button add_button" on:click={addDomain}>{$i18nStore.t('add_domain_button')}</button>
    <button class="sap_button save_button" on:click={saveDomains}>{$i18nStore.t('save_domains_button')}</button>
    <button class="sap_button reload_button" on:click={saveDomains}>
        <span class="reload_icon">⟳</span>{$i18nStore.t('reload_domains_button')}
    </button>
  </div>
</div>

<UserModal
  show={showUserModal}
  user={editingUser}
  catalogMode={false}
  errorMessage={usersError}
  on:close={closeUserModal}
  on:save={handleSave}
/>

<style>
  /* Permissions section */
  .permissions-table {
    margin-bottom: 1.5rem;
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    background-color: white;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  th, td {
    padding: 0.75rem 1rem;
    text-align: left;
  }

  th {
    background-color: #edf2f7;
    font-weight: bold;
    color: #4a5568;
  }

  tr:nth-child(even) {
    background-color: #f7fafc;
  }

  .edit-button, .edit-link {
    background-color: #4299e1;
    color: white;
    border: none;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
    margin-right: 0.5rem;
  }

  .delete-button {
    background-color: #e53e3e;
    color: white;
    border: none;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    cursor: pointer;
  }

  .add_button {
    padding: 0.5rem 1rem;
    background-color: #48bb78;
    color: white;
  }

  .remove_button {
    padding: 0.5rem 1rem;
    background-color: #ff2626;
    color: white;
    width: 90px;
  }

  .add_user_button {
    padding: 0.5rem 1rem;
    background-color: #48bb78;
    color: white;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .reload_button {
    background-color: #e53e3e;
    color: white;
    line-height: normal !important;
  }

  .reload_icon {
    font-size: 200%;
    line-height: 0;
    display: inline-block;
    vertical-align: middle;
    margin-right: 2px;
    position: relative;
    top: -5px;
  }

  /* Modal styles */
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

  .save_button {
    padding: 0.5rem 1rem;
    background-color: #4299e1;
    color: white;
  }

  /* Domains section */
  .domains-section {
    margin-top: 2rem;
    background-color: white;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .domains-section h3 {
    margin-top: 0;
    color: #2d3748;
    margin-bottom: 1rem;
  }

  .domains-container {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .domain-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .domains-actions {
    display: flex;
    gap: 1rem;
  }

  .error {
    color: #e53e3e;
    margin-bottom: 1rem;
  }

  .success-message {
    color: #38a169;
    background-color: #c6f6d5;
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    margin-left: 1rem;
    font-size: 0.875rem;
    font-weight: 500;
    display: inline-block;
    position: relative;
    top: -2px;
  }
  .domain_input {
    border: 1px solid green !important;
    background-color: #faffec;
    width: 250px !important;
  }
  .domain_td {
    vertical-align: top;
  }

  .section-header {
    display: flex;
    align-items: center;
    margin-bottom: 1.5rem;
    min-height: 2.5rem;
  }

  .toggle-switch {
    position: relative;
    display: inline-block;
    width: 40px;
    height: 24px;
  }

  .toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #ccc;
    transition: .4s;
  }

  .toggle-slider:before {
    position: absolute;
    content: "";
    height: 16px;
    width: 16px;
    left: 4px;
    bottom: 4px;
    background-color: white;
    transition: .4s;
  }

  input:checked + .toggle-slider {
    background-color: #4299e1;
  }

  input:focus + .toggle-slider {
    box-shadow: 0 0 1px #4299e1;
  }

  input:checked + .toggle-slider:before {
    transform: translateX(16px);
  }

  .toggle-slider.round {
    border-radius: 24px;
  }

  .toggle-slider.round:before {
    border-radius: 50%;
  }

  .toggle-switch.disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .toggle-switch.disabled input {
    cursor: not-allowed;
  }

  .toggle-switch.disabled .toggle-slider {
    cursor: not-allowed;
    background-color: #d1d5db;
  }
</style>
