from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from backend.app.db import init_db
from backend.app.routers import common, erp, crm, ehr, lms, documents, review_queue

# Load environment variables from backend/.env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Elyris API", lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(common.router)
app.include_router(erp.router)
app.include_router(crm.router)
app.include_router(ehr.router)
app.include_router(lms.router)
app.include_router(documents.router)
app.include_router(review_queue.router)
