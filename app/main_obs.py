import cv2
import numpy as np
import tensorflow as tf
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from pathlib import Path
from models.detect import process_image_array
from pathlib import Path
from fastapi import Form
from fastapi import FastAPI, Request
import asyncio
import time

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 기본 경로 설정
BASE_DIR = Path(__file__).resolve().parent
CROSSHAIR_PATH = BASE_DIR / "static" / "img" / "crosshair.png"
TEMP_PATH = BASE_DIR / "tmp" / "temp.jpg"
DESIRED_SIZE = (1280, 720)

horizontal_command_queue = []
vertical_command_queue = []
last_turret_y = None
TARGET = 9.42  # 기본 포탑 목표 각도

# 모델 로드
yolo_model = YOLO(BASE_DIR / "models/yolo_weights/best.pt")
efficientnet_model = tf.keras.models.load_model(
    BASE_DIR / "models/Efficientnet_weights/30000Efficient_weight.h5",
    compile=False
)

# OBS 가상카메라 연결 (보통 0 또는 1)
cap = cv2.VideoCapture(0)

# MJPEG 생성 비동기 루프
async def generate_yolo_mjpeg():
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # 객체 인식
        arr = await process_image_array(
            image=frame,
            yolo_model=yolo_model,
            efficientnet_model=efficientnet_model,
            crosshair_path=CROSSHAIR_PATH,
            tmp_path=TEMP_PATH,
            detected_objects=detected_objects,  # 로그 저장용 리스트
            horizontal_command_queue=[],  # 무시 가능
            set_target_callback=lambda v: None
        )

        # ✅ 여기서 리스트 로그 찍기
        print(f"🧠 현재 감지된 객체 수: {len(detected_objects)}")
        for obj in detected_objects:
            print(f" - {obj}")

        small = cv2.resize(arr, DESIRED_SIZE)
        _, jpeg = cv2.imencode('.jpg', small)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

        await asyncio.sleep(0)

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_yolo_mjpeg(), media_type='multipart/x-mixed-replace; boundary=frame')

# 상태 관리용 변수
simulator_status = {
    "player_pos": {"x": 60, "y": 10, "z": 27.23},
    "player_speed": 0,
    "player_health": 100,
    "enemy_health": 100,
    "distance": 0,
    "is_info_received": True,
    "gear": 2,
    "threat": "없음"
}

ROI = {
    'top': 0,
    'left': 0,
    'width': DESIRED_SIZE[0],
    'height': DESIRED_SIZE[1]
}

@app.get("/get_status")
async def get_status():
    return {
        **simulator_status,
        "ROI": ROI,
        "size_x": DESIRED_SIZE[0],
        "size_y": DESIRED_SIZE[1]
    }

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

detected_objects = []
@app.get("/get_detected_objects")
async def get_detected_objects():
    return {
        "objects": detected_objects
    }

@app.get("/")
def root():
    return {"status": "✅ FastAPI is working"}

move_command_queue = []
gear_level = 2
gear_weights = {1: 0.3, 2: 0.6, 3: 1.0}

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
    if move_command_queue:
        return move_command_queue.pop(0)
    return {"move": "STOP", "weight": 1.0}

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

@app.post("/update_position")
async def update_position(request: Request):
    global simulator_status
    data = await request.json()
    pos_str = data.get("position", "")
    try:
        x, y, z = map(float, pos_str.split(","))
        simulator_status["player_pos"] = {"x": x, "y": y, "z": z}
    except Exception as e:
        return {"error": f"Invalid position format: {e}"}
    return {"status": "success"}



print("✅ 서버가 제대로 main_obs.py에서 실행됨")