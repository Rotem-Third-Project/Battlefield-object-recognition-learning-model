import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO
from pathlib import Path
from datetime import datetime
from utils.network import get_local_ip
from models.detect import process_image_array
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import tensorflow as tf
import asyncio
import cv2
import numpy as np
import threading
import time
import io
from PIL import Image
import base64
import shutil
import traceback
from typing import List

# 로깅 설정
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("app.main")

############################################################
# 🛰️ FastAPI 앱 & 리소스 초기화
############################################################

BASE_DIR = Path(__file__).resolve().parent
CROSSHAIR_PATH = BASE_DIR / "static" / "img" / "crosshair.png"
EFFICIENTNET_MODEL_PATH = BASE_DIR / "models" / "Efficientnet_weights" / "30000Efficient_weight.h5"
TEMP_PATH = BASE_DIR / "tmp" / "temp.jpg"
app = FastAPI()

# 임시 및 확정 객체 저장소
pending_objects = {}  # track_id -> YOLO 감지 객체
confirmed_objects = []  # 최종 결과 저장

##########################################################
# 프론트엔드 리소스 설정 
##########################################################
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

logger.info("🚀 서버 초기화 중...")
logger.info(f"📁 작업 디렉토리: {BASE_DIR}")
logger.info(f"🎯 크로스헤어 경로: {CROSSHAIR_PATH}")
logger.info(f"💾 임시 파일 경로: {TEMP_PATH}")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# YOLO 모델 로드
try:
    logger.info("🔍 YOLO 모델 로드 중...")
    yolo_model = YOLO(BASE_DIR / "models" / "yolo_weights" / "best.pt")
    logger.info("✅ YOLO 모델 로드 완료")
except Exception as e:
    logger.error(f"❌ YOLO 모델 로드 실패: {str(e)}")
    logger.error(traceback.format_exc())
    yolo_model = None

# EfficientNet 모델 로드
try:
    logger.info("🔍 EfficientNet 모델 로드 중...")
    efficientnet_model = tf.keras.models.load_model(EFFICIENTNET_MODEL_PATH, compile=False)
    logger.info("✅ EfficientNet 모델 로드 완료")
except Exception as e:
    logger.error(f"❌ EfficientNet 모델 로드 실패: {str(e)}")
    logger.error(traceback.format_exc())
    efficientnet_model = None

# Lifespan 핸들러
@asynccontextmanager
async def lifespan(app: FastAPI):
    async def cleanup_pending_task():
        while True:
            try:
                for tid in list(pending_objects.keys()):
                    if time.time() - pending_objects[tid]["timestamp"] > 300:  # 5분
                        pending_objects.pop(tid)
                        logger.info(f"Cleared stale pending object: track_id={tid}")
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error in cleanup_pending_task: {str(e)}")
                await asyncio.sleep(60)
    
    task = asyncio.create_task(cleanup_pending_task())
    logger.info("Started cleanup_pending_task")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("cleanup_pending_task cancelled on shutdown")

app.lifespan = lifespan

############################################################
# 🖼️ 이미지 처리 설정
############################################################

size_x, size_y = 2560, 1440
DESIRED_SIZE = (size_x, size_y)

ROI = {
    'top':    0,
    'left':   0,
    'width':  size_x,
    'height': size_y
}

move_command_queue = []
horizontal_command_queue = []
vertical_command_queue = []
bullet_logs = []
turret_pitch_angle = 0.0
gear_level = 2
gear_weights = {1: 0.3, 2: 0.6, 3: 1.0}
last_turret_y = None
TARGET = 9.42
detected_objects = []

simulator_status = {
    "player_pos": {"x": 60, "y": 10, "z": 27.23},
    "player_speed": 0,
    "player_health": 100,
    "enemy_health": 100,
    "distance": 0,
}

def set_target(val: float):
    global TARGET
    TARGET = val

