# Guía de Despliegue

Esta guía detalla los pasos para desplegar la aplicación Flask en AWS Lambda usando SAM.

## Preparación del Entorno

1. **Configurar AWS CLI**:
   ```bash
   aws configure
   ```
   Ingresa tus credenciales AWS, región (us-east-1) y formato de salida (json).

2. **Verificar instalación de SAM CLI**:
   ```bash
   sam --version
   ```
   Debe mostrar la versión instalada. Si no está instalado, sigue las [instrucciones de instalación](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html).

## Despliegue Paso a Paso

### 1. Construir el Proyecto

```bash
cd /Users/lramirez/Documents/3HTP/svelte_flask/lambda
sam build
```

Este comando:
- Instala las dependencias de Python
- Empaqueta la aplicación
- Prepara el paquete para despliegue

### 2. Desplegar la Aplicación

Para un despliegue guiado (recomendado para la primera vez):
```bash
sam deploy --guided
```

Sigue las instrucciones:
- **Stack Name**: Nombre para tu pila CloudFormation (ej. "sapientum-api")
- **AWS Region**: us-east-1 (debe ser la misma región donde está el secreto)
- **Confirm changes before deploy**: "Y" para revisar los cambios
- **Allow SAM CLI IAM role creation**: "Y" para permitir la creación de roles IAM
- **Disable rollback**: "N" para permitir rollback en caso de error
- **Save arguments to samconfig.toml**: "Y" para guardar la configuración

Para despliegues posteriores, puedes usar:
```bash
sam deploy
```

### 3. Verificar el Despliegue

Una vez completado el despliegue, SAM mostrará:
- URL del API Gateway
- Nombre de la función Lambda
- Otros recursos creados

Puedes verificar los recursos en la consola AWS:
- CloudFormation: Para ver la pila creada
- Lambda: Para ver la función desplegada
- API Gateway: Para ver la API creada

## Actualización de la Aplicación

Para actualizar la aplicación después de cambios en el código:

1. Reconstruir:
   ```bash
   sam build
   ```

2. Redesplegar:
   ```bash
   sam deploy
   ```

## Eliminación de Recursos

Para eliminar todos los recursos creados:

```bash
sam delete
```

O desde la consola AWS CloudFormation, elimina la pila.

## Solución de Problemas de Despliegue

### Error de Permisos IAM
Si encuentras errores de permisos durante el despliegue:
1. Verifica que tu usuario AWS tenga permisos suficientes
2. Considera usar `--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM` en el comando `sam deploy`

### Error de Acceso al Secreto
Si la función Lambda no puede acceder al secreto:
1. Verifica que el secreto exista en la región correcta
2. Confirma que la política IAM en `template.yaml` tenga el ARN correcto del secreto
3. Si el secreto está en otra cuenta, asegúrate de que tenga una política de recursos que permita el acceso

### Error de Conexión a la Base de Datos
Si la función Lambda no puede conectarse a la base de datos:
1. Verifica que las credenciales en el secreto sean correctas
2. Asegúrate de que la base de datos sea accesible desde Lambda (VPC, grupos de seguridad)
3. Revisa los logs de CloudWatch para ver errores específicos