from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from models.detect import detect_target

import threading
import webbrowser
import os
import time
import cv2
import numpy as np
from pathlib import Path

# === 경로 설정 ===
BASE_DIR = Path(__file__).resolve().parent
CROSSHAIR_PATH = BASE_DIR / "static" / "img" / "crosshair.png"

# === 앱 초기화 ===
app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/tmp", StaticFiles(directory=BASE_DIR / "tmp"), name="tmp")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 전역 상태 ===
model = YOLO(BASE_DIR / "models" / "best.pt")
BARREL_X, BARREL_Y = 960, 883
TOLERANCE = 15

gear_level = 2
gear_weights = {1: 0.5, 2: 0.7, 3: 1.0}
move_command_queue = []
action_command_queue = []
current_position = (0, 0)

latest_frame = None
frame_lock = threading.Lock()
tracking_active = False
last_get_move_time = time.time()
last_move = {"move": "STOP", "weight": 0.0}

@app.on_event("startup")
async def startup_event():
    move_command_queue.clear()
    action_command_queue.clear()

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.post("/input_key")
async def input_key(key: str = Form(...)):
    global gear_level
    if key in ["W", "A", "S", "D"]:
        move_command_queue.append({"move": key, "weight": gear_weights[gear_level]})
    elif key == "P" and gear_level < 3:
        gear_level += 1
    elif key == "L" and gear_level > 1:
        gear_level -= 1
    return {"gear": gear_level}

@app.get("/get_move")
async def get_move():
    global tracking_active, last_get_move_time, last_move

    now = time.time()
    time_diff = now - last_get_move_time
    last_get_move_time = now

    if not tracking_active:
        print("🟢 트래킹 시작됨 → 명령 큐 초기화")
        move_command_queue.clear()
        action_command_queue.clear()
        tracking_active = True

    if time_diff > 3:
        print("🔴 트래킹 중단 감지")
        tracking_active = False

    if move_command_queue:
        last_move = move_command_queue.pop(0)
        return last_move

    if last_move["move"] in ["W", "A", "S", "D"]:
        return {"move": last_move["move"], "weight": max(0.2, last_move["weight"] * 0.8)}

    return {"move": "DECELERATE", "weight": 0.2}

@app.get("/get_action")
async def get_action():
    if action_command_queue:
        return action_command_queue.pop(0)
    return {"turret": " ", "weight": 0.0}

@app.post("/send_action")
async def send_action(turret: str = Form(...), weight: float = Form(...)):
    action_command_queue.append({"turret": turret, "weight": weight})
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/detect")
async def detect_endpoint(image: UploadFile = File(...)):
    return await detect_target(
        image=image,
        model=model,
        action_command_queue=action_command_queue,
        BARREL_X=BARREL_X,
        BARREL_Y=BARREL_Y,
        TOLERANCE=TOLERANCE,
        CROSSHAIR_PATH=CROSSHAIR_PATH,
        latest_frame=latest_frame,
        frame_lock=frame_lock
    )

@app.get("/video_feed")
def video_feed():
    def generate():
        while True:
            with frame_lock:
                frame = latest_frame.copy() if latest_frame is not None else None
            if frame is not None:
                _, buffer = cv2.imencode(".jpg", frame)
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            time.sleep(0.016)
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/status")
async def status():
    return {
        "gear_level": gear_level,
        "current_position": current_position,
        "action_queue_len": len(action_command_queue)
    }

@app.post("/update_position")
async def update_position(request: Request):
    global current_position
    data = await request.json()
    try:
        x, y, z = map(float, data["position"].split(","))
        current_position = (int(x), int(z))
        return {"status": "OK", "current_position": current_position}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": str(e)})

@app.post("/update_bullet")
async def update_bullet(request: Request):
    data = await request.json()
    print(f"Bullet Impact at X={data.get('x')}, Y={data.get('y')}, Z={data.get('z')}, Target={data.get('hit')}")
    return {"status": "OK", "message": "Bullet impact data received"}

@app.post("/set_destination")
async def set_destination(request: Request):
    data = await request.json()
    try:
        x, y, z = map(float, data["destination"].split(","))
        return {"status": "OK", "destination": {"x": x, "y": y, "z": z}}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": f"Invalid format: {str(e)}"})

@app.get("/init")
async def init():
    return {
        "startMode": "start",
        "blStartX": 60, "blStartY": 10, "blStartZ": 27.23,
        "rdStartX": 59, "rdStartY": 10, "rdStartZ": 280
    }

if __name__ == "__main__":
    if os.environ.get("RUN_MAIN") != "true":
        threading.Thread(target=lambda: webbrowser.open("http://localhost:5000/dashboard")).start()
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True, access_log=False)