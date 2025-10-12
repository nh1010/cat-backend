import os

import uvicorn


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # Boot the FastAPI app defined in src/main.py
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=True)


