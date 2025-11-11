from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from servers.routes import router


app = FastAPI(title="Incident Tracker (Modular In-memory)")


app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)


app.include_router(router)