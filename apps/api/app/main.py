from fastapi import FastAPI

from .routers import router

app = FastAPI(title="OpenAgentSearch API", version="0.1.0")
app.include_router(router)
