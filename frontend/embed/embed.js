(function() {
  // Configuration options with defaults
  const SapientumEmbed = {
    create: function(targetSelector, options = {}) {
      // Default configuration
      const config = {
        width: options.width || '100%',
        height: options.height || '600px',
        server: options.server || window.location.origin,
        theme: options.theme || 'light',
        autoLogin: options.autoLogin || false,
        credentials: options.credentials || null,
        chatOnly: options.chatOnly || false,
        onMessage: options.onMessage || function() {},
        onReady: options.onReady || function() {}
      };

      // Find target element
      const targetElement = document.querySelector(targetSelector);
      if (!targetElement) {
        console.error('Sapientum Embed: Target element not found:', targetSelector);
        return;
      }

      // Create container with unique ID
      const containerId = 'sapientum-embed-' + Math.random().toString(36).substring(2, 15);
      const container = document.createElement('div');
      container.id = containerId;
      container.className = 'sapientum-embed-container';
      container.style.width = config.width;
      container.style.height = config.height;
      container.style.border = 'none';
      container.style.overflow = 'hidden';
      container.style.position = 'relative';
      
      targetElement.appendChild(container);

      // Create iframe
      const iframe = document.createElement('iframe');
      iframe.style.width = '100%';
      iframe.style.height = '100%';
      iframe.style.border = 'none';
      iframe.style.overflow = 'hidden';
      
      // Set source URL with embed parameter to signal to the frontend it's embedded
      let appUrl = `${config.server}/#/?embedded=true&theme=${config.theme}`;
      
      // Add chatOnly parameter if needed
      if (config.chatOnly) {
        appUrl += '&chatOnly=true';
      }
      
      iframe.src = appUrl;
      
      container.appendChild(iframe);

      // Setup message handling for cross-domain communication
      window.addEventListener('message', function(event) {
        // Verify origin for security
        if (event.origin !== config.server && !config.server.includes(event.origin)) {
          return;
        }
        
        const message = event.data;
        
        // Handle specific message types
        if (message.type === 'sapientum:ready') {
          config.onReady(iframe.contentWindow);
          
          // If auto login is enabled and credentials provided
          if (config.autoLogin && config.credentials) {
            iframe.contentWindow.postMessage({
              type: 'sapientum:login',
              credentials: config.credentials
            }, config.server);
          }
        }
        
        // Forward all messages to the custom handler
        config.onMessage(message);
      });

      // Return API for controlling the embed
      return {
        iframe: iframe,
        chatOnly: config.chatOnly, // Expose chatOnly setting
        getContainer: function() {
          return container;
        },
        sendMessage: function(message) {
          iframe.contentWindow.postMessage(message, config.server);
        },
        resize: function(width, height) {
          if (width) container.style.width = width;
          if (height) container.style.height = height;
        },
        destroy: function() {
          window.removeEventListener('message', this.messageHandler);
          container.remove();
        }
      };
    }
  };

  // Expose to global scope
  window.SapientumEmbed = SapientumEmbed;
})();