# Traductor_Salesforce
Este repositorio cuenta con un proyecto de Python para traducir archivos .stf de salesforce mediante la API de OpenAI. El resultado de la traducción son, como máximo, 4 archivos, disponibles en la carpeta de output:
1. El archivo .stf con las traducciones
2. Un archivo .xlsx con las traducciones que no son importables a Salesforce debido al los límites de carácteres
3. Archivo de texto opcional que contiene keys duplicadas en el archivo original
4. Archivo de texto opcional que contiene keys cuya traducción no está soportada por Salesforce

El programa está pensado para traducir un archivo Source exportado desde el Translation Workbench de Salesforce. Una vez obtenido el archvio con las traducciones (1), este debe importarse a Salesforce para aplicar los cambios de idioma en la organización.

Para ejecutar el programa, instalar Python (disponible en la Microsoft Store) y ejecutar el comando "python .\Traductor\" en el directorio donde se encuentre el paquete. Además, se debe proporcionar una Api Key de OpenAI para el funcionamiento de la traducción. Esta configuración y otros parametros adicionales son modificables desde el archivo "Traductor\resources\static\config.properties"
