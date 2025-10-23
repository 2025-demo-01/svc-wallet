FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml /app/
RUN pip install --upgrade pip && pip install setuptools wheel && pip install -e .
COPY src/ /app/src/
EXPOSE 8080
USER 65532:65532
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
