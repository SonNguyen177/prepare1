"""Entry point: FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.rest import router as rest_router
from .api.ws import router as ws_router
from .fix.server import start_fix_server

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start FIX server alongside FastAPI
    fix_server = await start_fix_server()
    logging.info("FIX 4.4 server started on port 9876")
    yield
    fix_server.close()
    await fix_server.wait_closed()


app = FastAPI(title="Matching Engine", version="0.1.0", lifespan=lifespan)

# CORS — allow admin and client UIs from any origin during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