async def process_crop_async(crop_img, track_id):
    """비동기적으로 EfficientNet 처리를 수행합니다."""
    try:
        if efficientnet_model is None:
            logger.error("EfficientNet 모델이 로드되지 않았습니다.")
            return

        img_resized = cv2.resize(crop_img, (224, 224), interpolation=cv2.INTER_AREA)
        img_array = np.expand_dims(img_resized, axis=0) / 255.0
        predictions = efficientnet_model.predict(img_array, verbose=0)
        logger.info(f"Raw predictions: {predictions[0].tolist()}")
        class_idx = np.argmax(predictions[0])
        confidence = float(predictions[0][class_idx])
        class_names = ["enemy_front", "enemy_side", "enemy_rear"]
        direction = class_names[class_idx] if class_idx < len(class_names) else "unknown"
        threat = {
            "enemy_front": "LEVEL 3",
            "enemy_side": "LEVEL 2",
            "enemy_rear": "LEVEL 1",
            "unknown": "Normal"
        }.get(direction, "Normal")

        logger.info(f"EfficientNet 예측: track_id={track_id}, 방향={direction}, 신뢰도={confidence:.2f}, 위협 등급={threat}")

        # pending_objects에서 객체 가져와 confirmed_objects에 추가
        if track_id in pending_objects:
            obj = pending_objects.pop(track_id)
            obj.update({
                "threat": threat,
                "direction": direction,
                "direction_confidence": confidence
            })
            existing = next((o for o in confirmed_objects if o["track_id"] == track_id), None)
            if existing:
                confirmed_objects.remove(existing)
            confirmed_objects.append(obj)
            logger.info(f"Confirmed object: track_id={track_id}, threat={threat}")
        else:
            logger.warning(f"No pending object found for track_id={track_id}")
    except Exception as e:
        logger.error(f"EfficientNet 처리 실패 (track_id: {track_id}): {str(e)}")

############################################################
# 🌐 FastAPI 엔드포인트
############################################################

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

@app.get("/get_detected_objects")
async def get_detected_objects():
    return {
        "roi": ROI,
        "objects": confirmed_objects
    }

@app.post("/detect_objects")
async def detect_objects_from_client(image: UploadFile = File(...), process_crop: bool = Form(False)):
    global pending_objects
    try:
        logger.info("==== 객체 감지 요청 수신 (서버 처리 방식) ====")
        start_time = time.time()
        
        image_bytes = await image.read()
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img_cv is None or img_cv.size == 0:
            logger.error("유효하지 않은 이미지 데이터 수신")
            return JSONResponse(
                status_code=400,
                content={"status": "ERROR", "message": "유효하지 않은 이미지 데이터"}
            )
            
        logger.info(f"📊 입력 이미지 크기: {img_cv.shape}, 데이터 크기: {len(image_bytes)} bytes")
        
        if yolo_model is None:
            logger.error("YOLO 모델이 로드되지 않았습니다.")
            return JSONResponse(
                status_code=500,
                content={"status": "ERROR", "message": "YOLO 모델이 초기화되지 않았습니다."}
            )
        
        results = await process_image_array(
            image=img_cv,
            yolo_model=yolo_model,
            detected_objects=detected_objects,
            image_size=(size_x, size_y)
        )
        
        if isinstance(results, JSONResponse):
            return results

        # pending_objects에 YOLO 감지 결과 저장
        for obj in detected_objects:
            track_id = obj["track_id"]
            obj["timestamp"] = time.time()
            pending_objects[track_id] = obj
            logger.info(f"Added to pending_objects: track_id={track_id}")
        
        # EfficientNet 처리 요청 시 비동기 처리
        if process_crop:
            for obj in detected_objects:
                if obj["className"] == "enemy" and "bbox" in obj:
                    x1, y1, x2, y2 = map(int, obj["bbox"])
                    crop_img = img_cv[y1:y2, x1:x2]
                    if crop_img.size > 0:
                        asyncio.create_task(process_crop_async(crop_img, obj["track_id"]))
        
        elapsed_time = time.time() - start_time
        logger.info(f"⏱️ 총 처리 시간: {elapsed_time:.4f}초")
        logger.info(f"🎯 감지된 객체 수: {len(detected_objects)}")
        
        if detected_objects:
            logger.info(f"📋 첫 번째 객체 정보: {detected_objects[0]}")
            
        return {"status": "success", "objects": detected_objects, "process_time_ms": int(elapsed_time * 1000)}
            
    except Exception as e:
        logger.error(f"❌ 객체 감지 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"status": "ERROR", "message": str(e)}
        )

