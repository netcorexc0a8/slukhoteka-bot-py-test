from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Импортируем все модели чтобы Base.metadata знал о них (на случай fallback create_all)
from app import models  # noqa: F401

from app.api import (
    auth, users, export, sync, backup, client as client_api,
    service as service_api,
    subscription as subscription_api,
    booking as booking_api,
    group as group_api,
)

app = FastAPI(title="Slukhoteka Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Схема БД управляется миграциями (entrypoint.sh -> migrations/migrate.py).
# Base.metadata.create_all НЕ вызываем — иначе SQLAlchemy попытается создать
# таблицы со своим представлением о схеме, что может расходиться с миграциями.

app.include_router(auth.router,            prefix="/api/v1/auth",          tags=["auth"])
app.include_router(client_api.router,      prefix="/api/v1/clients",       tags=["clients"])
app.include_router(service_api.router,     prefix="/api/v1/services",      tags=["services"])
app.include_router(subscription_api.router, prefix="/api/v1/subscriptions", tags=["subscriptions"])
app.include_router(booking_api.router,     prefix="/api/v1/bookings",      tags=["bookings"])
app.include_router(group_api.router,       prefix="/api/v1/groups",        tags=["groups"])
app.include_router(users.router,           prefix="/api/v1/users",         tags=["users"])
app.include_router(export.router,          prefix="/api/v1/export",        tags=["export"])
app.include_router(sync.router,            prefix="/api/v1/sync",          tags=["sync"])
app.include_router(backup.router,          prefix="/api/v1/backup",        tags=["backup"])


@app.get("/")
def read_root():
    return {"message": "Slukhoteka Backend API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
