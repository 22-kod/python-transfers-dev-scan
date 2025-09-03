import os

FORMAT_DATE = "%Y-%m-%d %H:%M:%S"
TIME_ZONE = os.environ.get("TIME_ZONE", "America/Mexico_City")

REGION_NAME = os.environ.get("REGION_NAME", "us-east-1")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "secretsmanager")

TIMEOUT = int(os.environ.get("TIMEOUT", "60"))
KAFKA_HOST = os.environ.get("KAFKA_HOST", "localhost:9093")
KAFKA_PROTOCOL = os.environ.get("KAFKA_PROTOCOL", "PLAINTEXT")

ISSUER = os.environ.get("ISSUER", "https://dev-89645961.okta.com")
CLIENT_ID = os.environ.get("CLIENT_ID", "0oabfj1b1hAec7oHg5d7")
AUDIENCE = os.environ.get("AUDIENCE", "0oabfj1b1hAec7oHg5d7")

PATH_SECRET_BUS = os.environ.get("PATH_SECRET_BUS", "dev/app/bus")
PATH_SECRET_FRONT = os.environ.get("PATH_SECRET_FRONT", "dev/app/frontend")
