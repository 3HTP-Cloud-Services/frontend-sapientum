<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { link } from 'svelte-spa-router';
  import { isAuthenticated } from '../lib/auth.js';

  let users = [
    {
      id: 1,
      email: 'user@example.com',
      documentAccess: 'Read',
      chatAccess: true,
      isAdmin: false
    },
    {
      id: 2,
      email: 'admin@example.com',
      documentAccess: 'Read/Write',
      chatAccess: true,
      isAdmin: true
    },
    {
      id: 3,
      email: 'guest@example.com',
      documentAccess: 'Read',
      chatAccess: false,
      isAdmin: false
    }
  ];

  let editingUser = null;
  let showModal = false;

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

  function saveUser() {
    if (editingUser.id) {
      // Update existing user
      const index = users.findIndex(u => u.id === editingUser.id);
      if (index !== -1) {
        users[index] = editingUser;
        users = [...users];
      }
    } else {
      // Add new user
      users = [...users, editingUser];
    }
    
    closeModal();
  }

  function closeModal() {
    showModal = false;
    editingUser = null;
  }
</script>

<div>
  <div class="header">
    <h1>User Permissions</h1>
    <a href="#/console" use:link class="back-link">← Back to Console</a>
  </div>

  <div class="permissions-section">
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
              <td><button class="edit-button" on:click={() => editUser(user)}>Edit</button></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <button class="add-user-button" on:click={addNewUser}>Add New User</button>
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
