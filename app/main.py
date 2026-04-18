from fastapi import FastAPI
from app.routes.measurements import router as measurements_router
from app.routes.reports import router as reports_router

app = FastAPI(title="Water Quality API")

app.include_router(measurements_router, prefix="/measurements", tags=["Measurements"])
app.include_router(reports_router, prefix="/reports", tags=["Reports"])


@app.get("/")
def root():
    return {"message": "API running"}