import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .routes.api import router as api_router
from .services.embeddings import get_embedding_service
from .services.vector_store import get_vector_store
from .services.document_manager import get_document_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("rag_app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing macOS RAG Assistant backend...")
    # Initialize core services on startup
    get_document_manager()
    get_vector_store()
    logger.info(f"RAG Backend running with chunk_size={settings.CHUNK_SIZE}, top_k={settings.TOP_K}")
    yield
    logger.info("RAG Backend shutting down.")

app = FastAPI(
    title="macOS RAG Research Workspace API",
    description="Full-featured local Retrieval-Augmented Generation API for macOS",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Enable CORS for React/Vite development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global safe exception handler: ensures stack traces never leak to client
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred while processing your request. Please check server logs."}
    )

# Include router at both root and /api for maximum compatibility
app.include_router(api_router, prefix="")
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
