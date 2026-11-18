import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import Config
from routes import routers
from services.fcm_service import FcmService
from utils.response import error_response, success_response


def create_app(_test_config=None) -> FastAPI:
    api = FastAPI(title="EcoRuta API REST", version="1.0.0")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    os.makedirs(os.path.join(Config.UPLOAD_DIR, "incidencias"), exist_ok=True)
    for router in routers:
        api.include_router(router)

    web_dir = os.path.join(os.path.dirname(__file__), "supervision-web")
    api.mount("/supervision-assets", StaticFiles(directory=web_dir), name="supervision-assets")

    @api.middleware("http")
    async def fcm_post_commit(request: Request, call_next):
        response = await call_next(request)
        if request.method in {"POST", "PUT", "DELETE"} and response.status_code < 400:
            FcmService().despachar_pendientes()
        return response

    @api.exception_handler(HTTPException)
    @api.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc):
        return error_response(str(exc.detail), exc.status_code)

    @api.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        return error_response("Solicitud inválida", 422, exc.errors())

    @api.exception_handler(Exception)
    async def internal_error(_request: Request, exc: Exception):
        logging.exception("Error no controlado", exc_info=exc)
        return error_response("Error interno del servidor", 500)

    @api.get("/", include_in_schema=False)
    def health(request: Request):
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url="/supervision")
        return success_response(
            {"app": "EcoRuta API REST", "framework": "FastAPI"}, "API disponible"
        )

    @api.get("/supervision", include_in_schema=False)
    @api.get("/supervision/", include_in_schema=False)
    def supervision():
        return FileResponse(
            os.path.join(web_dir, "index.html"),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    return api


app = create_app()


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    uvicorn.run("app:app", host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")), reload=False)
