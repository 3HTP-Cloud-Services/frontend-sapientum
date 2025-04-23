<script>
  import { push, location } from 'svelte-spa-router';
  import { login, isAuthenticated } from '../lib/auth.js';

  let username = '';
  let password = '';
  let error = '';

  async function handleSubmit() {
    error = '';
    const result = await login(username, password);

    if (result.success) {
      push('/');
    } else {
      error = result.message || 'Login failed';
    }
  }

  // Redirect to documents if already authenticated
  $: {
    if ($isAuthenticated) {
      push('/');
    }
  }
</script>

<div class="login-container">
  <h1>Iniciar Sesión</h1>

  <form on:submit|preventDefault={handleSubmit}>
    {#if error}
      <div class="error">{error}</div>
    {/if}

    <div class="form-group">
      <label for="username">Usuario</label>
      <input
        type="text"
        id="username"
        bind:value={username}
        required
      />
    </div>

    <div class="form-group">
      <label for="password">Contraseña</label>
      <input
        type="password"
        id="password"
        bind:value={password}
        required
      />
    </div>

    <button class="login_button" type="submit">Iniciar Sesión</button>
  </form>
</div>

<style>
  .login-container {
    max-width: 400px;
    margin: 0 auto;
    padding: 2rem;
    background-color: #f0f0ff;
    color: #111111;
    border-radius: 8px;
  }

  .error {
    color: #ff6b6b;
    margin-bottom: 1rem;
    padding: 0.5rem;
    background-color: rgba(255, 107, 107, 0.1);
    border-radius: 4px;
  }
</style>
