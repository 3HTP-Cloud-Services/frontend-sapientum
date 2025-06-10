<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { i18nStore } from '../../../shared-components/utils/i18n.js';
  import { httpCall } from '../../../shared-components/utils/httpCall.js';

  export let activeSectionStore;

  let activityLogs = [];
  let loading = false;
  let error = '';
  let successMessage = '';
  
  // Pagination state
  let currentPage = 1;
  let perPage = 20;
  let totalPages = 1;
  let totalItems = 0;
  let hasNext = false;
  let hasPrev = false;

  async function fetchActivityLogs(page = currentPage) {
    try {
      loading = true;
      error = '';
      const response = await httpCall(`/api/activity-logs?page=${page}&per_page=${perPage}`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        activityLogs = data.logs;
        
        // Update pagination state
        if (data.pagination) {
          currentPage = data.pagination.page;
          totalPages = data.pagination.pages;
          totalItems = data.pagination.total;
          hasNext = data.pagination.has_next;
          hasPrev = data.pagination.has_prev;
        }
        
        console.log('Activity logs loaded:', activityLogs);
      } else if (response.status === 401) {
        // User is not authenticated
        push('/login');
      } else if (response.status === 403) {
        // User does not have admin permissions
        error = $i18nStore.t('access_denied_admin_required') || 'Access denied. Admin permissions required.';

        const errorData = await response.json().catch(() => ({}));
        if (errorData && errorData.error) {
          error = errorData.error;
        }
      } else {
        console.error('Error fetching activity logs:', response.status, response.statusText);
        error = 'Error loading activity logs';
      }
    } catch (err) {
      console.error('Activity logs fetch error:', err);
      error = 'Connection error';
    } finally {
      loading = false;
    }
  }

  // Format date for display
  function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString();
  }

  // Get event type display name
  function getEventTypeDisplay(eventType) {
    const eventTypes = {
      'permission_violation': 'Permission Violation',
      'user_login': 'User Login',
      'user_creation': 'User Creation',
      'user_deletion': 'User Deletion',
      'user_edition': 'User Edition',
      'user_permission': 'User Permission Change',
      'catalog_creation': 'Catalog Creation',
      'catalog_edition': 'Catalog Edition',
      'catalog_deletion': 'Catalog Deletion',
      'file_upload': 'File Upload',
      'file_deletion': 'File Deletion',
      'file_new_version': 'New File Version',
      'chat_interaction': 'Chat Interaction'
    };

    return eventTypes[eventType] || eventType;
  }

  // Pagination navigation functions
  function goToPage(page) {
    if (page >= 1 && page <= totalPages && page !== currentPage) {
      fetchActivityLogs(page);
    }
  }

  function nextPage() {
    if (hasNext) {
      goToPage(currentPage + 1);
    }
  }

  function prevPage() {
    if (hasPrev) {
      goToPage(currentPage - 1);
    }
  }

  $: if ($activeSectionStore === 'activity-log') {
    console.log("Activity Log section is now active");
    fetchActivityLogs();
  }
</script>

<div class="section-header">
  <h2>{$i18nStore.t('activity_log') || 'Activity Log'}</h2>
  {#if successMessage}
    <div class="success-message" transition:fade={{ duration: 150 }}>
      {successMessage}
    </div>
  {/if}
</div>

<div class="activity-log-section">
  {#if loading}
    <p transition:fade={{ duration: 150 }}>{$i18nStore.t('loading') || 'Loading...'}</p>
  {:else if error}
    <p class="error" transition:fade={{ duration: 150 }}>{error}</p>
  {:else if activityLogs.length === 0 && !loading}
    <p transition:fade={{ duration: 150 }}>{$i18nStore.t('no_activity_logs') || 'No activity logs found'}</p>
  {:else}
    <div transition:fade={{ duration: 150 }}>
      <table>
        <thead>
          <tr>
            <th>{$i18nStore.t('date') || 'Date'}</th>
            <th>{$i18nStore.t('user') || 'User'}</th>
            <th>{$i18nStore.t('event_type') || 'Event Type'}</th>
            <th>{$i18nStore.t('activity') || 'Activity'}</th>
            <th>{$i18nStore.t('message') || 'Message'}</th>
          </tr>
        </thead>
        <tbody>
          {#each activityLogs as log}
            <tr>
              <td>{formatDate(log.created_at)}</td>
              <td>{log.user_email || log.user_id}</td>
              <td>{getEventTypeDisplay(log.event)}</td>
              <td>{log.activity}</td>
              <td>{log.message}</td>
            </tr>
          {/each}
        </tbody>
      </table>
      
      <!-- Pagination Controls -->
      {#if totalPages > 1}
        <div class="pagination-controls" transition:fade={{ duration: 150 }}>
          <div class="pagination-info">
            <span>{$i18nStore.t('showing') || 'Showing'} {((currentPage - 1) * perPage) + 1}-{Math.min(currentPage * perPage, totalItems)} {$i18nStore.t('of') || 'of'} {totalItems} {$i18nStore.t('items') || 'items'}</span>
          </div>
          
          <div class="pagination-buttons">
            <button 
              class="pagination-btn" 
              disabled={!hasPrev}
              on:click={prevPage}
              title="{$i18nStore.t('previous_page') || 'Previous page'}"
            >
              ← {$i18nStore.t('previous') || 'Previous'}
            </button>
            
            <div class="page-numbers">
              {#each Array(totalPages).fill(0) as _, i}
                {#if i + 1 === 1 || i + 1 === totalPages || (i + 1 >= currentPage - 2 && i + 1 <= currentPage + 2)}
                  <button 
                    class="page-btn" 
                    class:active={i + 1 === currentPage}
                    on:click={() => goToPage(i + 1)}
                  >
                    {i + 1}
                  </button>
                {:else if i + 1 === currentPage - 3 || i + 1 === currentPage + 3}
                  <span class="ellipsis">...</span>
                {/if}
              {/each}
            </div>
            
            <button 
              class="pagination-btn" 
              disabled={!hasNext}
              on:click={nextPage}
              title="{$i18nStore.t('next_page') || 'Next page'}"
            >
              {$i18nStore.t('next') || 'Next'} →
            </button>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  /* Activity Log section */
  .activity-log-section {
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

  .section-header {
    display: flex;
    align-items: center;
    margin-bottom: 1.5rem;
    min-height: 2.5rem;
  }

  /* Pagination styles */
  .pagination-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1.5rem;
    padding: 1rem 0;
    border-top: 1px solid #e2e8f0;
  }

  .pagination-info {
    color: #718096;
    font-size: 0.875rem;
  }

  .pagination-buttons {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .pagination-btn {
    padding: 0.5rem 1rem;
    border: 1px solid #e2e8f0;
    background-color: white;
    color: #4a5568;
    border-radius: 0.375rem;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  .pagination-btn:hover:not(:disabled) {
    background-color: #f7fafc;
    border-color: #cbd5e0;
  }

  .pagination-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .page-numbers {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .page-btn {
    padding: 0.5rem 0.75rem;
    border: 1px solid #e2e8f0;
    background-color: white;
    color: #4a5568;
    border-radius: 0.375rem;
    cursor: pointer;
    font-size: 0.875rem;
    min-width: 2.5rem;
    transition: all 0.2s;
  }

  .page-btn:hover {
    background-color: #f7fafc;
    border-color: #cbd5e0;
  }

  .page-btn.active {
    background-color: #3182ce;
    border-color: #3182ce;
    color: white;
  }

  .ellipsis {
    padding: 0.5rem 0.25rem;
    color: #a0aec0;
    font-size: 0.875rem;
  }
</style>
