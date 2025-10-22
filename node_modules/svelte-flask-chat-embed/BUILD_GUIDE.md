# Guía de Construcción - Frontend Embebido

## Requisitos Previos

- Node.js (versión 16 o superior)
- npm
- Backend Lambda funcionando

## Configuración Inicial

### 1. Instalar Dependencias
```bash
cd embed-frontend
npm install
```

### 2. Configurar Backend
Editar `src/backend.json`:
```json
{
  "apiUrl": "https://tu-lambda-url.lambda-url.us-east-1.on.aws/api"
}
```

### 3. Configurar Proxy (Desarrollo)
En `vite.config.js`, actualizar el proxy:
```javascript
proxy: {
  '/api': {
    target: 'https://tu-lambda-url.lambda-url.us-east-1.on.aws',
    changeOrigin: true,
    secure: false
  }
}
```

## Comandos de Construcción

### Desarrollo
```bash
npm run dev
```
- Inicia servidor en `http://localhost:5573`
- Hot reload habilitado
- Proxy configurado para evitar CORS

### Producción
```bash
npm run build
```
- Genera archivos optimizados en `dist/`
- Minifica CSS y JavaScript
- Rutas relativas para assets

### Vista Previa
```bash
npm run preview
```
- Sirve la versión de producción localmente

## Estructura de Archivos Generados

```
dist/
├── index.html              # Página principal
├── assets/
│   ├── index-[hash].css    # Estilos compilados
│   └── index-[hash].js     # JavaScript compilado
```

## Despliegue

### Opción 1: Servidor Web Estático
```bash
# Copiar archivos dist/ a tu servidor web
cp -r dist/* /var/www/html/
```

### Opción 2: AWS S3 + CloudFront
```bash
# Subir a S3
aws s3 sync dist/ s3://tu-bucket-name/

# Invalidar CloudFront
aws cloudfront create-invalidation --distribution-id YOUR_ID --paths "/*"
```

### Opción 3: Nginx
```nginx
server {
    listen 80;
    server_name tu-dominio.com;
    root /path/to/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Configuración CORS

### En tu Lambda
```python
headers = {
    'Access-Control-Allow-Origin': 'https://tu-dominio.com',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Credentials': 'true'
}
```

### En API Gateway
1. Ir a AWS Console → API Gateway
2. Seleccionar tu API
3. Actions → Enable CORS
4. Configurar origins permitidos
5. Deploy API

## Variables de Entorno

Para diferentes entornos, crear archivos:

### `.env.development`
```
VITE_API_URL=http://localhost:8000/api
```

### `.env.production`
```
VITE_API_URL=https://tu-lambda-url.lambda-url.us-east-1.on.aws/api
```

## Solución de Problemas

### Error CORS
- Verificar configuración CORS en Lambda/API Gateway
- Usar proxy en desarrollo (`secure: false`)

### Error 404 en rutas
- Configurar servidor para servir `index.html` en todas las rutas
- Verificar `base: './'` en `vite.config.js`

### Certificados SSL
- Usar `secure: false` en proxy de desarrollo
- Verificar certificados en producción

## Optimizaciones

### Reducir tamaño del bundle
```javascript
// En vite.config.js
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        vendor: ['svelte', 'svelte-spa-router']
      }
    }
  }
}
```

### Cache busting
Los archivos incluyen hash automáticamente para cache busting.

## Monitoreo

### Logs de desarrollo
```bash
npm run dev -- --debug
```

### Análisis del bundle
```bash
npm run build -- --analyze
```