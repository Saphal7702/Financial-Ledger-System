from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .routers import health, accounts, transactions, admin
from .db.db import init_db

print("Welcome to the Ledger System!")

app = FastAPI(title="Ledger System")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(health.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(admin.router)