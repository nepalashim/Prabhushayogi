"""Pydantic request models for the FastAPI app."""

from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str
