from __future__ import annotations

from fastapi import FastAPI

from recipe_quality.api.routes import router

app = FastAPI(title="Recipe Quality API", version="0.1.0")
app.include_router(router)

