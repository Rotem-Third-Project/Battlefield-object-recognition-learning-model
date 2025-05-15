from fastapi import FastAPI, Request, Form, WebSocket
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
import io
from PIL import Image
import base64

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

capture_q = asyncio.Queue(maxsize=2)
stream_q = asyncio.Queue(maxsize=2)

############################################################
# 🛰️ FastAPI 앱 & 리소스 초기화
############################################################

BASE_DIR = Path(__file__).resolve().parent
CROSSHAIR_PATH = BASE_DIR / "static" / "img" / "crosshair.png"
EFFICIENTNET_MODEL_PATH = BASE_DIR / "models" / "Efficientnet_weights" / "30000Efficient_weight.h5"
TEMP_PATH = BASE_DIR / "tmp" / "temp.jpg"
app = FastAPI()

# 프론트엔드 리소스 설정
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

yolo_model = YOLO(BASE_DIR / "models" / "yolo_weights" / "best.pt")
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

# 📌 객체 감지 결과 제공 (기존 GET 엔드포인트)
@app.get("/get_detected_objects")
async def get_detected_objects():
    return {
        "roi": ROI,
        "objects": detected_objects
    }

# 📌 클라이언트 이미지로 객체 감지 (새 POST 엔드포인트)
@app.post("/detect_objects")
async def detect_objects_from_client(request: Request):
    try:
        data = await request.json()
        image_data = data.get('image').split(',')[1]  # Base64 데이터 추출
        img = Image.open(io.BytesIO(base64.b64decode(image_data)))
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # detect.py의 process_image_array 호출
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
        return {"objects": detected_objects}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "ERROR", "message": str(e)}
        )

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

# 📌 ROI 설정 API (웹에서 ROI 변경 가능)
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
# 🎯 비동기 캡처 & 인코딩 루프
############################################################

# async def capture_loop():
#     with mss.mss() as sct:
#         while True:
#             img = sct.grab(ROI.copy())
#             await capture_q.put(img)
#             await asyncio.sleep(INTERVAL)

# async def encode_loop():
#     while True:
#         sct_img = await capture_q.get()

#         arr = np.frombuffer(sct_img.rgb, dtype=np.uint8).reshape(
#             sct_img.height, sct_img.width, 3)
#         arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

#         arr = await process_image_array(
#             image=arr,
#             yolo_model=yolo_model,
#             efficientnet_model=efficientnet_model,
#             crosshair_path=CROSSHAIR_PATH,
#             tmp_path=TEMP_PATH,
#             detected_objects=detected_objects,
#             horizontal_command_queue=horizontal_command_queue,
#             set_target_callback=set_target
#         )

#         small = cv2.resize(arr, DESIRED_SIZE, interpolation=cv2.INTER_LINEAR)
#         _, jpeg = cv2.imencode('.jpg', small, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
#         await stream_q.put(jpeg.tobytes())

#         await asyncio.sleep(0)

# async def generate_mjpeg():
#     while True:
#         frame = await stream_q.get()
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
#         await asyncio.sleep(0)

# @app.get("/video_feed")
# async def video_feed():
#     return StreamingResponse(generate_mjpeg(),
#                              media_type='multipart/x-mixed-replace; boundary=frame')

############################################################
# 🔄 lifespan: 서버 시작 시 캡처 & 인코드 시작
############################################################

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # WebRTC로 전환했으므로 capture_loop 비활성화
#     # asyncio.create_task(capture_loop())
#     asyncio.create_task(encode_loop())
#     yield

# app.router.lifespan_context = lifespan

############################################################
# 🏁 서버 실행 설정
############################################################

SERVER_IP = get_local_ip()
DASHBOARD_URL = f"http://{SERVER_IP}:5000/dashboard"

def monitor_info_status():
    while True:
        last_time = simulator_status.get("last_info_time", 0)
        if time.time() - last_time > 3:
            simulator_status["is_info_received"] = False
        time.sleep(1)

threading.Thread(target=monitor_info_status, daemon=True).start()

if __name__ == "__main__":
    print("🖥️ 대시보드 접속 주소:")
    print(f"👉 {DASHBOARD_URL}")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, access_log=False)

##########################################################
# 프론트엔드 리소스 설정
##########################################################
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중 전체 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)