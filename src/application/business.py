import io
import logging
import zipfile
from datetime import datetime
from result import Ok, Err
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from infrastructure.s3 import upload_file, download_file
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

logger = logging.getLogger(__name__)

def upload_file_logic(file_content, bucket_name, key):
    file_buffer = io.BytesIO(file_content)

    try:
        success = upload_file(file_buffer, bucket_name, key)
        
        if success == True:
            return Ok({"message": "File uploaded successfully", "status": "success"})
        else:
            return Err(success)  # Pass the specific error (e.g., "BucketNotFound") directly

    except NoCredentialsError:
        logger.error("AWS credentials not found")
        return Err("AWS credentials not found")

    except PartialCredentialsError:
        logger.error("Incomplete AWS credentials")
        return Err("Incomplete AWS credentials")

    except ClientError as e:
        logger.error(f"ClientError: {e}")
        return Err(f"ClientError: {e}")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return Err(f"An unexpected error occurred: {e}")

# Función para la lógica de descarga de archivos
def download_file_logic(files_data):
    final_zip_buffer = io.BytesIO()  # Buffer para el ZIP final
    has_files = False  # Verifica si al menos un archivo fue descargado
    missing_files = []  # Lista para almacenar archivos que no se encontraron

    with zipfile.ZipFile(final_zip_buffer, 'w') as final_zip:
        for bucket_name, folders in files_data.items():
            for folder_dict in folders:
                for folder_name, files in folder_dict.items():
                    folder_zip_buffer = io.BytesIO()  # Buffer en memoria para el ZIP de la carpeta
                    files_in_folder = False  # Asegura que la carpeta tiene archivos válidos

                    with zipfile.ZipFile(folder_zip_buffer, 'w') as folder_zip:
                        for file_info in files:
                            key = file_info["key"]
                            file_name = file_info["fileName"]
                            # Descargar el archivo de S3
                            file_obj = download_file(bucket_name, key)

                            if file_obj:
                                folder_zip.writestr(file_name, file_obj.read())
                                files_in_folder = True
                                has_files = True  # Marcar que se encontró al menos un archivo
                            else:
                                logger.error(f"Failed to download {key} from {bucket_name}")
                                missing_files.append(f"{key} from {bucket_name}")
                                # Continuar con el siguiente archivo en lugar de retornar un error

                    # Solo agregar la carpeta si contiene archivos válidos
                    if files_in_folder:
                        folder_zip_buffer.seek(0)
                        final_zip.writestr(f"{folder_name}.zip", folder_zip_buffer.getvalue())

    if not has_files:
        # En lugar de lanzar un error, devolvemos un mensaje personalizado
        return {
            "response": None,
            "error": "No files found to download.",
            "status_code": 404  # Puedes cambiar este código según lo que necesites
        }
    
    if missing_files:
        # Retornar una advertencia sobre los archivos que faltan, pero devolver el ZIP
        final_zip_buffer.seek(0)  # Asegurarse de que el buffer del ZIP esté en el inicio
        return StreamingResponse(
            final_zip_buffer,
            headers={
                "Content-Disposition": f"attachment; filename={datetime.now().strftime('%Y%m%d%H%M%S')}.zip",
                "Content-Type": "application/zip"
            },
            status_code=206  # Aquí especificamos el código de estado 206
        )

    # Generar el nombre del archivo ZIP final con timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    final_filename = f"{timestamp}.zip"

    # Devolver el ZIP final como StreamingResponse con el nombre formateado
    final_zip_buffer.seek(0)  # Asegurarse de que el buffer del ZIP esté en el inicio
    headers = {
        "Content-Disposition": f"attachment; filename={final_filename}",
        "Content-Type": "application/zip"
    }

    return StreamingResponse(final_zip_buffer, headers=headers, status_code=200)


uses_cases = {
    "put_file": upload_file_logic,
    "get_file": download_file_logic,
}

def business_logic(action, context: dict) -> dict:
    logger.info(f"Context: {context}")
    logger.info(f"Action: {action}")

    if action not in uses_cases:
        raise Exception(f"Event {action} not found")
    
    use_case = uses_cases[action]
    result = use_case(**context)

    match result:
        case Ok(value):
            return {                    
                "response": value,
                "error": None
            }
        case Err(error):
            error_message = str(error)
            logger.error(f"Business logic error: {error_message}")
            
            if error_message == "BucketNotFound":
                return {
                    "response": "",
                    "error": "Bucket not found",
                    "status_code": 404
                }
            elif "ClientError" in error_message:
                return {
                    "response": "",
                    "error": "Client error occurred during file upload",
                    "status_code": 500
                }
            else:
                return {
                    "response": "",
                    "error": "An unexpected error occurred",
                    "status_code": 500  # Internal Server Error
                }
        case _:
            return result
