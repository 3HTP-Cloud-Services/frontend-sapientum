import { writable } from 'svelte/store';

export const isAuthenticated = writable(false);
export const userRole = writable(null);
export const userEmail = writable(null);
export const isEmbedded = writable(false);

export const checkAuth = async () => {
  try {
    const response = await fetch('/api/check-auth', {
      credentials: 'include'
    });
    
    if (response.ok) {
      const data = await response.json();
      isAuthenticated.set(data.authenticated);
      
      if (data.authenticated) {
        userRole.set(data.role);
        userEmail.set(data.email);
        isEmbedded.set(data.is_embedded || false);
      } else {
        userRole.set(null);
        userEmail.set(null);
        isEmbedded.set(false);
      }
      
      return data.authenticated;
    } else {
      isAuthenticated.set(false);
      userRole.set(null);
      userEmail.set(null);
      isEmbedded.set(false);
      return false;
    }
  } catch (error) {
    console.error('Auth check error:', error);
    isAuthenticated.set(false);
    userRole.set(null);
    userEmail.set(null);
    isEmbedded.set(false);
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
      userRole.set(data.role);
      userEmail.set(username);
      isEmbedded.set(data.is_embedded || false);
      return { 
        success: true, 
        role: data.role,
        is_embedded: data.is_embedded || false
      };
    } else {
      if (data.error === 'no_chat_access') {
        return { 
          success: false, 
          message: data.message || 'You do not have chat access',
          error: 'no_chat_access'
        };
      }
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
    userRole.set(null);
    userEmail.set(null);
    isEmbedded.set(false);
  } catch (error) {
    console.error('Logout error:', error);
  }
};

export const checkChatAccess = async () => {
  try {
    const response = await fetch('/api/check-chat-access', {
      credentials: 'include'
    });
    
    if (response.ok) {
      const data = await response.json();
      
      // Update embedded status from the response
      if (data.is_embedded !== undefined) {
        isEmbedded.set(data.is_embedded);
      }
      
      return data.has_access === true;
    }
    return false;
  } catch (error) {
    console.error('Error checking chat access:', error);
    return false;
  }
};

// Function to check if the app is in chat-only mode
export const isChatOnlyMode = () => {
  const urlParams = new URLSearchParams(window.location.hash.split('?')[1] || '');
  return urlParams.get('chatOnly') === 'true';
};