@app.post("/process_crop")
async def process_crop_image(crop: UploadFile = File(...), track_id: str = Form(...)):
    global confirmed_objects
    try:
        if efficientnet_model is None:
            logger.error("EfficientNet 모델이 로드되지 않았습니다.")
            return JSONResponse(
                status_code=500,
                content={"status": "ERROR", "message": "EfficientNet 모델이 초기화되지 않았습니다."}
            )

        image_bytes = await crop.read()
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img_cv is None or img_cv.size == 0:
            logger.error(f"유효하지 않은 크롭 이미지 데이터: 크기={len(image_bytes)} bytes")
            return JSONResponse(
                status_code=400,
                content={"status": "ERROR", "message": "유효하지 않은 이미지 데이터"}
            )

        logger.info(f"Input image shape: {img_cv.shape}, mean: {np.mean(img_cv)}")
        img_resized = cv2.resize(img_cv, (224, 224), interpolation=cv2.INTER_AREA)
        img_array = np.expand_dims(img_resized, axis=0) / 255.0
        predictions = efficientnet_model.predict(img_array, verbose=0)
        logger.info(f"Raw predictions: {predictions[0].tolist()}")
        class_idx = np.argmax(predictions[0])
        confidence = float(predictions[0][class_idx])
        class_names = ["enemy_front", "enemy_side", "enemy_rear"]
        direction = class_names[class_idx] if class_idx < len(class_names) else "unknown"
        threat = {
            "enemy_front": "LEVEL 3",
            "enemy_side": "LEVEL 2",
            "enemy_rear": "LEVEL 1",
            "unknown": "Normal"
        }.get(direction, "Normal")

        logger.info(f"EfficientNet 예측: track_id={track_id}, 방향={direction}, 신뢰도={confidence:.2f}, 위협 등급={threat}")

        # pending_objects에서 객체 가져와 confirmed_objects에 추가
        if track_id in pending_objects:
            obj = pending_objects.pop(track_id)
            obj.update({
                "threat": threat,
                "direction": direction,
                "direction_confidence": confidence
            })
            existing = next((o for o in confirmed_objects if o["track_id"] == track_id), None)
            if existing:
                confirmed_objects.remove(existing)
            confirmed_objects.append(obj)
            logger.info(f"Confirmed object: track_id={track_id}, threat={threat}")
        else:
            logger.warning(f"No pending object found for track_id={track_id}")

        return {
            "status": "success",
            "direction": direction,
            "direction_confidence": confidence,
            "threat": threat
        }
    except Exception as e:
        logger.error(f"크롭 이미지 처리 오류: track_id={track_id}, {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"status": "ERROR", "message": str(e)}
        )

@app.post("/clear_pending")
async def clear_pending(request: Request):
    global pending_objects
    try:
        data = await request.json()
        track_id = data.get("track_id")
        if not track_id:
            return JSONResponse(
                status_code=400,
                content={"status": "ERROR", "message": "track_id is required"}
            )
        if track_id in pending_objects:
            pending_objects.pop(track_id)
            logger.info(f"Cleared pending object: track_id={track_id}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to clear pending object: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "ERROR", "message": str(e)}
        )

@app.get("/init")
async def init():
    return {
        "startMode": "start",
        "blStartX": 60, "blStartY": 10, "blStartZ": 27.23,
        "rdStartX": 59, "rdStartY": 10, "rdStartZ": 280
    }

@app.api_route("/get_status", methods=["GET", "HEAD"])
async def get_status_dummy():
    return {"status": "online"}

@app.post("/update_bullet")
async def update_bullet(request: Request):
    data = await request.json()
    impact_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log_msg = f"[{impact_time}] 💥 Impact at X={data.get('x')}, Y={data.get('y')}, Z={data.get('z')}, Target={data.get('hit')}"
    bullet_logs.append(log_msg)
    return {"status": "OK"}

@app.get("/get_logs")
async def get_logs():
    return {"logs": bullet_logs[-20:]}

@app.post("/info")
async def receive_simulator_info(request: Request):
    global simulator_status, last_turret_y
    data = await request.json()
    last_turret_y = data.get("playerTurretY", last_turret_y)
    simulator_status["player_pos"] = data.get("playerPos", simulator_status["player_pos"])
    simulator_status["player_speed"] = data.get("playerSpeed", simulator_status["player_speed"])
    simulator_status["player_health"] = data.get("playerHealth", simulator_status["player_health"])
    simulator_status["player_turret_x"] = data.get("playerTurretX", simulator_status["player_turret_x"])
    simulator_status["player_turret_y"] = last_turret_y
    simulator_status["enemy_health"] = data.get("enemyHealth", simulator_status["enemy_health"])
    simulator_status["distance"] = data.get("distance", simulator_status["distance"])
    return {"status": "success"}

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

SERVER_IP = get_local_ip()
DASHBOARD_URL = f"http://{SERVER_IP}:8000/dashboard"

if __name__ == "__main__":
    print("🖥️ 대시보드 접속 주소:")
    print(f"👉 {DASHBOARD_URL}")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)