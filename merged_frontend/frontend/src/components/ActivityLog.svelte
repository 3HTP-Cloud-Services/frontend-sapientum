<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { i18nStore } from '../../../shared-components/utils/i18n.js';

  export let activeSectionStore;

  let activityLogs = [];
  let loading = false;
  let error = '';
  let successMessage = '';

  async function fetchActivityLogs() {
    try {
      loading = true;
      error = '';
      const response = await fetch('/api/activity-logs', {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        activityLogs = data.logs;
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
</style>
