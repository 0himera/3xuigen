import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 8000))
    
    # Development environment check
    is_dev = os.getenv("ENV", "production").lower() == "development"
    
    # Start the FastAPI application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=is_dev
    ) 