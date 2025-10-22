# Arquitectura del Proyecto

Este documento describe la arquitectura y los componentes principales del proyecto Flask en AWS Lambda.

## Visión General

La aplicación es una API REST construida con Flask que se ejecuta en AWS Lambda y se expone a través de API Gateway. Utiliza una base de datos PostgreSQL para almacenamiento persistente y AWS Secrets Manager para gestionar credenciales.

## Componentes Principales

### 1. Aplicación Flask (`backend/app.py`)

El núcleo de la aplicación es un servidor Flask que maneja las solicitudes HTTP y proporciona las siguientes funcionalidades:
- Autenticación de usuarios
- Gestión de catálogos y documentos
- Conversaciones de chat
- Gestión de usuarios y permisos

### 2. Modelos de Datos (`backend/models/`)

Define la estructura de la base de datos utilizando SQLAlchemy ORM:
- `User`: Usuarios del sistema con roles y permisos
- `Domain`: Dominios permitidos para usuarios
- `Catalog`: Catálogos de documentos
- `File`: Archivos almacenados en S3
- `Version`: Versiones de archivos
- `Conversation`: Conversaciones de chat
- `Message`: Mensajes individuales en conversaciones
- `ActivityLog`: Registro de actividades del sistema

### 3. Adaptador Lambda (`backend/lambda_handler.py`)

Actúa como puente entre AWS Lambda y la aplicación Flask:
- Convierte eventos de API Gateway en solicitudes WSGI
- Inicializa la conexión a la base de datos
- Maneja errores y proporciona respuestas formateadas
- Configura el entorno de ejecución

### 4. Utilidades de Base de Datos (`backend/db.py`)

Gestiona la conexión a la base de datos:
- Recupera credenciales de AWS Secrets Manager
- Configura la conexión a PostgreSQL
- Proporciona fallback a SQLite para desarrollo
- Prueba la conectividad de la base de datos

## Flujo de Datos

1. El cliente envía una solicitud HTTP a API Gateway
2. API Gateway invoca la función Lambda con el evento HTTP
3. `lambda_handler.py` convierte el evento en una solicitud WSGI
4. La aplicación Flask procesa la solicitud
5. Si es necesario, la aplicación interactúa con la base de datos
6. Flask genera una respuesta HTTP
7. `lambda_handler.py` convierte la respuesta WSGI en un formato compatible con API Gateway
8. API Gateway devuelve la respuesta al cliente

## Seguridad

- **Autenticación**: Basada en sesiones con Flask
- **Credenciales**: Almacenadas en AWS Secrets Manager
- **Permisos**: Gestionados a través de roles IAM y permisos de aplicación
- **Datos**: Transmitidos a través de HTTPS

## Escalabilidad

- **Computación**: AWS Lambda escala automáticamente según la demanda
- **Base de datos**: PostgreSQL debe dimensionarse adecuadamente
- **Almacenamiento**: S3 proporciona almacenamiento escalable para archivos

## Diagrama de Arquitectura

```
┌─────────┐     ┌─────────────┐     ┌───────────────┐     ┌─────────────┐
│  Cliente │────▶│ API Gateway │────▶│ AWS Lambda    │────▶│ PostgreSQL  │
└─────────┘     └─────────────┘     │ (Flask App)   │     └─────────────┘
                                    └───────┬───────┘
                                            │
                                            ▼
                                    ┌─────────────┐     ┌─────────────┐
                                    │ AWS Secrets │     │     S3      │
                                    │  Manager    │     │  (Archivos) │
                                    └─────────────┘     └─────────────┘
```

## Consideraciones de Diseño

1. **Serverless**: La arquitectura serverless permite escalar automáticamente y pagar solo por lo que se usa.

2. **Separación de Responsabilidades**: Cada componente tiene una responsabilidad clara:
   - Flask: Lógica de negocio y API
   - SQLAlchemy: Abstracción de base de datos
   - Lambda Handler: Integración con AWS

3. **Configuración Externalizada**: Las credenciales y configuraciones sensibles se almacenan en AWS Secrets Manager.

4. **Fallback para Desarrollo**: El uso de SQLite como fallback facilita el desarrollo y pruebas locales.

5. **Manejo de Errores**: Captura y registro de errores en cada nivel para facilitar la depuración.