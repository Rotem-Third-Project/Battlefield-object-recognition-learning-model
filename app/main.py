from fastapi import FastAPI, Request, Form, WebSocket
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO
from pathlib import Path
from contextlib import asynccontextmanager
from utils.network import get_local_ip
from models.detect import process_image_array
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect
import websockets

import tensorflow as tf
import asyncio
import cv2
import numpy as np
import threading
import time
import os
import io
import base64
from PIL import Image
import torch
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

############################################################
# 🖼️ 이미지 처리 설정
############################################################

disp_x, disp_y = 2560, 1440
size_x, size_y = 2560, 1440  # 작업표시줄 높이(40px)를 제외한 전체화면 크기
DESIRED_SIZE = (size_x, size_y)

FPS = 120
INTERVAL = 1.0 / FPS

ROI = {
    'top':    0,  # 상단에서 시작
    'left':   0,  # 좌측에서 시작
    'width':  size_x,  # 전체 가로 크기
    'height': size_y  # 작업표시줄을 제외한 세로 크기
}

############################################################
# 🛰️ FastAPI 앱 & 리소스 초기화
############################################################

# 프로젝트 기본 경로
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
TEMP_PATH = BASE_DIR / "tmp"
CROSSHAIR_PATH = STATIC_DIR / "crosshair.png"
EFFICIENTNET_MODEL_PATH = BASE_DIR / "models" / "Efficientnet_weights" / "30000Efficient_weight.h5"

# FastAPI 앱 초기화
app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/tmp", StaticFiles(directory=TEMP_PATH), name="tmp")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GPU 설정
physical_devices = tf.config.list_physical_devices('GPU')
if physical_devices:
    tf.config.experimental.set_memory_growth(physical_devices[0], True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 모델 로드
yolo_model = YOLO(BASE_DIR / "models" / "yolo_weights" / "best.pt").to(device)
efficientnet_model = tf.keras.models.load_model(EFFICIENTNET_MODEL_PATH, compile=False)

############################################################
# 🧠 상태 변수들
############################################################

move_command_queue = []
action_command_queue = []
horizontal_command_queue = []
vertical_command_queue = []
bullet_logs = []
turret_pitch_angle = 0.0
gear_level = 2
gear_weights = {1: 0.3, 2: 0.6, 3: 1.0}
current_position = (60, 27)
last_turret_y = None
TARGET = 9.42  # 초기값

detected_objects = []

simulator_status = {
    "player_pos": {"x": 60, "y": 10, "z": 27.23},
    "player_speed": 0,
    "player_health": 100,
    "enemy_health": 100,
    "distance": 0,
    "is_info_received": False
}

def set_target(val: float):
    global TARGET
    TARGET = val

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
    global vertical_command_queue, horizontal_command_queue, last_turret_y, TARGET
    if last_turret_y is not None:
        error = TARGET - last_turret_y
        direction = "R" if error > 0 else "F"
        w = min(0.15 * abs(error), 1.0)
        vertical_command_queue.clear()
        vertical_command_queue.append({"turret": direction, "weight": w})
    if horizontal_command_queue:
        return horizontal_command_queue.pop(0)
    if vertical_command_queue:
        return vertical_command_queue.pop(0)
    return {"turret": " ", "weight": 0.0}

# 📌 객체 감지 결과 제공
@app.get("/get_detected_objects")
async def get_detected_objects():
    return {
        "roi": ROI,
        "objects": detected_objects
    }

# 📌 클라이언트 이미지로 객체 감지
@app.post("/detect_objects")
async def detect_objects_from_client(request: Request):
    try:
        data = await request.json()
        image_data = data.get('image').split(',')[1]
        img = Image.open(io.BytesIO(base64.b64decode(image_data)))
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        processed_img = await process_image_array(
            image=img_cv,
            yolo_model=yolo_model,
            efficientnet_model=efficientnet_model,
            crosshair_path=CROSSHAIR_PATH,
            tmp_path=TEMP_PATH,
            detected_objects=detected_objects,
            horizontal_command_queue=horizontal_command_queue,
            set_target_callback=set_target
        )
        
        _, buffer = cv2.imencode('.jpg', processed_img)
        processed_image_base64 = base64.b64encode(buffer).decode('utf-8')
        return {
            "objects": detected_objects,
            "processed_image": f"data:image/jpeg;base64,{processed_image_base64}"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "ERROR", "message": str(e)}
        )

