from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .db import Base, engine
from .routers import answers, auth, questions


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fine while the schema is young. Swap for Alembic migrations before deploying.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Askwell", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(questions.router)
app.include_router(answers.router)


@app.get("/health")
def health():
    return {"status": "ok"}
