<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { link } from 'svelte-spa-router';
  import { logout, isAuthenticated } from '../lib/auth.js';

  let documents = [];
  let loading = true;
  let error = '';

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
        if (window.location.pathname === '/' && !window.location.href.includes('localhost:5173')) {
          console.log('In static mode, using mock documents');
          documents = [
            {"id": 1, "title": "Static Document 1", "content": "This is static document 1 content."},
            {"id": 2, "title": "Static Document 2", "content": "This is static document 2 content."},
            {"id": 3, "title": "Static Document 3", "content": "This is static document 3 content."}
          ];
        } else {
          error = 'Failed to fetch documents';
        }
      }
    } catch (err) {
      console.error('Document fetch error:', err);

      // In static mode, just show some documents if the API fails
      if (window.location.pathname === '/' && !window.location.href.includes('localhost:5173')) {
        console.log('In static mode, using mock documents');
        documents = [
          {"id": 1, "title": "Static Document 1", "content": "This is static document 1 content."},
          {"id": 2, "title": "Static Document 2", "content": "This is static document 2 content."},
          {"id": 3, "title": "Static Document 3", "content": "This is static document 3 content."}
        ];
      } else {
        error = 'Network error';
      }
    } finally {
      loading = false;
    }
  }

  async function handleLogout() {
    await logout();
    push('/login');
  }

  onMount(() => {
    if ($isAuthenticated) {
      fetchDocuments();
    }
  });
</script>

<div>
  <div class="nav-bar">
    <h1>Documents</h1>
    <div class="nav-buttons">
      <a href="#/console" use:link class="back-link">Back to Console</a>
      <button class="logout_button" on:click={handleLogout}>Logout</button>
    </div>
  </div>

  {#if loading}
    <p>Loading documents...</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else if documents.length === 0}
    <p>No documents found.</p>
  {:else}
    <ul class="document-list">
      {#each documents as doc}
        <li class="document_item">
          <!-- Use relative paths to avoid double # issue -->
          <a href="#/documents/{doc.id}" use:link>{doc.title}</a>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .error {
    color: #ff6b6b;
  }
  .document_item {
    padding: 1rem;
    margin-bottom: 0.5rem;
    background-color: #d0d0ff;
    color: #111111;
    border-radius: 4px;
    cursor: pointer;
  }
  
  .nav-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }
  
  .nav-buttons {
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  
  .back-link {
    color: #4299e1;
    text-decoration: none;
  }

</style>
