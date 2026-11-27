"""Router utama API v1 yang menggabungkan 9 modul endpoint DSS."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ahp,
    auth,
    history,
    map_view,
    observations,
    segments,
    topsis,
    users,
    worklists,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(segments.router)
api_router.include_router(observations.router)
api_router.include_router(ahp.router)
api_router.include_router(topsis.router)
api_router.include_router(map_view.router)
api_router.include_router(worklists.router)
api_router.include_router(history.router)
