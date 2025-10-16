# Installing Nginx for the Sapientum AI Embed Server

This document provides instructions for installing Nginx on different platforms to run the Sapientum AI embed server.

## macOS

### Using Homebrew (Recommended)

1. If you don't have Homebrew installed, install it with:
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. Install Nginx:
   ```
   brew install nginx
   ```

3. After installation, you can run the embed server using:
   ```
   cd /Users/jpnunez/aicompetency/svelte_flask/frontend/embed
   ./start-nginx.sh
   ```

### Using MacPorts

1. If you prefer MacPorts:
   ```
   sudo port install nginx
   ```

## Linux (Debian/Ubuntu)

```
sudo apt update
sudo apt install nginx
```

## Windows

1. Download the Windows version of Nginx from: http://nginx.org/en/download.html
2. Extract the zip file to a location of your choice
3. Update the paths in nginx.conf to use Windows-style paths
4. Run nginx.exe from the extracted directory

## Alternative: Using Docker

If you prefer to use Docker, you can run Nginx in a container:

1. Install Docker if you don't have it
2. Create a Dockerfile in the embed directory:
   ```
   FROM nginx:alpine
   COPY . /usr/share/nginx/html
   COPY nginx.conf /etc/nginx/conf.d/default.conf
   EXPOSE 7000
   ```

3. Build and run the Docker container:
   ```
   docker build -t sapientum-embed .
   docker run -p 7000:7000 sapientum-embed
   ```

## Testing Your Installation

After installing Nginx, test your installation by running:

```
nginx -v
```

You should see the Nginx version displayed.

## Using Python's Simple HTTP Server as an Alternative

If you have Python installed, you can use its built-in HTTP server as an alternative to Nginx:

```
cd /Users/jpnunez/aicompetency/svelte_flask/frontend/embed
python -m http.server 7000
```

This will serve the files in the current directory on port 7000, accessible at http://localhost:7000