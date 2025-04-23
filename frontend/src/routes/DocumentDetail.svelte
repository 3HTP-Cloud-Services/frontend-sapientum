<script>
  import { onMount } from 'svelte';
  import { push, location } from 'svelte-spa-router';
  import { link } from 'svelte-spa-router';
  import { isAuthenticated } from '../lib/auth.js';

  export let params = {};

  let document = null;
  let loading = true;
  let error = '';

  async function fetchDocument(id) {
    try {
      loading = true;
      const response = await fetch(`/api/documents/${id}`, {
        credentials: 'include'
      });

      if (response.ok) {
        document = await response.json();
      } else if (response.status === 401) {
        // User is not authenticated
        push('/login');
      } else if (response.status === 404) {
        error = 'Document not found';
      } else {
        console.error('Error fetching document:', response.status, response.statusText);

        // In static mode, just show mock document if the API fails
        if (window.location.pathname === '/' && !window.location.href.includes('localhost:5173')) {
          console.log('In static mode, using mock document');
          document = {
            "id": parseInt(id),
            "title": `Static Document ${id}`,
            "content": `This is static document ${id} content. It's used as a fallback when the API isn't available.`
          };
        } else {
          error = 'Failed to fetch document';
        }
      }
    } catch (err) {
      console.error('Document fetch error:', err);

      // In static mode, just show mock document if the API fails
      if (window.location.pathname === '/' && !window.location.href.includes('localhost:5173')) {
        console.log('In static mode, using mock document');
        document = {
          "id": parseInt(id),
          "title": `Static Document ${id}`,
          "content": `This is static document ${id} content. It's used as a fallback when the API isn't available.`
        };
      } else {
        error = 'Network error';
      }
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    if ($isAuthenticated && params.id) {
      fetchDocument(params.id);
    }
  });
</script>

<div>
  <div class="nav-bar">
    <a href="#/documents" use:link>← Back to Documents</a>
    <a href="#/console" use:link>Back to Console</a>
  </div>

  {#if loading}
    <p>Loading document...</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else if document}
    <div class="document_detail">
      <h1>{document.title}</h1>
      <div class="document-content">
        {document.content}
      </div>
    </div>
  {/if}
</div>

<style>
  .error {
    color: #ff6b6b;
  }

  .document_detail {
    background-color: #e0e0ff;
    color: #111;
    padding: 2rem;
    border-radius: 8px;
  }
  
  .nav-bar {
    display: flex;
    justify-content: space-between;
    margin-bottom: 1.5rem;
  }
  
  .nav-bar a {
    color: #4299e1;
    text-decoration: none;
  }

  .document-content {
    margin-top: 1rem;
    line-height: 1.6;
  }
</style>
