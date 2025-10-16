# Sapientum AI Embed Documentation

This document provides instructions for embedding the Sapientum AI application into your website with minimal configuration.

## Getting Started

### 1. Add the Embed Script

Add the following script tag to your HTML page:

```html
<script src="https://your-sapientum-server.com/embed.js"></script>
```

### 2. Create a Container Element

Create a container element where the embedded application will be loaded:

```html
<div id="sapientum-container"></div>
```

### 3. Initialize the Embed

Initialize the embed with your desired configuration:

```html
<script>
  const embed = SapientumEmbed.create('#sapientum-container', {
    width: '100%',
    height: '600px',
    server: 'https://your-sapientum-server.com',
    theme: 'light'
  });
</script>
```

## Configuration Options

The `SapientumEmbed.create()` function accepts the following options:

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `width` | String | '100%' | Width of the embed container |
| `height` | String | '600px' | Height of the embed container |
| `server` | String | window.location.origin | URL of the Sapientum server |
| `theme` | String | 'light' | Theme ('light' or 'dark') |
| `autoLogin` | Boolean | false | Whether to attempt auto-login |
| `credentials` | Object | null | Credentials for auto-login (if enabled) |
| `onMessage` | Function | - | Callback for messages from the embed |
| `onReady` | Function | - | Callback when the embed is ready |

## API Reference

The `SapientumEmbed.create()` function returns an API object with the following methods:

| Method | Description |
| --- | --- |
| `getContainer()` | Returns the container element |
| `sendMessage(message)` | Sends a message to the embedded application |
| `resize(width, height)` | Resizes the embed container |
| `destroy()` | Removes the embed from the page |

## Message Types

You can send messages to the embedded application using the `sendMessage()` method:

```javascript
embed.sendMessage({
  type: 'sapientum:navigate',
  path: '/console'
});
```

### Supported Message Types

| Type | Description | Parameters |
| --- | --- | --- |
| `sapientum:navigate` | Navigate to a specific path | `path`: Path to navigate to |
| `sapientum:login` | Attempt to log in | `credentials`: Login credentials |

### Messages from the Embed

The embedded application can send messages back to the parent page:

| Type | Description | Data |
| --- | --- | --- |
| `sapientum:ready` | The application is ready | `status`: 'success' |
| `sapientum:navigationChanged` | Navigation has changed | `path`: Current path |

## Examples

### Basic Example

```html
<div id="sapientum-container"></div>

<script src="https://your-sapientum-server.com/embed.js"></script>
<script>
  const embed = SapientumEmbed.create('#sapientum-container', {
    width: '100%',
    height: '600px',
    server: 'https://your-sapientum-server.com',
    theme: 'light'
  });
</script>
```

### Handle Messages

```javascript
const embed = SapientumEmbed.create('#sapientum-container', {
  // ... other options
  onMessage: function(message) {
    if (message.type === 'sapientum:navigationChanged') {
      console.log('Navigation changed to:', message.path);
    }
  }
});
```

### Resize the Embed

```javascript
// Resize to full width and 800px height
embed.resize('100%', '800px');
```

### Navigate Programmatically

```javascript
// Navigate to the chat section
embed.sendMessage({
  type: 'sapientum:navigate',
  path: '/console/chat'
});
```

## Browser Support

The embed functionality works in all modern browsers:

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Troubleshooting

If you experience issues with the embed:

1. Check the browser console for errors
2. Ensure your server's CORS configuration allows embedding
3. Verify that the server URL is correct and accessible

For more help, contact your Sapientum administrator.