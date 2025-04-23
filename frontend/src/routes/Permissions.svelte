<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { link } from 'svelte-spa-router';
  import { isAuthenticated } from '../lib/auth.js';

  let users = [];
  let loading = true;
  let error = '';
  let editingUser = null;
  let showModal = false;
  
  // Fetch users from the backend
  async function fetchUsers() {
    try {
      loading = true;
      error = '';
      
      const response = await fetch('/api/users', {
        credentials: 'include'
      });
      
      if (response.ok) {
        users = await response.json();
      } else if (response.status === 401) {
        // User is not authenticated
        push('/login');
      } else {
        console.error('Error fetching users:', response.status, response.statusText);
        error = 'Failed to fetch user data';
      }
    } catch (err) {
      console.error('User fetch error:', err);
      error = 'Network error';
    } finally {
      loading = false;
    }
  }

  function editUser(user) {
    editingUser = { ...user };
    showModal = true;
  }

  function addNewUser() {
    editingUser = {
      id: users.length + 1,
      email: '',
      documentAccess: 'Read',
      chatAccess: false,
      isAdmin: false
    };
    showModal = true;
  }

  async function saveUser() {
    try {
      if (editingUser.id) {
        // Update existing user
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
          // Update local user data
          const index = users.findIndex(u => u.id === updatedUser.id);
          if (index !== -1) {
            users[index] = updatedUser;
            users = [...users]; // Trigger reactivity
          }
        } else {
          console.error('Error updating user:', response.status);
          error = 'Failed to update user';
        }
      } else {
        // Add new user
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
          error = 'Failed to create user';
        }
      }
      
      closeModal();
    } catch (err) {
      console.error('Error saving user:', err);
      error = 'Network error while saving user';
    }
  }
  
  async function deleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user?')) {
      return;
    }
    
    try {
      const response = await fetch(`/api/users/${userId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        // Remove from local data
        users = users.filter(u => u.id !== userId);
      } else {
        console.error('Error deleting user:', response.status);
        error = 'Failed to delete user';
      }
    } catch (err) {
      console.error('Error deleting user:', err);
      error = 'Network error while deleting user';
    }
  }

  function closeModal() {
    showModal = false;
    editingUser = null;
  }
  
  onMount(() => {
    if ($isAuthenticated) {
      fetchUsers();
    }
  });
</script>

<div>
  <div class="header">
    <h1>User Permissions</h1>
    <a href="#/console" use:link class="back-link">← Back to Console</a>
  </div>

  <div class="permissions-section">
    {#if loading}
      <p>Loading users...</p>
    {:else if error}
      <p class="error">{error}</p>
    {:else if users.length === 0}
      <p>No users found.</p>
    {:else}
      <div class="permissions-table">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Document Access</th>
              <th>Chat Access</th>
              <th>Admin Rights</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each users as user}
              <tr>
                <td>{user.email}</td>
                <td>{user.documentAccess}</td>
                <td>{user.chatAccess ? 'Enabled' : 'Disabled'}</td>
                <td>{user.isAdmin ? 'Yes' : 'No'}</td>
                <td>
                  <button class="edit-button" on:click={() => editUser(user)}>Edit</button>
                  <button class="delete-button" on:click={() => deleteUser(user.id)}>Delete</button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <button class="add-user-button" on:click={addNewUser}>Add New User</button>
    {/if}
  </div>

  {#if showModal}
    <div class="modal-backdrop">
      <div class="modal">
        <h2>{editingUser.id ? 'Edit User' : 'Add New User'}</h2>
        
        <div class="form-group">
          <label for="email">Email:</label>
          <input type="email" id="email" bind:value={editingUser.email} required />
        </div>
        
        <div class="form-group">
          <label for="documentAccess">Document Access:</label>
          <select id="documentAccess" bind:value={editingUser.documentAccess}>
            <option value="Read">Read</option>
            <option value="Read/Write">Read/Write</option>
            <option value="None">None</option>
          </select>
        </div>
        
        <div class="form-group checkbox">
          <label>
            <input type="checkbox" bind:checked={editingUser.chatAccess} />
            Enable Chat Access
          </label>
        </div>
        
        <div class="form-group checkbox">
          <label>
            <input type="checkbox" bind:checked={editingUser.isAdmin} />
            Admin Rights
          </label>
        </div>
        
        <div class="modal-actions">
          <button class="cancel-button" on:click={closeModal}>Cancel</button>
          <button class="save-button" on:click={saveUser}>Save</button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }

  h1 {
    margin: 0;
    color: #2d3748;
  }

  .back-link {
    color: #4299e1;
    text-decoration: none;
  }

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

  .edit-button {
    background-color: #4299e1;
    color: white;
    border: none;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    cursor: pointer;
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

  .add-user-button {
    background-color: #48bb78;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
  }

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
  
  .error {
    color: #ff6b6b;
    padding: 1rem;
    background-color: #fee;
    border-radius: 4px;
    margin-bottom: 1rem;
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
