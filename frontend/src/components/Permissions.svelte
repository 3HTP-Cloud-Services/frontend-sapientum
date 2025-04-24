<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';

  // Permissions data
  export let users = [];
  export let loadingUsers = false;
  export let usersError = '';
  export let editingUser = null;
  export let showUserModal = false;
  export let hidden = false;

  // Fetch users for permissions section
  export async function fetchUsers() {
    try {
      loadingUsers = true;
      usersError = '';
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
        usersError = 'Error al cargar usuarios';
      }
    } catch (err) {
      console.error('Users fetch error:', err);
      usersError = 'Error de conexión';
    } finally {
      loadingUsers = false;
    }
  }

  // User management functions
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
          usersError = 'Error al actualizar usuario';
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
          usersError = 'Error al crear usuario';
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
        // Remove from local data
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

  export function closeUserModal() {
    showUserModal = false;
    editingUser = null;
  }

  // Initialize on component mount
  onMount(() => {
    if (!hidden && users.length === 0 && !loadingUsers) {
      fetchUsers();
    }
  });

  // Refresh data when becoming visible - always reload when component becomes visible
  $: if (!hidden) {
    console.log("Permissions component became visible");
    fetchUsers();
  }
</script>

<div style="display: {hidden ? 'none' : 'block'}">
<div class="section-header">
  <h2>Permisos</h2>
</div>
<div class="permissions-section">
  <div class="permissions-table">
    {#if loadingUsers}
      <p>Cargando usuarios...</p>
    {:else if usersError}
      <p class="error">{usersError}</p>
    {:else if users.length === 0}
      <p>No se encontraron usuarios.</p>
    {:else}
      <table>
        <thead>
        <tr>
          <th>Usuario</th>
          <th>Acceso a Documentos</th>
          <th>Acceso a Chat</th>
          <th>Derechos de Admin</th>
          <th>Acciones</th>
        </tr>
        </thead>
        <tbody>
        {#each users as user}
          <tr>
            <td>{user.email}</td>
            <td>{user.documentAccess}</td>
            <td>{user.chatAccess ? 'Habilitado' : 'Deshabilitado'}</td>
            <td>{user.isAdmin ? 'Sí' : 'No'}</td>
            <td>
              <button class="edit-button" on:click={() => editUser(user)}>Editar</button>
              <button class="delete-button" on:click={() => deleteUser(user.id)}>Eliminar</button>
            </td>
          </tr>
        {/each}
        </tbody>
      </table>
    {/if}
  </div>
  <button class="add-user-button" on:click={addNewUser}>Agregar Nuevo Usuario</button>
</div>

{#if showUserModal}
  <div class="modal-backdrop">
    <div class="modal">
      <h2>{editingUser.id ? 'Editar Usuario' : 'Agregar Nuevo Usuario'}</h2>

      <div class="form-group">
        <label for="email">Email:</label>
        <input type="email" id="email" bind:value={editingUser.email} required />
      </div>

      <div class="form-group">
        <label for="documentAccess">Acceso a Documentos:</label>
        <select id="documentAccess" bind:value={editingUser.documentAccess}>
          <option value="Lectura">Lectura</option>
          <option value="Lectura/Escritura">Lectura/Escritura</option>
          <option value="Ninguno">Ninguno</option>
        </select>
      </div>

      <div class="form-group checkbox">
        <label>
          <input type="checkbox" bind:checked={editingUser.chatAccess} />
          Habilitar Acceso a Chat
        </label>
      </div>

      <div class="form-group checkbox">
        <label>
          <input type="checkbox" bind:checked={editingUser.isAdmin} />
          Derechos de Administrador
        </label>
      </div>

      <div class="modal-actions">
        <button class="cancel-button" on:click={closeUserModal}>Cancelar</button>
        <button class="save-button" on:click={saveUser}>Guardar</button>
      </div>
    </div>
  </div>

{/if}
</div>
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

  .add-user-button {
    background-color: #48bb78;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
    text-decoration: none;
    display: inline-block;
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
