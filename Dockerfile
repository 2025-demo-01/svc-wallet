FROM python:3.11-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app /app

FROM python:3.11-slim
WORKDIR /app
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /app /app
ENV PORT=8081
EXPOSE 8081
CMD ["gunicorn", "-b", "0.0.0.0:8081", "main:app", "--workers", "2", "--threads", "4"]
