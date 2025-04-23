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

  // Chat data
  let messages = [
    {
      id: 1,
      type: 'system',
      content: 'Welcome to AI Assistant. How can I help you today?',
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

  // Function to switch between sections
  function switchSection(section) {
    activeSection = section;
  }

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

        // In static mode, just show some documents if the API is not available
        if (window.isStaticMode) {
          console.log('In static mode, using mock documents');
          documents = [
            {"id": 1, "title": "Document 1", "content": "This is document 1 content."},
            {"id": 2, "title": "Document 2", "content": "This is document 2 content."},
            {"id": 3, "title": "Document 3", "content": "This is document 3 content."}
          ];
        } else {
          error = 'Failed to fetch documents';
        }
      }
    } catch (err) {
      console.error('Document fetch error:', err);

      // In static mode, just show some documents if the API fails
      if (window.isStaticMode) {
        console.log('In static mode, using mock documents');
        documents = [
          {"id": 1, "title": "Document 1", "content": "This is document 1 content."},
          {"id": 2, "title": "Document 2", "content": "This is document 2 content."},
          {"id": 3, "title": "Document 3", "content": "This is document 3 content."}
        ];
      } else {
        error = 'Network error';
      }
    } finally {
      loading = false;
    }
  }

  // Function to scroll chat to bottom
  function scrollToBottom() {
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  // Function to send a chat message
  function sendMessage() {
    if (!userInput.trim()) return;

    // Add user message
    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      content: userInput,
      timestamp: new Date()
    };
    
    messages = [...messages, userMessage];
    
    // Clear input
    userInput = '';
    
    // Scroll to bottom after rendering user message
    setTimeout(scrollToBottom, 0);
    
    // Simulate AI response after a delay
    setTimeout(() => {
      const aiResponse = generateAIResponse(userMessage.content);
      messages = [...messages, {
        id: messages.length + 1,
        type: 'system',
        content: aiResponse,
        timestamp: new Date()
      }];
      
      // Scroll to bottom after rendering AI response
      setTimeout(scrollToBottom, 0);
    }, 1000);
  }

  // Function to generate AI response
  function generateAIResponse(userQuery) {
    // Mock AI response based on user query
    const responses = {
      'hello': 'Hello! How can I assist you today?',
      'help': 'I can help you with document summaries, answer questions about the system, or provide guidance on AI competency evaluation.',
      'document': 'Which document would you like me to summarize or provide information about?',
      'summarize': 'I can summarize documents for you. Please specify which document you would like me to summarize.',
      'document 1': 'Document 1 contains information about AI competency evaluation procedures. It outlines metrics for measuring performance including accuracy, response time, and knowledge breadth.',
      'document 2': 'Document 2 describes implementation strategies for AI systems in various organizational contexts, including best practices for deployment and integration.',
      'document 3': 'Document 3 provides case studies of successful AI implementations with detailed analysis of outcomes and lessons learned.',
      'permissions': 'User permissions are managed by administrators. There are different access levels for documents and chat functionality.',
    };
    
    // Check if query contains any keywords
    const lowerQuery = userQuery.toLowerCase();
    for (const [keyword, response] of Object.entries(responses)) {
      if (lowerQuery.includes(keyword)) {
        return response;
      }
    }
    
    // Default response
    return "I'm not sure I understand your question. Could you please rephrase or provide more details?";
  }

  // Handle key press for chat input
  function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  onMount(() => {
    if ($isAuthenticated) {
      fetchDocuments();
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
    <h1>AI Competency Console</h1>
    <button class="logout-button" on:click={handleLogout}>Logout</button>
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
            <span class="text">Documents</span>
          </button>
        </li>
        <li class={activeSection === 'permissions' ? 'active' : ''}>
          <button on:click={() => switchSection('permissions')}>
            <span class="icon">🔒</span>
            <span class="text">Permissions</span>
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
      {#if activeSection === 'documents'}
        <div class="section-header">
          <h2>Documents</h2>
          <a href="#/documents" use:link class="view-all">View All Documents</a>
        </div>
        <div class="documents-section">
          {#if loading}
            <p>Loading documents...</p>
          {:else if error}
            <p class="error">{error}</p>
          {:else if documents.length === 0}
            <p>No documents found.</p>
          {:else}
            <div class="document-cards">
              {#each documents as doc}
                <div class="document-card">
                  <h3>{doc.title}</h3>
                  <p>{doc.content.substring(0, 100)}...</p>
                  <a href="#/documents/{doc.id}" use:link>View Document</a>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {:else if activeSection === 'permissions'}
        <div class="section-header">
          <h2>Permissions</h2>
          <a href="#/permissions" use:link class="view-all">Manage All Permissions</a>
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
              <tr>
                <td>user@example.com</td>
                <td>Read</td>
                <td>Enabled</td>
                <td>No</td>
                <td><a href="#/permissions" use:link class="edit-link">Edit</a></td>
              </tr>
              <tr>
                <td>admin@example.com</td>
                <td>Read/Write</td>
                <td>Enabled</td>
                <td>Yes</td>
                <td><a href="#/permissions" use:link class="edit-link">Edit</a></td>
              </tr>
              <tr>
                <td>guest@example.com</td>
                <td>Read</td>
                <td>Disabled</td>
                <td>No</td>
                <td><a href="#/permissions" use:link class="edit-link">Edit</a></td>
              </tr>
              </tbody>
            </table>
          </div>
          <a href="#/permissions" use:link class="add-user-button">Manage Users</a>
        </div>
      {:else if activeSection === 'chat'}
        <div class="section-header">
          <h2>AI Chat</h2>
          <a href="#/chat" use:link class="view-all">Open Full Chat</a>
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
                placeholder="Type your message here..." 
                bind:value={userInput}
                on:keydown={handleKeydown}
              ></textarea>
              <button class="send-button" on:click={sendMessage}>Send</button>
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

  .document-card a {
    display: inline-block;
    margin-top: 1rem;
    color: #4299e1;
    text-decoration: none;
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
