# Instalación del Plugin `ISI_INVOICE for Odoo` para Odoo

## Paso 1: Descarga y Preparación

1. **Descarga el Plugin**
   - Descarga el paquete del plugin "isiodoo" desde esté repositorio.
  
> [!WARNING]
> Asegúrate de que el plugin "isiodoo" sea compatible con la versión de Odoo que estás utilizando. Si no es así, es posible que encuentres problemas de compatibilidad y funcionalidad.

2. **Cambiar el Nombre de la Carpeta**
   - Una vez descargado, cambia el nombre de la carpeta del plugin a **"isiodoo"** (con fines de prueba y desarrollo).

## Paso 2: Mover la Carpeta al Directorio de Instalación de Odoo

1. **Ubicación de Instalación de Odoo**
   - El directorio de instalación de Odoo normalmente se encuentra en:
     ```
     (nombre_de_la_carpeta_de_instalación)/odoo/addons/
     ```

2. **Mover la Carpeta**
   - Copia la carpeta **"isiodoo"** en el directorio de addons de Odoo:
     ```
     (nombre_de_la_carpeta_de_instalación)/odoo/addons/isiodoo
     ```

## Requisitos Previos

Antes de instalar y utilizar el plugin "isiodoo", asegúrate de que cumples con los siguientes requisitos:

- **Python**: Este componente está diseñado para funcionar con versiones de Odoo 17, 18 y posteriores. Por lo tanto, asegúrate de tener instalada una versión de Python compatible (preferiblemente Python 3.8 o superior).

- **Dependencias de Odoo**: Verifica que todas las dependencias de Odoo estén instaladas y configuradas correctamente. Esto incluye bibliotecas necesarias para la funcionalidad del plugin.

> [!TIP]
> Si no tienes instalado Odoo en tu sistema, puedes seguir la guía oficial de instalación de Odoo para configurar un entorno de desarrollo o producción.


## Instalación y Configuración Final

1. **Reiniciar el Servidor de Odoo**
   - Después de mover la carpeta, reinicia el servidor de Odoo para que reconozca el nuevo plugin.

2. **Activar el Plugin**
   - Ve al panel de administración de Odoo y activa el plugin "isiodoo" desde la sección de aplicaciones.

3. **Verificación**
   - Asegúrate de que el plugin esté funcionando correctamente realizando pruebas en la funcionalidad específica que ofrece.
  
> [!IMPORTANT]
> Si estás utilizando una versión de Odoo anterior a la 17, es posible que algunas funcionalidades del plugin "isiodoo" no estén disponibles, instala una versión compatible del plugin o actualiza tu instancia de Odoo.

## Comando mas Usados

#### 1. Iniciar el Servidor de Odoo
 ```
python3 odoo-bin --addons-path=addons -d (nombre de la bd)
 ```
### 2. Actualizar un Módulo
 ```
python3 odoo-bin --config /ruta/a/tu/archivo.conf --update nombre_del_modulo
 ```
#### 3. Instalar un Módulo
 ```
python3 odoo-bin --config /ruta/a/tu/archivo.conf --install nombre_del_modulo
 ```
#### 4. Reiniciar el Servidor
 ```
sudo systemctl restart odoo
 ```
#### 5. Verificar los Registros
 ```
tail -f /var/log/odoo/odoo.log
 ```
#### 6. Crear un Backup de la Base de Datos
 ```
pg_dump nombre_de_la_base_de_datos > /ruta/a/tu/backup.sql
 ```
#### 7. Restaurar una Base de Datos desde un Backup
 ```
psql nombre_de_la_base_de_datos < /ruta/a/tu/backup.sql
 ```
#### 8. Limpiar el Cache de Odoo
 ```
python3 odoo-bin --config /ruta/a/tu/archivo.conf --db-filter=nombre_de_la_base_de_datos --update=all
 ```
#### 9. Generar la Documentación de Odoo
 ```
python3 odoo-bin --config /ruta/a/tu/archivo.conf --generate-docs
 ```
### 10. Acceder al Entorno de Shell de Odoo
 ```
python3 odoo-bin shell --config /ruta/a/tu/archivo.conf
 ```

### 11. Comprimir el archivo
   ```
   zip -r ../isiodoo.zip . -x ".git/*" ".gitignore" "*.md" ".DS_Store" "*.pyc" "*/__pycache__/*" "*/.DS_Store" "*/.idea/*" "*/.vscode/*" "*/tests/*" "*/.pytest_cache/*" "*/.coverage" "*/htmlcov/*" "*/doc/*" "*/docs/*" "*/README.md" "*/CHANGELOG.md" "*/requirements.txt" "*/requirements-dev.txt"  
   ```

### 12. Subir el archivo comprimido, damos permisos y reiniciamos el servidor
   ```
   chown -R root:root /home/**/odooContainer/odoo-17/addons # Especificar la ruta de tu contenedor
   chmod -R 777 /home/**/odooContainer/odoo-17/addons # Especificar la ruta de tu contenedor
   ```

### 13. Descomprimir el archivo
   ```
   mkdir isiodoo              # Crear carpeta de destino
   unzip isiodoo.zip -d isiodoo  # Extraer el contenido dentro de la carpeta
   ```

### 14. Reinciciar el servidor docker
   ```
   docker restart odoo
   ```

   - Sube el archivo comprimido a la carpeta de addons de Odoo.
> [!TIP]
> La compresión es dentro de la carpeta addons/isiodoo, si se hacce desde afuera modificar la ruta.


> [!WARNING]
> La compresión del archivo es opcional, pero es recomendable para evitar problemas de compatibilidad y seguridad.



## Conclusión

Siguiendo estos pasos, podrás instalar y configurar el plugin "isiodoo" en tu instancia de Odoo. Si encuentras algún problema durante la instalación, consulta la documentación oficial de Odoo o busca soporte en la comunidad de Odoo.

Developer: [Nick](https://www.linkedin.com/in/nickynn/)

