from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controller import router as controller_router
from collections import deque

class AppState:
    broadcast_messages: deque[str]

class MyApp(FastAPI):
    state: "AppState"

app = MyApp(
    title="MyService API",
    description="REST API вместо WebSocket",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state = AppState()
app.state.broadcast_messages = deque(maxlen=16)

app.include_router(
    controller_router,
    prefix="/api",
    tags=["controller"],
)
