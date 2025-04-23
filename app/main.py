from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import torch
from ultralytics import YOLO
import shutil
import json
import threading
import webbrowser
import requests
import os
import time
import asyncio
from pathlib import Path
import cv2
import numpy as np

# 📌 경로 기본 설정
BASE_DIR = Path(__file__).resolve().parent
TMP_PATH = BASE_DIR / "tmp" / "temp_image.jpg"
CROSSHAIR_PATH = BASE_DIR / "static" / "img" / "crosshair.png"

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/tmp", StaticFiles(directory=BASE_DIR / "tmp"), name="tmp")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

model = YOLO(BASE_DIR / "models" / "best.pt")

move_command_queue = []
action_command_queue = []
gear_level = 2
gear_weights = {1: 0.3, 2: 0.6, 3: 1.0}
current_position = (0, 0)

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

@app.post("/send_move")
async def send_move(move: str = Form(...), weight: float = Form(...)):
    move_command_queue.append({"move": move, "weight": weight})
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/send_action")
async def send_action(turret: str = Form(...), weight: float = Form(...)):
    action_command_queue.append({"turret": turret, "weight": weight})
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/get_move")
async def get_move():
    if move_command_queue:
        return move_command_queue.pop(0)
    return {"move": "STOP", "weight": 1.0}

@app.get("/get_action")
async def get_action():
    if action_command_queue:
        return action_command_queue.pop(0)
    return {"turret": "", "weight": 0.0}

@app.post("/detect")
async def detect(image: UploadFile = File(...)):
    with open(TMP_PATH, "wb") as f:
        shutil.copyfileobj(image.file, f)

    try:
        results = list(model(str(TMP_PATH), verbose=False, stream=True))
        detections = results[0].boxes.data.cpu().numpy()
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "ERROR", "message": str(e)})

    target_classes = {0: "person", 2: "car", 7: "truck", 15: "rock"}
    filtered_results = []

    img_cv = cv2.imread(str(TMP_PATH))
    crosshair = cv2.imread(str(CROSSHAIR_PATH), cv2.IMREAD_UNCHANGED)
    crosshair = cv2.resize(crosshair, (60, 60), interpolation=cv2.INTER_AREA)

    for box in detections:
        class_id = int(box[5])
        if class_id in target_classes:
            x1, y1, x2, y2 = map(int, box[:4])
            confidence = float(box[4])
            class_name = target_classes[class_id]

            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            h, w = crosshair.shape[:2]
            x_offset = max(cx - w // 2, 0)
            y_offset = max(cy - h // 2, 0)

            for c in range(3):
                alpha_s = crosshair[:, :, 3] / 255.0
                alpha_l = 1.0 - alpha_s
                for i in range(h):
                    for j in range(w):
                        if y_offset + i < img_cv.shape[0] and x_offset + j < img_cv.shape[1]:
                            img_cv[y_offset + i, x_offset + j, c] = (
                                alpha_s[i, j] * crosshair[i, j, c] +
                                alpha_l[i, j] * img_cv[y_offset + i, x_offset + j, c]
                            )

            filtered_results.append({
                'className': class_name,
                'bbox': [x1, y1, x2, y2],
                'confidence': confidence
            })

    # ✅ 이미지 출력용만 리사이즈 (예: 60%)
    resize_ratio = 0.6
    resized_img = cv2.resize(img_cv, (0, 0), fx=resize_ratio, fy=resize_ratio)
    cv2.imwrite(str(TMP_PATH), resized_img)

    return JSONResponse(content=filtered_results)

@app.post("/update_position")
async def update_position(request: Request):
    global current_position
    data = await request.json()
    if "position" not in data:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": "Missing position data"})

    try:
        x, y, z = map(float, data["position"].split(","))
        current_position = (int(x), int(z))
        return {"status": "OK", "current_position": current_position}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": str(e)})

@app.get("/check_new_frame")
async def check_new_frame(last_mtime: float = 0):
    MAX_WAIT_TIME = 5.0
    CHECK_INTERVAL = 0.3
    start_time = time.time()

    while True:
        if not TMP_PATH.exists():
            return {"updated": False, "mtime": 0}

        mtime = os.path.getmtime(TMP_PATH)
        if mtime > last_mtime:
            return {"updated": True, "mtime": mtime}

        if time.time() - start_time > MAX_WAIT_TIME:
            return {"updated": False, "mtime": mtime}

        await asyncio.sleep(CHECK_INTERVAL)

@app.post("/update_bullet")
async def update_bullet(request: Request):
    data = await request.json()
    print(f"💥 Bullet Impact at X={data.get('x')}, Y={data.get('y')}, Z={data.get('z')}, Target={data.get('hit')}")
    return {"status": "OK", "message": "Bullet impact data received"}

@app.post("/set_destination")
async def set_destination(request: Request):
    data = await request.json()
    if "destination" not in data:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": "Missing destination data"})
    try:
        x, y, z = map(float, data["destination"].split(","))
        return {"status": "OK", "destination": {"x": x, "y": y, "z": z}}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": f"Invalid format: {str(e)}"})

@app.post("/update_obstacle")
async def update_obstacle(request: Request):
    data = await request.json()
    print("🪨 Obstacle Data:", data)
    return {"status": "success", "message": "Obstacle data received"}

@app.get("/init")
async def init():
    return {
        "startMode": "start",
        "blStartX": 60,
        "blStartY": 10,
        "blStartZ": 27.23,
        "rdStartX": 59,
        "rdStartY": 10,
        "rdStartZ": 280
    }

@app.get("/start")
async def start():
    return {"control": ""}

def open_browser():
    time.sleep(1)
    webbrowser.open("http://localhost:5000/dashboard")

if __name__ == "__main__":
    if os.environ.get("RUN_MAIN") != "true":
        threading.Thread(target=open_browser).start()

    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True, access_log=False)
