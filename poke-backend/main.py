import uvicorn
from server.api_v2 import app

def main():
    """Run the FastAPI server"""
    uvicorn.run(
        "server.api_v2:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