# 📌 WebRTC WebSocket 엔드포인트
@app.websocket("/ws/video")
async def websocket_video(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            image_data = data.get('frame').split(',')[1]
            img = Image.open(io.BytesIO(base64.b64decode(image_data)))
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            processed_img = await process_image_array(
                image=img_cv,
                yolo_model=yolo_model,
                efficientnet_model=efficientnet_model,
                crosshair_path=CROSSHAIR_PATH,
                tmp_path=TEMP_PATH,
                detected_objects=detected_objects,
                horizontal_command_queue=horizontal_command_queue,
                set_target_callback=lambda x: globals().update(target=x)
            )
            
            _, buffer = cv2.imencode('.jpg', processed_img)
            processed_image_base64 = base64.b64encode(buffer).decode('utf-8')
            await websocket.send_json({
                "frame": f"data:image/jpeg;base64,{processed_image_base64}",
                "objects": detected_objects
            })
            await asyncio.sleep(INTERVAL)  # 120 FPS
    except WebSocketDisconnect:
        pass
    finally:
        if websocket.client_state == websockets.WebSocketState.CONNECTED:
            await websocket.close()

# 📌 시뮬레이터 시작 위치
@app.get("/init")
async def init():
    return {
        "startMode": "start",
        "blStartX": 60, "blStartY": 10, "blStartZ": 27.23,
        "rdStartX": 59, "rdStartY": 10, "rdStartZ": 280
    }

# 📌 상태 정보 제공
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
    global simulator_status, last_turret_y
    data = await request.json()
    last_turret_y = data.get("playerTurretY")
    simulator_status["player_pos"] = data.get("playerPos", simulator_status["player_pos"])
    simulator_status["player_speed"] = data.get("playerSpeed", simulator_status["player_speed"])
    simulator_status["player_health"] = data.get("playerHealth", simulator_status["player_health"])
    simulator_status["enemy_health"] = data.get("enemyHealth", simulator_status["enemy_health"])
    simulator_status["distance"] = data.get("distance", simulator_status["distance"])
    simulator_status["is_info_received"] = True
    simulator_status["last_info_time"] = time.time()
    return {"status": "success"}

# 📌 ROI 설정 API
@app.post("/set_roi")
async def set_roi(request: Request):
    global size_x, size_y, DESIRED_SIZE
    data = await request.json()
    ROI["top"] = int(data.get("top", ROI["top"]))
    ROI["left"] = int(data.get("left", ROI["left"]))
    ROI["width"] = int(data.get("width", ROI["width"]))
    ROI["height"] = int(data.get("height", ROI["height"]))

    size_x = ROI["width"]
    size_y = ROI["height"]
    DESIRED_SIZE = (size_x, size_y)

    return {"status": "success", "ROI": ROI}

############################################################
# 🔄 lifespan: 서버 시작 시 초기화
############################################################

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app.router.lifespan_context = lifespan

############################################################
# 🏁 서버 실행 설정
############################################################

SERVER_IP = get_local_ip()

def monitor_info_status():
    while True:
        last_time = simulator_status.get("last_info_time", 0)
        if time.time() - last_time > 3:
            simulator_status["is_info_received"] = False
        time.sleep(1)

threading.Thread(target=monitor_info_status, daemon=True).start()

if __name__ == "__main__":
    print("🖥️ 대시보드 접속 주소:")
    print(f"👉 http://{SERVER_IP}:8000/dashboard")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)