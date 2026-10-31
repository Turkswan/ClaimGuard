# MLflow tracking server + model registry. boto3 lets it store artefacts in S3.
FROM public.ecr.aws/docker/library/python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 MLFLOW_DISABLE_AGENT_HINT=1

RUN pip install "mlflow>=3.5,<4" boto3

# /mlflow holds the SQLite database. Owned by our non-root user.
RUN useradd --uid 10001 mlflow && mkdir /mlflow && chown 10001 /mlflow
USER 10001
WORKDIR /mlflow

EXPOSE 5000
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
