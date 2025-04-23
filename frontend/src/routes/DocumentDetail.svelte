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
        error = 'Documento no encontrado';
      } else {
        console.error('Error fetching document:', response.status, response.statusText);
        error = 'Error al cargar el documento';
      }
    } catch (err) {
      console.error('Document fetch error:', err);
      error = 'Error de conexión';
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    // Redirect to the Console component with document view
    push('/console');
  });
</script>

<div>
  <div class="nav-bar">
    <a href="#/documents" use:link>← Volver a Documentos</a>
    <a href="#/console" use:link>Volver a la Consola</a>
  </div>

  {#if loading}
    <p>Cargando documento...</p>
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
