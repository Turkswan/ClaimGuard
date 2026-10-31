# Image for the online scoring API.
FROM public.ecr.aws/docker/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MLFLOW_DISABLE_AGENT_HINT=1 \
    HOME=/tmp

WORKDIR /app

COPY requirements/ requirements/
RUN pip install -r requirements/serve.txt

COPY pyproject.toml .
COPY src ./src
RUN pip install --no-deps .
COPY serving ./serving

RUN useradd --uid 10001 app
USER 10001

EXPOSE 8000
CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8000"]
