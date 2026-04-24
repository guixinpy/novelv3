#!/usr/bin/env python3
import webbrowser

import uvicorn

from app.main import app

if __name__ == "__main__":
    webbrowser.open("http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
