from fastapi import FastAPI

from app.routers import auth, bookings, addresses, family, services, users

app = FastAPI(title="Hospital Home-Care API", version="1.0.0")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(family.router)
app.include_router(addresses.router)
app.include_router(services.router)
app.include_router(bookings.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
