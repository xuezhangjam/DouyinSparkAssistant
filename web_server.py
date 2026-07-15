import os
import json
import asyncio
import subprocess
import sys
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_FILE = "clients.json"
LOG_FILE = "douyin_playwright.log"

@app.get("/api/clients")
async def get_clients():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/clients")
async def save_clients(request: Request):
    data = await request.json()
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return {"status": "ok"}

@app.post("/api/run")
async def run_client(request: Request):
    data = await request.json()
    cid = data.get("cid")
    
    env = os.environ.copy()
    env["DOUYIN_HEADLESS"] = "true"
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(base_dir, ".venv", "bin", "python")
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable
    if cid:
        subprocess.Popen([python_exe, os.path.join(base_dir, "runner.py"), cid], env=env)
        return {"status": "started", "cid": cid}
    else:
        subprocess.Popen([python_exe, os.path.join(base_dir, "scheduler.py")], env=env)
        return {"status": "started_all"}

@app.get("/api/logs")
async def get_logs():
    if not os.path.exists(LOG_FILE):
        return {"logs": ""}
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return {"logs": "".join(lines[-100:])}
    except Exception as e:
        return {"logs": f"Error reading logs: {e}"}

# Serve static files from Vue dist
dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_ui", "dist")
if os.path.exists(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
