import { httpCall } from './httpCall.js';

// Logo cache - stores blob URL and timestamp
let logoCache = {
  url: null,
  timestamp: 0,
  cacheTimeout: 60000 // 1 minute in milliseconds
};

/**
 * Clear the logo cache (called when logo is uploaded)
 */
export function clearLogoCache() {
  if (logoCache.url) {
    URL.revokeObjectURL(logoCache.url);
  }
  logoCache.url = null;
  logoCache.timestamp = 0;
  console.log('Logo cache cleared');
}

/**
 * Load company logo from the API with 1-minute caching
 * @returns {Promise<string|null>} Promise that resolves to a blob URL or null if no logo
 */
export async function loadLogo() {
  try {
    const now = Date.now();
    
    // Check if we have a valid cached logo
    if (logoCache.url && (now - logoCache.timestamp) < logoCache.cacheTimeout) {
      console.log('Using cached logo');
      return logoCache.url;
    }
    
    // Clear old cached URL if it exists
    if (logoCache.url) {
      URL.revokeObjectURL(logoCache.url);
      logoCache.url = null;
    }
    
    console.log('Loading fresh logo from API');
    const cacheBuster = Date.now();
    const response = await httpCall(`/api/logo?v=${cacheBuster}`);
    
    if (response.ok) {
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      
      // Cache the new logo
      logoCache.url = blobUrl;
      logoCache.timestamp = now;
      
      return blobUrl;
    }
    // If response is not ok (like 404), return null
    return null;
  } catch (err) {
    // Silently fail - logo is optional
    console.log('No logo available');
    return null;
  }
}