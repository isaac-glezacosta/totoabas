from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.fish import router as fish_router
from app.routes.reports import router as reports_router

app = FastAPI(title="Totoabas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fish_router, tags=["Fish"])
app.include_router(reports_router, prefix="/reports", tags=["Reports"])


@app.get("/")
def root():
    return {"message": "API running"}