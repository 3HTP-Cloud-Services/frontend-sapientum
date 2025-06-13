import config from '../../frontend/src/backend.json';

// Get API base URL from config
const getApiBaseUrl = () => {
  console.log('Using API URL:', config.apiUrl);
  return config.apiUrl;
};

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

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const method = options.method || 'GET';
    
    xhr.open(method, url);
    
    // Set response type to arraybuffer for binary data (downloads)
    if (url.includes('/download')) {
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
      }
    }
    
    // Set headers (but not Content-Type for FormData - browser will set it automatically)
    Object.keys(headers).forEach(key => {
      if (!(options.body instanceof FormData && key.toLowerCase() === 'content-type')) {
        xhr.setRequestHeader(key, headers[key]);
      }
    });
    
    // Remove credentials handling since we're using JWT tokens now
    // if (options.credentials === 'include') {
    //   xhr.withCredentials = true;
    // }
    
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