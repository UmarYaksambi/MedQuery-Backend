from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import analytics, query, database, history

# Create tables on startup (good for dev, use Alembic for prod)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MedQuery API", version="1.0.0")

# CORS Configuration
origins = [
    "http://localhost:5173", # Vite default port
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(query.router)
app.include_router(analytics.router)
app.include_router(database.router)
app.include_router(history.router)

@app.get("/")
def read_root():
    return {"status": "online", "system": "MedQuery API"}