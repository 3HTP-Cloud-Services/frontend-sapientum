import { writable } from 'svelte/store';
import { httpCall } from './httpCall.js';

export const isAuthenticated = writable(false);
export const userRole = writable(null);
export const userEmail = writable(null);
export const isEmbedded = writable(false);
export const authToken = writable(null);
export const refreshToken = writable(null);
export const accessToken = writable(null);

// Token management functions
export const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem('authToken', token);
    authToken.set(token);
  } else {
    localStorage.removeItem('authToken');
    authToken.set(null);
  }
};

export const setRefreshToken = (token) => {
  if (token) {
    localStorage.setItem('refreshToken', token);
    refreshToken.set(token);
  } else {
    localStorage.removeItem('refreshToken');
    refreshToken.set(null);
  }
};

export const setAccessToken = (token) => {
  if (token) {
    localStorage.setItem('accessToken', token);
    accessToken.set(token);
  } else {
    localStorage.removeItem('accessToken');
    accessToken.set(null);
  }
};

export const getAuthToken = () => {
  return localStorage.getItem('authToken');
};

export const getRefreshToken = () => {
  return localStorage.getItem('refreshToken');
};

export const getAccessToken = () => {
  return localStorage.getItem('accessToken');
};

export const clearAuthToken = () => {
  localStorage.removeItem('authToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('accessToken');
  authToken.set(null);
  refreshToken.set(null);
  accessToken.set(null);
};

// Initialize auth tokens from localStorage on app start
export const initAuth = () => {
  const token = getAuthToken();
  const refresh = getRefreshToken();
  const access = getAccessToken();
  
  if (token) {
    authToken.set(token);
  }
  if (refresh) {
    refreshToken.set(refresh);
  }
  if (access) {
    accessToken.set(access);
  }
  
  // Load saved language preference
  try {
    const savedLanguage = localStorage.getItem('selectedLanguage');
    if (savedLanguage && (savedLanguage === 'en' || savedLanguage === 'es' || savedLanguage === 'pt')) {
      // Import and use setLocale from i18n
      import('./i18n.js').then(({ setLocale, currentLocale }) => {
        currentLocale.set(savedLanguage);
      });
    }
  } catch (error) {
    console.error('Error loading saved language:', error);
  }
};

export const checkAuth = async () => {
  try {
    const token = getAuthToken();
    if (!token) {
      isAuthenticated.set(false);
      userRole.set(null);
      userEmail.set(null);
      isEmbedded.set(false);
      return false;
    }

    const response = await httpCall('/api/check-auth', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    console.log('auth.js checking with JWT token');
    if (response.ok) {
      const data = await response.json();
      isAuthenticated.set(data.authenticated);

      if (data.authenticated) {
        console.log('auth.js', 'if', data.authenticated, data.role, data);
        userRole.set(data.role);
        userEmail.set(data.email);
        isEmbedded.set(data.is_embedded || false);
      } else {
        console.log('auth.js', 'else');
        clearAuthToken();
        userRole.set(null);
        userEmail.set(null);
        isEmbedded.set(false);
      }

      return data.authenticated;
    } else {
      console.log('auth.js', 'response not ok', response.ok, response.status);
      clearAuthToken();
      isAuthenticated.set(false);
      userRole.set(null);
      userEmail.set(null);
      isEmbedded.set(false);
      return false;
    }
  } catch (error) {
    console.error('auth.js', 'Auth check error:', error);
    clearAuthToken();
    isAuthenticated.set(false);
    userRole.set(null);
    userEmail.set(null);
    isEmbedded.set(false);
    return false;
  }
};

export const login = async (username, password) => {
  try {
    const response = await httpCall('/api/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, password })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      // Store all tokens
      if (data.token) {
        setAuthToken(data.token);
      }
      if (data.cognito?.refreshToken) {
        setRefreshToken(data.cognito.refreshToken);
      }
      if (data.cognito?.accessToken) {
        setAccessToken(data.cognito.accessToken);
      }
      
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
      // Handle NEW_PASSWORD_REQUIRED challenge
      if (data.error === 'new_password_required') {
        return {
          success: false,
          challenge: 'new_password_required',
          session: data.session,
          username: username,
          message: data.message || 'New password required',
          error: 'new_password_required'
        };
      }
      
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

export const setNewPassword = async (username, newPassword, session) => {
  try {
    const response = await httpCall('/api/set-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        username, 
        newPassword, 
        session 
      })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      // Store all tokens
      if (data.token) {
        setAuthToken(data.token);
      }
      if (data.cognito?.refreshToken) {
        setRefreshToken(data.cognito.refreshToken);
      }
      if (data.cognito?.accessToken) {
        setAccessToken(data.cognito.accessToken);
      }
      
      isAuthenticated.set(true);
      userRole.set(data.role);
      userEmail.set(username);
      isEmbedded.set(data.is_embedded || false);
      return {
        success: true,
        role: data.role,
        is_embedded: data.is_embedded || false,
        message: data.message || 'Password updated successfully'
      };
    } else {
      return { 
        success: false, 
        message: data.message || 'Failed to update password' 
      };
    }
  } catch (error) {
    console.error('Set password error:', error);
    return { success: false, message: 'Network error' };
  }
};

export const refreshAuthToken = async () => {
  try {
    const refresh = getRefreshToken();
    if (!refresh) {
      console.log('No refresh token available');
      return false;
    }

    const response = await httpCall('/api/refresh-token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ refreshToken: refresh })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      // Update tokens
      if (data.token) {
        setAuthToken(data.token);
      }
      if (data.accessToken) {
        setAccessToken(data.accessToken);
      }
      
      console.log('Token refreshed successfully');
      return true;
    } else {
      console.error('Token refresh failed:', data.error);
      return false;
    }
  } catch (error) {
    console.error('Token refresh error:', error);
    return false;
  }
};

export const logout = async () => {
  try {
    const token = getAuthToken();
    if (token) {
      await httpCall('/api/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    }
    
    // Clear token and reset state
    clearAuthToken();
    isAuthenticated.set(false);
    userRole.set(null);
    userEmail.set(null);
    isEmbedded.set(false);
  } catch (error) {
    console.error('Logout error:', error);
    // Still clear local state even if API call fails
    clearAuthToken();
    isAuthenticated.set(false);
    userRole.set(null);
    userEmail.set(null);
    isEmbedded.set(false);
  }
};

export const checkChatAccess = async () => {
  try {
    const token = getAuthToken();
    if (!token) {
      return false;
    }

    const response = await httpCall('/api/check-chat-access', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
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
