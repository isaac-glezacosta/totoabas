from fastapi import FastAPI
from app.routes.fish import router as fish_router
from app.routes.reports import router as reports_router

app = FastAPI(title="Water Quality API")

app.include_router(fish_router, tags=["Fish"])
app.include_router(reports_router, prefix="/reports", tags=["Reports"])


@app.get("/")
def root():
    return {"message": "API running"}