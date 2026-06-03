from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import create_db_and_tables
from rag.ingest import ingest_policy
from routers import appeals, claims, health, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    try:
        ingest_policy()
    except Exception as e:
        print(f"[WARNING] RAG ingestion failed: {e}")
    yield


app = FastAPI(
    title="Plum OPD Claims API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(claims.router)
app.include_router(appeals.router)
app.include_router(admin.router)
