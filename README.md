# Frontend Clean

## Configuración e Instalación

### 1. Configurar URL del Backend

Antes de compilar, edita el archivo `frontend/src/backend.json` para especificar la URL de tu lambda del backend:

```json
{
  "apiUrl": "https://tu-lambda-url.amazonaws.com/api"
}
```

### 2. Instalar y Ejecutar

```bash
cd frontend
npm install && npm run dev
```

## Estructura del Proyecto

- `frontend/src/backend.json` - Configuración de la URL del API backend
- `frontend/` - Aplicación principal del frontend
- `shared-components/` - Componentes compartidos
- `embed-frontend/` - Frontend embebido
