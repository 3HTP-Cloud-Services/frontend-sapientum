<script>
  import { link } from 'svelte-spa-router';
  import { logout, isAuthenticated } from '../lib/auth.js';
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';

  // Active section state
  let activeSection = 'documents';

  // Document data
  let documents = [];
  let loading = true;
  let error = '';

  // Document detail data
  let selectedDocument = null;
  let loadingDocument = false;
  let documentError = '';

  // Permissions data
  let users = [];
  let loadingUsers = false;
  let usersError = '';
  let editingUser = null;
  let showUserModal = false;

  // Chat data
  let messages = [
    {
      id: 1,
      type: 'system',
      content: 'Bienvenido al Asistente de IA. ¿Cómo puedo ayudarte hoy?',
      timestamp: new Date(Date.now() - 60000)
    }
  ];
  let userInput = '';
  let chatContainer;
  let messagesContainer;

  // Sidebar state
  let sidebarCollapsed = false;
  let isMobile = false;

  // Check if device is mobile
  function checkMobile() {
    isMobile = window.innerWidth <= 768;
    // On mobile, start with sidebar in collapsed state
    if (isMobile && !sidebarCollapsed) {
      sidebarCollapsed = true;
    }
  }

  // Toggle sidebar visibility
  function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
  }

  // This function definition is moved down in the file

  // Handle logout
  async function handleLogout() {
    await logout();
    push('/login');
  }

  // Fetch documents for the documents section
  async function fetchDocuments() {
    try {
      loading = true;
      const response = await fetch('/api/documents', {
        credentials: 'include'
      });

      if (response.ok) {
        documents = await response.json();
      } else if (response.status === 401) {
        // User is not authenticated
        push('/login');
      } else {
        console.error('Error fetching documents:', response.status, response.statusText);
        error = 'Error al cargar documentos';
      }
    } catch (err) {
      console.error('Document fetch error:', err);
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  // Fetch a specific document by ID
  async function fetchDocument(id) {
    try {
      // Clear any previous document
      selectedDocument = null;
      loadingDocument = true;
      documentError = '';

      const response = await fetch(`/api/documents/${id}`, {
        credentials: 'include'
      });

      if (response.ok) {
        selectedDocument = await response.json();
      } else if (response.status === 401) {
        // User is not authenticated
        push('/login');
      } else if (response.status === 404) {
        documentError = 'Documento no encontrado';
      } else {
        console.error('Error fetching document:', response.status, response.statusText);
        documentError = 'Error al cargar el documento';
      }
    } catch (err) {
      console.error('Document detail fetch error:', err);
      documentError = 'Error de conexión';
    } finally {
      loadingDocument = false;
    }
  }

  // View document details
  function viewDocument(id) {
    fetchDocument(id);
    activeSection = 'document-detail';
  }

  // Back to documents list
  function backToDocuments() {
    selectedDocument = null;
    documentError = '';
    activeSection = 'documents';
  }

  // Function to scroll chat to bottom
  function scrollToBottom() {
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  // Function to send a chat message
  async function sendMessage() {
    if (!userInput.trim()) return;

    // Add user message
    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      content: userInput,
      timestamp: new Date()
    };

    messages = [...messages, userMessage];

    // Clear input and store the message for sending
    const messageToSend = userInput;
    userInput = '';

    // Scroll to bottom after rendering user message
    setTimeout(scrollToBottom, 0);

    try {
      // Call the backend API
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: messageToSend }),
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();

        // Add AI response
        messages = [...messages, {
          id: messages.length + 1,
          type: 'system',
          content: data.response,
          timestamp: new Date()
        }];

        // Scroll to bottom after rendering AI response
        setTimeout(scrollToBottom, 0);
      } else if (response.status === 401) {
        // User is not authenticated
        push('/login');
      } else {
        // Fall back to client-side response if API fails
        console.error('Error from chat API:', response.status);

        // Use fallback responses
        let fallbackResponse = "Estoy teniendo problemas para conectarme al servidor. Por favor, inténtalo más tarde.";

        messages = [...messages, {
          id: messages.length + 1,
          type: 'system',
          content: fallbackResponse,
          timestamp: new Date()
        }];

        setTimeout(scrollToBottom, 0);
      }
    } catch (error) {
      console.error('Network error when calling chat API:', error);

      // Handle network errors with fallback
      messages = [...messages, {
        id: messages.length + 1,
        type: 'system',
        content: "Estoy teniendo problemas para conectarme al servidor. Por favor, inténtalo más tarde.",
        timestamp: new Date()
      }];

      setTimeout(scrollToBottom, 0);
    }
  }

  // Handle key press for chat input
  function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  // Fetch users for permissions section
  async function fetchUsers() {
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
  function editUser(user) {
    editingUser = { ...user };
    showUserModal = true;
  }

  function addNewUser() {
    editingUser = {
      id: null,
      email: '',
      documentAccess: 'Lectura',
      chatAccess: false,
      isAdmin: false
    };
    showUserModal = true;
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

  async function deleteUser(userId) {
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

  function closeUserModal() {
    showUserModal = false;
    editingUser = null;
  }

  // Handle section change - load data as needed
  function switchSection(section) {
    activeSection = section;

    // Load section-specific data if needed
    if (section === 'permissions' && users.length === 0 && !loadingUsers) {
      fetchUsers();
    }
  }

  onMount(() => {
    if ($isAuthenticated) {
      fetchDocuments();
      // Pre-load permissions data
      fetchUsers();

      // Check if we should activate a specific section (e.g. from redirect)
      const savedSection = localStorage.getItem('activeConsoleSection');
      if (savedSection) {
        activeSection = savedSection;
        localStorage.removeItem('activeConsoleSection'); // Clear after use
      }
    }

    // Check if mobile on initial load
    checkMobile();

    // Add resize event listener
    window.addEventListener('resize', checkMobile);

    // Scroll chat to bottom on initial load
    setTimeout(scrollToBottom, 0);

    // Cleanup function
    return () => {
      window.removeEventListener('resize', checkMobile);
    };
  });
</script>

<div class="console">
  <header class="console-header">
    <h1>Consola de Administración Sapientum AI</h1>
    <button class="logout-button" on:click={handleLogout}>Cerrar Sesión</button>
  </header>

  <div class="console-container">
    <nav class="sidebar" class:collapsed={sidebarCollapsed} class:mobile={isMobile}>
      <div class="sidebar-toggle" on:click={toggleSidebar}>
        <span class="toggle-icon">{sidebarCollapsed ? '→' : '←'}</span>
      </div>
      <ul>
        <li class={activeSection === 'documents' ? 'active' : ''}>
          <button on:click={() => switchSection('documents')}>
            <span class="icon">📄</span>
            <span class="text">Documentos</span>
          </button>
        </li>
        <li class={activeSection === 'permissions' ? 'active' : ''}>
          <button on:click={() => switchSection('permissions')}>
            <span class="icon">🔒</span>
            <span class="text">Permisos</span>
          </button>
        </li>
        <li class={activeSection === 'chat' ? 'active' : ''}>
          <button on:click={() => switchSection('chat')}>
            <span class="icon">💬</span>
            <span class="text">Chat</span>
          </button>
        </li>
      </ul>
    </nav>

    <main class="content" class:expanded={sidebarCollapsed}>
      {#if activeSection === 'document-detail'}
        <div class="section-header">
          <h2>Detalles del Documento</h2>
          <button class="back-button" on:click={backToDocuments}>← Volver a Documentos</button>
        </div>
        <div class="document-detail-section">
          {#if loadingDocument}
            <p>Cargando documento...</p>
          {:else if documentError}
            <p class="error">{documentError}</p>
          {:else if selectedDocument}
            <div class="document-detail">
              <h1>{selectedDocument.title}</h1>
              <div class="document-content">
                {selectedDocument.content}
              </div>
            </div>
          {:else}
            <p>Selecciona un documento para ver detalles.</p>
          {/if}
        </div>
      {:else if activeSection === 'documents'}
        <div class="section-header">
          <h2>Documentos</h2>
        </div>
        <div class="documents-section">
          {#if loading}
            <p>Cargando documentos...</p>
          {:else if error}
            <p class="error">{error}</p>
          {:else if documents.length === 0}
            <p>No se encontraron documentos.</p>
          {:else}
            <div class="document-cards">
              {#each documents as doc}
                <div class="document-card">
                  <h3>{doc.title}</h3>
                  <p>{doc.content.substring(0, 100)}...</p>
                  <button class="view-document-button" on:click={() => viewDocument(doc.id)}>Ver Documento</button>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {:else if activeSection === 'permissions'}
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
      {:else if activeSection === 'chat'}
        <div class="section-header">
          <h2>Chat IA</h2>
          <div class="chat-buttons">
            <button on:click={() => {messages = [
              {
                id: 1,
                type: 'system',
                content: 'Bienvenido al Asistente de IA. ¿Cómo puedo ayudarte hoy?',
                timestamp: new Date()
              }
            ]}} class="clear-button">Limpiar Chat</button>
          </div>
        </div>
        <div class="chat-section">
          <div class="chat-container">
            <div class="chat-messages" bind:this={messagesContainer}>
              {#each messages as message (message.id)}
                <div class={`message ${message.type}`}>
                  <div class="message-content">{message.content}</div>
                  <div class="message-time">{message.timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                </div>
              {/each}
            </div>
            <div class="chat-input">
              <textarea
                placeholder="Escribe tu mensaje aquí y presiona Enter para enviar..."
                bind:value={userInput}
                on:keydown={handleKeydown}
              ></textarea>
              <button class="send-button" on:click={sendMessage} disabled={!userInput.trim()}>Enviar</button>
            </div>
          </div>
        </div>
      {/if}
    </main>
  </div>
</div>

<style>
  .error {
    color: #ff6b6b;
    padding: 1rem;
    background-color: #fee;
    border-radius: 4px;
    margin-bottom: 1rem;
  }

  .console {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    color: #333;
  }

  .console-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
    background-color: #4a5568;
    color: white;
  }

  .console-header h1 {
    margin: 0;
    font-size: 1.5rem;
  }

  .logout-button {
    background-color: #e53e3e;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
  }

  .console-container {
    display: flex;
    flex: 1;
    background-color: #f7fafc;
    position: relative;
    overflow-x: hidden; /* Prevent horizontal scrolling */
  }

  .sidebar {
    width: 250px;
    background-color: #2d3748;
    color: white;
    padding: 1rem 0;
    position: relative;
    transition: all 0.3s ease;
  }

  .sidebar.collapsed {
    width: 60px;
  }

  /* Mobile sidebar specific styles */
  .sidebar.mobile {
    position: absolute;
    height: 100%;
    z-index: 100;
  }

  .sidebar.mobile.collapsed {
    width: 60px; /* On mobile, collapsed should be narrow but visible */
    padding: 1rem 0;
    overflow: visible;
  }

  .sidebar-toggle {
    position: absolute;
    top: 10px;
    right: -15px;
    width: 30px;
    height: 30px;
    background-color: #4a5568;
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    box-shadow: 0 0 5px rgba(0, 0, 0, 0.2);
    z-index: 10;
    color: white;
  }

  .toggle-icon {
    font-size: 16px;
    font-weight: bold;
  }

  .sidebar ul {
    list-style-type: none;
    padding: 0;
    margin: 0;
    margin-top: 20px;
  }

  .sidebar li {
    padding: 0;
  }

  .sidebar li button {
    display: flex;
    align-items: center;
    width: 100%;
    text-align: left;
    padding: 0.75rem 1.5rem;
    background: none;
    border: none;
    color: #e2e8f0;
    cursor: pointer;
    font-size: 1rem;
    transition: background-color 0.2s;
    overflow: hidden;
    white-space: nowrap;
  }

  .sidebar li button .icon {
    margin-right: 12px;
    font-size: 1.2rem;
    min-width: 20px;
  }

  .sidebar.collapsed li button .text {
    opacity: 0;
    width: 0;
    display: none;
  }

  .sidebar.collapsed li button {
    padding: 0.75rem;
    justify-content: center;
  }

  .sidebar.collapsed li button .icon {
    margin-right: 0;
    font-size: 1.5rem;
  }

  .sidebar li.active button {
    background-color: #4a5568;
    color: white;
    font-weight: bold;
  }

  .sidebar li button:hover {
    background-color: #4a5568;
  }

  .content {
    flex: 1;
    padding: 2rem;
    overflow: auto;
    transition: all 0.3s ease;
  }

  .content.expanded {
    margin-left: 0; /* Don't use negative margin which causes horizontal scroll */
  }

  @media (max-width: 768px) {
    .content.expanded {
      margin-left: 0;
      padding-left: 70px; /* Add padding to avoid content being hidden under sidebar */
    }
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .section-header h2 {
    margin: 0;
    color: #2d3748;
  }

  .view-all {
    color: #4299e1;
    text-decoration: none;
  }

  .chat-buttons {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .clear-button {
    background-color: #a0aec0;
    color: white;
    border: none;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
  }

  /* Document detail view */
  .document-detail-section {
    margin-bottom: 2rem;
  }

  .document-detail {
    background-color: white;
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .document-detail h1 {
    margin-top: 0;
    color: #2d3748;
    font-size: 1.5rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 0.75rem;
  }

  .document-content {
    line-height: 1.6;
    color: #4a5568;
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

  /* Documents section */
  .document-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
  }

  .document-card {
    background-color: white;
    border-radius: 8px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .document-card h3 {
    margin-top: 0;
    color: #2d3748;
  }

  .document-card .view-document-button {
    display: inline-block;
    margin-top: 1rem;
    color: #4299e1;
    background: none;
    border: 1px solid #4299e1;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  .document-card .view-document-button:hover {
    background-color: #4299e1;
    color: white;
  }

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

  /* Chat section */
  .chat-container {
    display: flex;
    flex-direction: column;
    height: 500px;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .chat-section {
    margin-bottom: 2rem;
  }

  .chat-messages {
    flex: 1;
    padding: 1rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .message {
    max-width: 80%;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    position: relative;
    margin-bottom: 0.5rem;
  }

  .message.system {
    align-self: flex-start;
    background-color: #edf2f7;
    color: #2d3748;
  }

  .message.user {
    align-self: flex-end;
    background-color: #4299e1;
    color: white;
  }

  .message-time {
    font-size: 0.75rem;
    margin-top: 0.25rem;
    opacity: 0.7;
    text-align: right;
  }

  .chat-input {
    display: flex;
    padding: 1rem;
    background-color: #edf2f7;
    border-top: 1px solid #e2e8f0;
  }

  .chat-input textarea {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    resize: none;
    height: 40px;
    font-family: inherit;
  }

  .send-button {
    margin-left: 0.5rem;
    background-color: #4299e1;
    color: white;
    border: none;
    padding: 0 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 40px;
    text-decoration: none;
    min-width: 80px;
  }

  /* Mobile optimizations */
  @media (max-width: 768px) {
    .console-header {
      padding: 1rem;
    }

    .console-header h1 {
      font-size: 1.2rem;
    }

    .content {
      padding: 1rem;
    }
  }
</style>
