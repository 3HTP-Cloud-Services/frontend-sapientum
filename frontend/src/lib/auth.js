import { writable } from 'svelte/store';

export const isAuthenticated = writable(false);

export const checkAuth = async () => {
  try {
    const response = await fetch('/api/check-auth', {
      credentials: 'include'
    });
    
    if (response.ok) {
      const data = await response.json();
      isAuthenticated.set(data.authenticated);
      return data.authenticated;
    } else {
      isAuthenticated.set(false);
      return false;
    }
  } catch (error) {
    console.error('Auth check error:', error);
    isAuthenticated.set(false);
    return false;
  }
};

export const login = async (username, password) => {
  try {
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, password }),
      credentials: 'include'
    });
    
    const data = await response.json();
    
    if (response.ok && data.success) {
      isAuthenticated.set(true);
      return { success: true };
    } else {
      return { success: false, message: data.message || 'Login failed' };
    }
  } catch (error) {
    console.error('Login error:', error);
    return { success: false, message: 'Network error' };
  }
};

export const logout = async () => {
  try {
    await fetch('/api/logout', {
      method: 'POST',
      credentials: 'include'
    });
    isAuthenticated.set(false);
  } catch (error) {
    console.error('Logout error:', error);
  }
};
