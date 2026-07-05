from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time

app = FastAPI()

EMAIL = "24f2000931@ds.study.iitm.ac.in"

# Allowed origins
allowed_origins = [
    "https://app-oy207o.example.com",
    "https://exam.sanand.workers.dev",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter configuration
LIMIT = 11
WINDOW = 10  # seconds

# client_id -> list of request timestamps
clients = {}


@app.middleware("http")
async def request_context(request: Request, call_next):
    # Use incoming request ID if present
    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    # Always echo request ID in response header
    response.headers["X-Request-ID"] = request_id

    return response


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_id = request.headers.get("X-Client-Id", "anonymous")
    now = time.time()

    if client_id not in clients:
        clients[client_id] = []

    # Remove timestamps older than WINDOW seconds
    clients[client_id] = [
        t for t in clients[client_id]
        if now - t < WINDOW
    ]

    # Reject if limit exceeded
    if len(clients[client_id]) >= LIMIT:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )
        response.headers["X-Request-ID"] = getattr(
            request.state,
            "request_id",
            str(uuid.uuid4())
        )
        return response

    clients[client_id].append(now)

    return await call_next(request)


@app.options("/ping")
async def options_ping():
    return Response(status_code=200)


@app.get("/ping")
async def ping(request: Request, response: Response):
    # Echo request ID in response header
    response.headers["X-Request-ID"] = request.state.request_id

    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }


@app.get("/")
async def root():
    return {"status": "ok"}
