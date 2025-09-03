# Worker Template

## Estructura

```bash
python_template
├── Dockerfile
├── Makefile
├── README.md
├── docker-compose.yml
├── pytest.ini
├── requirements.txt
├── src
│   ├── app.py
│   ├── application
│   │   └── business.py
│   ├── domain
│   │   ├── entities
│   │   │   └── example.py
│   │   └── repositories
│   │       └── repository_example.py
│   └── infrastructure
│       └── entity_manager.py
└── tests
    └── application
```

### Descripción de la estructura

- Dockerfile: archivo con la configuración para crear la imagen del servicio del worker
- Makefile: archivo para facilitar la compilación de los contenedores
- docker-compose.yml: archivo con la configuración para levantar el servicio del worker
- src: carpeta para almacenar el código del servicio
- app.py: archivo inicial para ejecutar el servicio del worker recibir los mensajes del bus de eventos, configuración de los logs, etc, llama a la función de inicio que manejara el evento solicitado al worker **business_logic(data: dict, context: dict) -> dict**
- application: carpeta para almacenar la lógica del servicio
   - business.py: archivo con la lógica del servicio contiene la función **business_logic(data: dict, context: dict) -> dict** 
- domain: carpeta para almacenar las clases de datos, entidades, repositorios, etc
   - entities: carpeta para almacenar las clases de datos
      - example.py: archivo con la clase de datos de ejemplo
   - repositories: carpeta para almacenar las clases de repositorios
      - repository_example.py: archivo con la clase de repositorio de ejemplo
- infrastructure: carpeta para almacenar la lógica para conectarse a servicios externos como bases de datos, correo, cache, etc
   - entity_manager.py: archivo con la lógica para conectarse a la base de datos
- tests: carpeta para almacenar las pruebas unitarias
   - application: carpeta para almacenar las pruebas unitarias de la lógica del servicio
      - test_business.py: archivo con las pruebas unitarias de la lógica del servicio


## Configurar el proyecto


1. Cambiar el nombre del servicio el docker-compose.yml
   ```yaml
   services:
   template_worker:
   ```
2. Configurar variables de entorno del servicio
   ```python
   # app.py
   APP_NAME = os.getenv("APP_NAME", "worker")
   TOPICS = os.environ["TOPICS"].split(",")  # si no se configura enviara una excepción al iniciar el servicio
   BUS_SECRET_NAME = os.getenv("BUS_SECRET_NAME", "dev/app/bus")
   ```

3. Archivo launch.json de vscode de ejemplo para configurar variables de entorno
   ``` json
      { 
      "version": "0.2.0",
      "configurations": [
         {
               "name": "Python: archivo actual",
               "type": "python",
               "request": "launch",
               "program": "${file}",
               "console": "integratedTerminal",
               "justMyCode": true,
               "env": {
                  "BUS_SECRET_NAME": "dev/app/bus",
                  "TOPICS": "topic1,topic2,topic3",
                  "MONGO_HOST":"mongodb://root:password@localhost:27017",
                  "KAFKA_HOST":"localhost:9092"
               }
            }
         ]
      }
   ```


4. Agregar la lógica del servicio

   ```python
   # business.py

   def business_logic(data: dict, context: dict) -> dict:
       pass

   ```

   la función `business_logic` recibe los 2 parámetros y regresa un diccionario

   - `data: dict`: es un diccionario que recibe el body del request realizado al api
   - `context: dict`: es un diccionario con la información de quien realizo la petición (sin implementar)
   - `-> dict`: la salida de la función debe se un diccionario que se pueda serealizar a json, el handler del mensaje `message_handler` agregara información extra a la petición y sera publicada en el bus de eventos

5. Levantar las dependencias ver repositorio [databases](https://github.com/copan-it/databases)
   
6. Levantar el API ver repositorio [python-api](https://github.com/copan-it/python-template)

7. comandos para: crear y activar entorno de python y instalar dependencias

   ```bash
   # crear entorno de python
   make create-venv

   # activar entorno de python
   source venv/bin/activate

   # desactivar entorno de python
   deactivate
   
   # instalar dependencias
   make install
   ```
8. Ejecutar pruebas unitarias, cobertura de código y reporte de cobertura

   ```bash
   # ejecutar pruebas unitarias
   make test

   # ejecutar pruebas unitarias con cobertura de código
   make coverage

   # reporte de cobertura
   make report

   # reporte de cobertura en html
   make report-html
   ```

9. Comandos de Makefile para: compilar, iniciar, parar, reiniciar, status, reconstruir, logs, y bash

   ```bash 
   # compila la imagen
   make build

   # levanta el contenedor
   make start

   # detiene el contenedor
   make stop

   # reinicia el contenedor
   make restart

   # muestra el status del contenedor
   make status

   # detiene, compila y levanta el contenedor del worker
   make rebuild

   # muestra los logs del contenedor
   make logs

   ```
10. Plataformas para realizar request http
   - Insomnia
   - Postman
   - curl
