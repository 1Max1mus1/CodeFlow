from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import project, session, operation, proxy


def create_app() -> FastAPI:
    app = FastAPI(
        title="CodeFlow API",
        description="Parse Python codebases into interactive directed graphs.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(project.router, prefix="/project", tags=["Project"])
    app.include_router(session.router, prefix="/session", tags=["Session"])
    app.include_router(operation.router, prefix="/operation", tags=["Operation"])
    app.include_router(proxy.router, prefix="/proxy", tags=["Proxy"])

    return app
