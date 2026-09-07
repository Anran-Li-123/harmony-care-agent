from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings

settings = get_settings()
app = FastAPI(
    title="Harmony Care Agent Demo API",
    version="0.1.0",
    description="面向一老一小全场景看护的 AI Agent 编排与多设备协同演示。",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
