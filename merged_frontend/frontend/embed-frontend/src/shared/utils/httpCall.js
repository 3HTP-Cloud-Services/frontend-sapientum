import config from '../../frontend/src/backend.json';

// Get API base URL from config
const getApiBaseUrl = () => {
  console.log('Using API URL:', config.apiUrl);
  return config.apiUrl;
};

// Track ongoing refresh to prevent multiple simultaneous refresh attempts
let refreshPromise = null;

// Check if a JWT token is expired or will expire soon
function isTokenExpired(token, bufferMinutes = 5) {
  if (!token) return true;
  
  try {
    // JWT tokens have 3 parts separated by dots
    const parts = token.split('.');
    if (parts.length !== 3) return true;
    
    // Decode the payload (second part)
    const payload = JSON.parse(atob(parts[1]));
    
    // Check if token has expiration time
    if (!payload.exp) return false; // No expiration, assume valid
    
    // Check if token is expired or will expire within buffer time
    const now = Math.floor(Date.now() / 1000);
    const expiresAt = payload.exp;
    const bufferSeconds = bufferMinutes * 60;
    
    return (expiresAt - now) <= bufferSeconds;
  } catch (error) {
    console.error('Error checking token expiration:', error);
    return true; // If we can't decode, assume expired
  }
}

// HTTP call function using XMLHttpRequest instead of fetch
export async function httpCall(url, options = {}) {
  console.log('httpCall', url, options);

  // If URL starts with /api, prepend the base URL
  if (typeof url === 'string' && url.startsWith('/api')) {
    console.log('\n\nhttpCall intercepting API call\n\n');
    const baseUrl = getApiBaseUrl();
    const normalizedEndpoint = url.replace('/api/', '');
    const newUrl = `${baseUrl}/${normalizedEndpoint}`;
    console.log(`Redirecting API call from ${url} to ${newUrl}`);
    url = newUrl;
  }

  // Check if token is expired before making API calls (proactive refresh)
  const isApiCall = typeof url === 'string' && (url.includes('/api/') || url.includes('/catalogs') || url.includes('/chat') || url.includes('/users'));
  if (isApiCall && !url.includes('refresh-token') && !url.includes('login')) {
    const currentToken = localStorage.getItem('authToken');
    if (currentToken && isTokenExpired(currentToken)) {
      console.log('Token expired, attempting proactive refresh');
      
      const refreshSuccessful = await attemptTokenRefresh();
      
      if (refreshSuccessful) {
        console.log('Proactive token refresh successful');
        // Update the Authorization header with the new token
        const newToken = localStorage.getItem('authToken');
        if (newToken && options.headers) {
          options.headers['Authorization'] = `Bearer ${newToken}`;
        }
      } else {
        console.log('Proactive token refresh failed, redirecting to login');
        // Clear tokens and redirect to login
        localStorage.removeItem('authToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('accessToken');
        window.location.href = '/#/login';
        return { ok: false, status: 401, statusText: 'Token refresh failed' };
      }
    }
  }

  // Make the initial request
  const response = await makeRequest(url, options);
  
  // Check if we got a 401 and this isn't already a refresh token request (reactive refresh)
  if (response.status === 401 && !url.includes('refresh-token') && !url.includes('login')) {
    console.log('Got 401, attempting reactive token refresh');
    
    // Try to refresh the token
    const refreshSuccessful = await attemptTokenRefresh();
    
    if (refreshSuccessful) {
      console.log('Reactive token refresh successful, retrying original request');
      // Update the Authorization header with the new token
      const newToken = localStorage.getItem('authToken');
      if (newToken && options.headers) {
        options.headers['Authorization'] = `Bearer ${newToken}`;
      }
      // Retry the original request with the new token
      return await makeRequest(url, options);
    } else {
      console.log('Reactive token refresh failed, redirecting to login');
      // Clear tokens and redirect to login
      localStorage.removeItem('authToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('accessToken');
      window.location.href = '/#/login';
      return response;
    }
  }
  
  return response;
}

// Attempt token refresh with promise caching to prevent multiple simultaneous requests
async function attemptTokenRefresh() {
  if (refreshPromise) {
    console.log('Token refresh already in progress, waiting...');
    return await refreshPromise;
  }

  refreshPromise = refreshTokenInternal();
  const result = await refreshPromise;
  refreshPromise = null;
  return result;
}

// Internal refresh function
async function refreshTokenInternal() {
  try {
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) {
      console.log('No refresh token available');
      return false;
    }

    // Build the full URL for the refresh endpoint
    const baseUrl = getApiBaseUrl();
    const refreshUrl = `${baseUrl}/refresh-token`;

    const response = await makeRequest(refreshUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ refreshToken })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      // Update tokens
      if (data.token) {
        localStorage.setItem('authToken', data.token);
      }
      if (data.accessToken) {
        localStorage.setItem('accessToken', data.accessToken);
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
}

// Make HTTP request using XMLHttpRequest
async function makeRequest(url, options = {}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const method = options.method || 'GET';

    xhr.open(method, url);

    // Set response type to arraybuffer for binary data (downloads and logo GET requests)
    // Only set arraybuffer for GET requests to logo endpoint, not POST requests
    if (url.includes('/download') || (url.includes('/logo') && method === 'GET')) {
      xhr.responseType = 'arraybuffer';
    }

    // Prepare headers
    const headers = { ...options.headers };

    // Auto-add Authorization header for API calls if not already present and token exists
    const isApiCall = typeof url === 'string' && (url.includes('/api/') || url.includes('/catalogs') || url.includes('/chat') || url.includes('/users'));
    if (isApiCall && !headers['Authorization']) {
      const token = localStorage.getItem('authToken');
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
        console.log('Auto-adding Authorization header for API call');
      } else {
        console.log('No auth token found for API call');
      }
    }

    // Set headers (but not Content-Type for FormData - browser will set it automatically)
    Object.keys(headers).forEach(key => {
      if (!(options.body instanceof FormData && key.toLowerCase() === 'content-type')) {
        xhr.setRequestHeader(key, headers[key]);
      }
    });

    xhr.onload = () => {
      const response = {
        ok: xhr.status >= 200 && xhr.status < 300,
        status: xhr.status,
        statusText: xhr.statusText,
        headers: {
          get: (name) => xhr.getResponseHeader(name),
          getAllResponseHeaders: () => xhr.getAllResponseHeaders()
        },
        text: () => Promise.resolve(xhr.responseText),
        json: () => {
          try {
            return Promise.resolve(JSON.parse(xhr.responseText));
          } catch (e) {
            return Promise.reject(e);
          }
        },
        blob: () => Promise.resolve(new Blob([xhr.response]))
      };
      resolve(response);
    };

    xhr.onerror = () => {
      reject(new Error('Network error'));
    };

    xhr.ontimeout = () => {
      reject(new Error('Request timeout'));
    };

    // Send request
    if (options.body) {
      if (typeof options.body === 'string') {
        xhr.send(options.body);
      } else if (options.body instanceof FormData) {
        // Send FormData directly without stringifying
        xhr.send(options.body);
      } else {
        xhr.send(JSON.stringify(options.body));
      }
    } else {
      xhr.send();
    }
  });
}
