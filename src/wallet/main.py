import os
import asyncio
from fastapi import FastAPI
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from wallet.config import Config
from wallet.db import init_pool, close_pool
from wallet.consumer import run_consumer

app = FastAPI(title="svc-wallet", version="0.1.0")

@app.on_event("startup")
async def startup():
    await init_pool(Config.PG_DSN)
    # 백그라운드로 Kafka consumer 실행
    app.state.consumer_task = asyncio.create_task(run_consumer())

@app.on_event("shutdown")
async def shutdown():
    app.state.consumer_task.cancel()
    await close_pool()

@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/readyz")
async def readyz():
    # 간단 체크: DB 핑이나 consumer_task 상태 확인도 가능
    return {"status": "ready", "env": Config.APP_ENV}
