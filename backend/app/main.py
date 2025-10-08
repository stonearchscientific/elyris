from fastapi import FastAPI
from contextlib import asynccontextmanager
from backend.app.db import init_db
from backend.app.routers import common, erp, crm, ehr, lms

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Elyris API", lifespan=lifespan)

app.include_router(common.router)
app.include_router(erp.router)
app.include_router(crm.router)
app.include_router(ehr.router)
app.include_router(lms.router)
