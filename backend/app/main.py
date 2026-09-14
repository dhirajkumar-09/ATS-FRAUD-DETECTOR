"""
main.py — FastAPI application entrypoint
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_TITLE, APP_VERSION
from app.database import Base, engine, init_db
from app.routers import auth, report, scan

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Create DB tables & ensure schema ──────────────────────────────────────────
init_db()
logger.info("Database tables and schema ensured.")

# ── FastAPI app ───────────────────────────────────────────────────────────────

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request

app = FastAPI(

    title=APP_TITLE,
    version=APP_VERSION,
    description=(
        "Recruiter-facing tool that scans resume PDFs for ATS manipulation techniques, "
        "produces fraud reports, visual heatmaps, and clean job-fit scores."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow cross-origin requests from Vercel, localhost, and other environments
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ats-fraud-detector.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error processing %s: %s", request.url.path, exc)
    origin = request.headers.get("origin") or "*"
    headers = {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
        headers=headers,
    )

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(scan.router)
app.include_router(report.router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "app": APP_TITLE, "version": APP_VERSION}


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={'detail': exc.errors()}, headers={'Access-Control-Allow-Origin': '*'})




from fastapi.exceptions import HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail}, headers={'Access-Control-Allow-Origin': '*'})

