import os
import json
import logging
from typing import Optional
import re
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    status,
    File,
    UploadFile,
    Body,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

from application.business import business_logic
from ds_security_validation.verification import Verification
from infrastructure.secret_manager import get_key_jwt


APP_NAME = os.getenv("APP_NAME", "python-transfers")
LOGGIN_LEVEL = os.getenv("LOGGIN_LEVEL", "DEBUG")

# Configuración S3 para videos
S3_BUCKET_VIDEOS = os.getenv(
    "S3_BUCKET_VIDEOS", "ds-multiad-help-202506041618"
)  # Configura tu bucket

JWT_SECRET = os.environ["JWT_SECRET_KEY_NAME"]

jw_key = get_key_jwt(JWT_SECRET)

ORIGINS = ["*"]

log_format = (
    f"%(asctime)s - [%(levelname)s] - {APP_NAME} - %(name)s - "
    "%(filename)s:%(lineno)d - %(funcName)s() - %(message)s"
)
logging.basicConfig(level=logging.getLevelName(LOGGIN_LEVEL), format=log_format)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_s3_client():
    """
    Obtiene el cliente de S3
    """
    try:
        return boto3.client("s3")
    except NoCredentialsError:
        logger.error("AWS credentials not found")
        raise Exception("AWS credentials not configured")


def parse_range_header(range_header: str, file_size: int):
    """
    Parse HTTP Range header y retorna posiciones de inicio y fin
    """
    if not range_header:
        return 0, file_size - 1

    range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not range_match:
        return 0, file_size - 1

    start = int(range_match.group(1))
    end = int(range_match.group(2)) if range_match.group(2) else file_size - 1

    # Asegurar que los valores estén dentro del rango válido
    start = max(0, min(start, file_size - 1))
    end = max(start, min(end, file_size - 1))

    return start, end


@app.get("/transfers/api/health")
async def health():
    """
    @description: API to check the health of the application
    @return: response: dict
    """
    return {"status": "ok"}


@app.get("/health")
async def health():
    """
    @description: API to check the health of the application
    @return: response: dict
    """
    return {"status": "ok"}


