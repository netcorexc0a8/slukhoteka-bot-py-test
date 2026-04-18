from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models import user, schedule, invite, client
from app.api import auth, schedule as schedule_api, users, export, sync, backup, client as client_api

app = FastAPI(title="Slukhoteka Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

user.Base.metadata.create_all(bind=engine)
schedule.Base.metadata.create_all(bind=engine)
invite.Base.metadata.create_all(bind=engine)
client.Base.metadata.create_all(bind=engine)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(schedule_api.router, prefix="/api/v1/schedules", tags=["schedules"])
app.include_router(client_api.router, prefix="/api/v1/clients", tags=["clients"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(export.router, prefix="/api/v1/export", tags=["export"])
app.include_router(sync.router, prefix="/api/v1/sync", tags=["sync"])
app.include_router(backup.router, prefix="/api/v1/backup", tags=["backup"])

@app.get("/")
def read_root():
    return {"message": "Slukhoteka Backend API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
