FROM 606212394872.dkr.ecr.us-east-1.amazonaws.com/ds-python:3.13-slim-custom AS base

WORKDIR /app

RUN useradd -m nonrootuser

RUN mkdir -p /app /home/nonrootuser/.aws && \
    chown -R nonrootuser:nonrootuser /app /home/nonrootuser/.aws

ARG VERSION
ARG BUILD_DATE
ARG GIT_COMMIT
ENV VERSION=${VERSION}
ENV BUILD_DATE=${BUILD_DATE}
ENV GIT_COMMIT=${GIT_COMMIT}

COPY requirements.txt ./

RUN --mount=type=secret,id=aws_access_key_id \
    --mount=type=secret,id=aws_secret_access_key \
    --mount=type=secret,id=aws_session_token \
    bash -c 'export AWS_ACCESS_KEY_ID=$(cat /run/secrets/aws_access_key_id) && \
    export AWS_SECRET_ACCESS_KEY=$(cat /run/secrets/aws_secret_access_key) && \
    export AWS_SESSION_TOKEN=$(cat /run/secrets/aws_session_token) && \
    aws codeartifact login --tool pip \
    --repository ds-copan-artifact \
    --domain dralmey \
    --domain-owner 606212394872 \
    --region us-east-1 && \
    pip install --no-cache-dir -r requirements.txt'

FROM 606212394872.dkr.ecr.us-east-1.amazonaws.com/ds-python:3.13-slim  AS final

RUN useradd -m nonrootuser

ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

WORKDIR /app
COPY --from=base /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY --from=base /usr/local/bin/uvicorn /usr/local/bin/uvicorn

RUN pip install uvicorn

EXPOSE 8080

COPY ./src /app

COPY global-bundle.pem /app/global-bundle.pem

RUN chown -R nonrootuser:nonrootuser /app
USER nonrootuser

# Comando para ejecutar FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4", "--log-level", "debug"]
