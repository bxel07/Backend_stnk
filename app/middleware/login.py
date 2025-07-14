from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.auth import verify_access_token

class LoginMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Izinkan semua request OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        public_paths = [
            "/login", "/register",
            "/docs", "/redoc", "/openapi.json",
            "/api/docs", "/api/openapi.json",
            "/storage/"
        ]

        # Gunakan startswith agar bisa akses file seperti /storage/foto.jpg
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header missing"}
            )

        token = auth_header.split(" ")[-1]
        payload = verify_access_token(token)
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"}
            )

        request.state.user = payload
        return await call_next(request)
