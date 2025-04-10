from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import firewall, reality, xui
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Config Generator API",
    description="API for generating configurations, managing users and firewall rules",
    version="0.1.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
# app.include_router(configs.router, prefix="/api/configs", tags=["Configurations"])
app.include_router(firewall.router, prefix="/api/firewall", tags=["Firewall"])
app.include_router(reality.router, prefix="/api/reality", tags=["Reality"])
app.include_router(xui.router, prefix="/api/xui", tags=["3xui"])

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to Config Generator API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=os.getenv("ENV", "production").lower() == "development") 