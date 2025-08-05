from fastapi import FastAPI
from controller import router as controller_router

app = FastAPI()
app.include_router(controller_router)
