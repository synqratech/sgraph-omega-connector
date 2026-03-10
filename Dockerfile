FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY connector /app/connector

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

EXPOSE 18080

CMD ["uvicorn", "connector.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "18080"]
