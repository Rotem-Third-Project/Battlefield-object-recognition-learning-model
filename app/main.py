from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from utils.network import get_local_ip
from models.detect import process_image_array
from fastapi.middleware.cors import CORSMiddleware

import tensorflow as tf
import asyncio
import mss
import cv2
import numpy as np
import threading
import time
import os

############################################################
# 🖼️ 이미지 처리 설정
############################################################

disp_x, disp_y = 2560, 1440
size_x, size_y = 1900, 1020
DESIRED_SIZE = (size_x, size_y)

FPS = 120
INTERVAL = 1.0 / FPS

ROI = {
    'top':    int((disp_y - size_y) // 2),
    'left':   int((disp_x - size_x) // 2),
    'width':  size_x,
    'height': size_y
}

capture_q = asyncio.Queue(maxsize=2)
stream_q = asyncio.Queue(maxsize=2)

############################################################
# 🛰️ FastAPI 앱 & 리소스 초기화
############################################################

BASE_DIR = Path(__file__).resolve().parent
CROSSHAIR_PATH = BASE_DIR / "static" / "img" / "crosshair.png"
EFFICIENTNET_MODEL_PATH = BASE_DIR / "models" / "Efficientnet_weights" / "30000Efficient_weight.h5"  # EfficientNet 모델 경로

app = FastAPI()

############################################################
# 프론트엔드 리소스 설정
############################################################
# CORS 설정 (vue.js와 통신을 위해)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # 개발 중 전체 허용
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

yolo_model = YOLO(BASE_DIR / "models" / "yolo_weights" / "best.pt")
efficientnet_model = tf.keras.models.load_model(EFFICIENTNET_MODEL_PATH, compile=False)

############################################################
# 🧠 상태 변수들
############################################################

move_command_queue = []
action_command_queue = []
bullet_logs = []
turret_pitch_angle = 0.0
gear_level = 2
gear_weights = {1: 0.3, 2: 0.6, 3: 1.0}
current_position = (60, 27)

detected_objects = []

simulator_status = {
    "player_pos": {"x": 60, "y": 10, "z": 27.23},
    "player_speed": 0,
    "player_health": 100,
    "enemy_health": 100,
    "distance": 0,
    "is_info_received": False
}

############################################################
# 🌐 FastAPI 엔드포인트
############################################################

# 📌 대시보드 렌더
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# 📌 키 입력 처리
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

# 📌 이동 명령 요청
@app.get("/get_move")
async def get_move():
    if move_command_queue:
        return move_command_queue.pop(0)
    return {"move": "STOP", "weight": 1.0}

# 📌 포탑 조작 명령 요청
@app.get("/get_action")
async def get_action():
    if action_command_queue:
        return action_command_queue.pop(0)
    return {"turret": " ", "weight": 0.0}

# 📌 객체 감지 결과 제공
@app.get("/get_detected_objects")
async def get_detected_objects():
    return {
        "roi": ROI,
        "objects": detected_objects
    }

# 📌 시뮬레이터 시작 위치
@app.get("/init")
async def init():
    return {
        "startMode": "start",
        "blStartX": 60, "blStartY": 10, "blStartZ": 27.23,
        "rdStartX": 59, "rdStartY": 10, "rdStartZ": 280
    }

# 📌 상태 정보 제공 (HUD.js가 사용)
@app.get("/get_status")
async def get_status():
    simulator_status["turret_pitch"] = turret_pitch_angle
    return {
        **simulator_status,
        "ROI": ROI,
        "size_x": size_x,
        "size_y": size_y
    }

# 📌 포탄 충돌 정보 수신
@app.post("/update_bullet")
async def update_bullet(request: Request):
    data = await request.json()
    impact_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log_msg = f"[{impact_time}] 💥 Impact at X={data.get('x')}, Y={data.get('y')}, Z={data.get('z')}, Target={data.get('hit')}"
    bullet_logs.append(log_msg)
    return {"status": "OK"}

# 📌 로그 요청
@app.get("/get_logs")
async def get_logs():
    return {"logs": bullet_logs[-20:]}

# 📌 시뮬레이터 정보 수신
@app.post("/info")
async def receive_simulator_info(request: Request):
    global simulator_status
    try:
        data = await request.json()

        simulator_status["player_pos"] = data.get("playerPos", simulator_status["player_pos"])
        simulator_status["player_speed"] = data.get("playerSpeed", simulator_status["player_speed"])
        simulator_status["player_health"] = data.get("playerHealth", simulator_status["player_health"])
        simulator_status["enemy_health"] = data.get("enemyHealth", simulator_status["enemy_health"])
        simulator_status["distance"] = data.get("distance", simulator_status["distance"])
        simulator_status["is_info_received"] = True
        simulator_status["last_info_time"] = time.time()

        return {"status": "success", "message": "Simulator info updated"}

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

def monitor_info_status():
    while True:
        last_time = simulator_status.get("last_info_time", 0)
        if time.time() - last_time > 3:
            simulator_status["is_info_received"] = False
        time.sleep(1)

threading.Thread(target=monitor_info_status, daemon=True).start()

if __name__ == "__main__":
    if os.environ.get("RUN_MAIN") != "true":
        print("🖥️ 대시보드 접속 주소:")
        print(f"👉 {DASHBOARD_URL}")
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True, access_log=False)

