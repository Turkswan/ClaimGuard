# Image for batch ML jobs: training and drift checks.
FROM public.ecr.aws/docker/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MLFLOW_DISABLE_AGENT_HINT=1

WORKDIR /app

# 1. Dependencies first: this layer is cached until requirements change.
COPY requirements/train.txt requirements/train.txt
RUN pip install -r requirements/train.txt

# 2. Our code last: it changes most often, so only this layer rebuilds.
COPY pyproject.toml .
COPY src ./src
RUN pip install --no-deps .

# 3. Never run as root inside the container.
RUN useradd --create-home --uid 10001 app
USER 10001

CMD ["python", "-m", "claimguard.train", "--help"]