@app.get("/transfers/api/video/stream")
async def stream_video(video_path: str, request: Request):
    """
    Stream de video desde S3 con soporte para Range requests

    Args:
        video_path: Path del video en S3 (ej: "Negotiaton/Ejecutivos/Guía rápida Editar un ejecutivo (2).mp4")
        request: Request object para obtener headers

    Returns:
        StreamingResponse con el video
    """
    try:
        logger.info(f"Solicitando stream de video: {video_path}")

        # Obtener cliente S3
        s3_client = get_s3_client()

        # Primero obtener información del archivo
        try:
            head_response = s3_client.head_object(
                Bucket=S3_BUCKET_VIDEOS, Key=video_path
            )
            file_size = head_response["ContentLength"]
            content_type = head_response.get("ContentType", "video/mp4")

            logger.info(
                f"Video encontrado - Tamaño: {file_size} bytes, Tipo: {content_type}"
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                logger.error(f"Video no encontrado: {video_path}")
                raise HTTPException(
                    status_code=404, detail=f"Video no encontrado: {video_path}"
                )
            elif error_code == "403":
                logger.error(f"Acceso denegado al video: {video_path}")
                raise HTTPException(status_code=403, detail="Acceso denegado al video")
            else:
                logger.error(f"Error al acceder al video: {str(e)}")
                raise HTTPException(
                    status_code=500, detail="Error interno del servidor"
                )

        # Parsear Range header si existe
        range_header = request.headers.get("range")
        start, end = parse_range_header(range_header, file_size)
        content_length = end - start + 1

        logger.debug(f"Range solicitado: {start}-{end} de {file_size}")

        # Obtener el contenido del video con rango específico
        try:
            if range_header:
                # Solicitud con rango específico
                range_param = f"bytes={start}-{end}"
                get_response = s3_client.get_object(
                    Bucket=S3_BUCKET_VIDEOS, Key=video_path, Range=range_param
                )
                status_code = 206  # Partial Content
            else:
                # Solicitud completa
                get_response = s3_client.get_object(
                    Bucket=S3_BUCKET_VIDEOS, Key=video_path
                )
                status_code = 200

            # Leer el contenido
            video_content = get_response["Body"].read()

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "InvalidRange":
                logger.error(f"Rango inválido solicitado: {range_header}")
                raise HTTPException(
                    status_code=416, detail="Rango solicitado no válido"
                )
            else:
                logger.error(f"Error al obtener contenido del video: {str(e)}")
                raise HTTPException(status_code=500, detail="Error al obtener el video")

        # Preparar headers para la respuesta
        headers = {
            "Content-Type": content_type,
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Cache-Control": "public, max-age=3600",  # Cache por 1 hora
        }

        # Si es una solicitud de rango, agregar Content-Range header
        if range_header:
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

        # Crear generador para streaming del contenido
        def generate_video_chunks():
            chunk_size = 8192  # 8KB por chunk
            for i in range(0, len(video_content), chunk_size):
                yield video_content[i : i + chunk_size]

        logger.info(f"Streaming video exitoso: {video_path} - {content_length} bytes")

        return StreamingResponse(
            generate_video_chunks(),
            status_code=status_code,
            headers=headers,
            media_type=content_type,
        )

    except HTTPException:
        # Re-raise HTTPExceptions para que FastAPI las maneje
        raise
    except Exception as e:
        logger.error(f"Error inesperado en stream de video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


class VideoStreamRequest(BaseModel):
    video_path: str


@app.get("/transfers/api/video/info")
async def get_video_info(video_path: str):
    """
    Obtiene información sobre un video sin descargarlo

    Args:
        video_path: Path del video en S3

    Returns:
        Información del video (tamaño, tipo, etc.)
    """
    try:
        logger.info(f"Obteniendo información del video: {video_path}")

        s3_client = get_s3_client()

        # Obtener metadata del archivo
        head_response = s3_client.head_object(Bucket=S3_BUCKET_VIDEOS, Key=video_path)

        video_info = {
            "video_path": video_path,
            "file_size": head_response["ContentLength"],
            "content_type": head_response.get("ContentType", "video/mp4"),
            "last_modified": (
                head_response.get("LastModified").isoformat()
                if head_response.get("LastModified")
                else None
            ),
            "etag": head_response.get("ETag"),
            "size_mb": round(head_response["ContentLength"] / (1024 * 1024), 2),
        }

        logger.info(f"Información obtenida exitosamente para: {video_path}")
        return video_info

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "404":
            logger.error(f"Video no encontrado: {video_path}")
            raise HTTPException(
                status_code=404, detail=f"Video no encontrado: {video_path}"
            )
        elif error_code == "403":
            logger.error(f"Acceso denegado al video: {video_path}")
            raise HTTPException(status_code=403, detail="Acceso denegado al video")
        else:
            logger.error(f"Error al obtener información del video: {str(e)}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.get("/transfers/api/videos/list")
async def list_videos(prefix: str = ""):
    """
    Lista videos disponibles en el bucket S3

    Args:
        prefix: Prefijo para filtrar videos (ej: "Negotiaton/")

    Returns:
        Lista de videos disponibles
    """
    try:
        logger.info(f"Listando videos con prefijo: {prefix}")

        s3_client = get_s3_client()

        # Listar objetos en el bucket
        paginator = s3_client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=S3_BUCKET_VIDEOS, Prefix=prefix)

        videos = []
        for page in page_iterator:
            if "Contents" in page:
                for obj in page["Contents"]:
                    # Filtrar solo archivos de video
                    key = obj["Key"]
                    if key.lower().endswith(
                        (".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv")
                    ):
                        videos.append(
                            {
                                "path": key,
                                "filename": key.split("/")[-1],
                                "size": obj["Size"],
                                "size_mb": round(obj["Size"] / (1024 * 1024), 2),
                                "last_modified": obj["LastModified"].isoformat(),
                                "stream_url": f"/api/video/stream?video_path={key}",
                            }
                        )

        logger.info(f"Se encontraron {len(videos)} videos")
        return {"total_videos": len(videos), "videos": videos}

    except Exception as e:
        logger.error(f"Error al listar videos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al listar videos: {str(e)}")


def get_token(authorization: Optional[str], jwt_token: Optional[str]) -> str:
    """
    Extrae el token de autenticación dando prioridad al header. Si no está, lo busca en el body (o query).
    Se asegura de que el token incluya el prefijo "Bearer ".
    """
    token = None
    if authorization:
        token = authorization
    elif jwt_token:
        token = jwt_token if jwt_token.startswith("Bearer ") else "Bearer " + jwt_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT es requerido ya sea en el header o en el body.",
        )
    if not token.startswith("Bearer "):
        token = "Bearer " + token
    return token


async def upload_file_logic(file: UploadFile, authorization: str, jw_key: str):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
        )

    token = authorization[len("Bearer ") :]
    verification = Verification(jw_key)

    if not verification.is_valid(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid!",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_claims = json.loads(verification.get_claims(token))
    file_content = await file.read()

    response = business_logic(
        "put_file",
        {
            "file_content": file_content,
            "bucket_name": token_claims["bucket"],
            "key": token_claims["key"],
        },
    )

    if response.get("status_code") == 404:
        raise HTTPException(status_code=404, detail=response["error"])
    elif response.get("status_code") == 403:
        raise HTTPException(status_code=403, detail=response["error"])
    elif response.get("status_code") == 500:
        raise HTTPException(status_code=500, detail=response["error"])

    return {"message": "File uploaded successfully", "details": response["response"]}


def download_file_logic(authorization: str, jw_key: str):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
        )

    token = authorization[len("Bearer ") :]
    verification = Verification(jw_key)

    if not verification.is_valid(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid!",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"token is: {token}")
    token_claims = json.loads(verification.get_claims(token))
    logger.debug(f"token claims are: {token_claims}")
    files_data = token_claims.get("files")

    logger.debug(f"files_data in app.py is: {files_data}")
    if not files_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files data found in token.",
        )

    response = business_logic("get_file", {"files_data": files_data})

    if isinstance(response, StreamingResponse):
        return response
    elif "error" in response:
        if (
            response.get("status_code") == 404
            and response["error"] == "No files found to download."
        ):
            logger.warning(response["error"])
            raise HTTPException(
                status_code=response.get("status_code"), detail=response["error"]
            )
        elif response.get("status_code") == 206:
            logger.warning(response["error"])
            return response["response"]  # Continuar con el ZIP parcial
        else:
            raise HTTPException(
                status_code=response.get("status_code", 500), detail=response["error"]
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed to process files.",
        )


@app.put("/api/file")
async def upload_file(
    file: UploadFile = File(...),
    authorization: str = Header(...),
):
    return await upload_file_logic(file, authorization, jw_key)


@app.put("/transfers/api/file")
async def upload_file(
    file: UploadFile = File(...),
    authorization: str = Header(...),
):
    return await upload_file_logic(file, authorization, jw_key)


class TokenBody(BaseModel):
    jwt: str


# Download file
@app.get("/api/file")
async def download_file(
    authorization: str = Header(...),
):
    return download_file_logic(authorization, jw_key)


@app.get("/transfers/api/file")
async def download_file(
    authorization: str = Header(...),
):
    return download_file_logic(authorization, jw_key)


@app.post("/api/file")
async def download_file_post(
    token_body: TokenBody = Body(...),
    authorization: Optional[str] = Header(None),
):
    token = get_token(authorization, token_body.jwt)
    return download_file_logic(token, jw_key)


@app.post("/transfers/api/file")
async def download_file_post_transfers(
    token_body: TokenBody = Body(...),
    authorization: Optional[str] = Header(None),
):
    token = get_token(authorization, token_body.jwt)
    return download_file_logic(token, jw_key)
