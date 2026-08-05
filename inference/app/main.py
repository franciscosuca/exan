"""Exan Backend - AI-powered exam scanning and grading API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import batch, exams, providers
from .providers.registry import get_provider

what

app = FastAPI(title="Exan API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(providers.router)
app.include_router(exams.router)
app.include_router(batch.router)
