import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse
# from fastapi.templating import Jinja2Templates  # 사용안함
# from fastapi.staticfiles import StaticFiles  # 사용안함
from ultralytics import YOLO
from pathlib import Path
from datetime import datetime
# from utils.network import get_local_ip  # 사용안함
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
from concurrent.futures import ThreadPoolExecutor
# from PIL import Image  # 사용안함
# import base64  # 사용안함
# import shutil  # 사용안함
import traceback
# from typing import List  # 사용안함

# 로깅 설정
logging.basicConfig(level=logging.WARNING,  # 기본 로깅 레벨을 WARNING으로 설정
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("app.main")
logger.setLevel(logging.INFO)  # 필요시 더 자세한 로깅을 위해 INFO로 설정

############################################################
# 🛰️ FastAPI 앱 & 리소스 초기화
############################################################

BASE_DIR = Path(__file__).resolve().parent
# CROSSHAIR_PATH = BASE_DIR / "static" / "img" / "crosshair.png"  # 사용안함
EFFICIENTNET_MODEL_PATH = BASE_DIR / "models" / "Efficientnet_weights" / "30000Efficient_weight.h5"
# TEMP_PATH = BASE_DIR / "tmp" / "temp.jpg"  # 사용안함
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
# logger.info(f"🎯 크로스헤어 경로: {CROSSHAIR_PATH}")  # 사용안함
# logger.info(f"💾 임시 파일 경로: {TEMP_PATH}")  # 사용안함

# app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")  # 사용안함
# templates = Jinja2Templates(directory=BASE_DIR / "templates")  # 사용안함

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

# size_x, size_y = 2560, 1440  # 사용안함
# DESIRED_SIZE = (size_x, size_y)  # 사용안함

# ROI = {  # 사용안함
#     'top':    0,
#     'left':   0,
#     'width':  size_x,
#     'height': size_y
# }

move_command_queue = []
horizontal_command_queue = []
vertical_command_queue = []
# bullet_logs = []  # 사용안함
# turret_pitch_angle = 0.0  # 사용안함
gear_level = 2
gear_weights = {1: 0.3, 2: 0.6, 3: 1.0}
# last_turret_y = None  # 사용안함
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
        class_names = ["enemy_front", "enemy_rear", "enemy_side"]
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

def process_crop_sync(crop_img, track_id):
    """동기적으로 EfficientNet 처리를 수행합니다."""
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
        class_names = ["enemy_front", "enemy_rear", "enemy_side"]
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

# @app.get("/dashboard", response_class=HTMLResponse)  # 사용안함
# async def dashboard(request: Request):
#     return templates.TemplateResponse("dashboard.html", {"request": request})

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
    global vertical_command_queue, horizontal_command_queue, TARGET
    if detected_objects:
        error = TARGET - detected_objects[0]["y"]
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
        # "roi": ROI,  # 사용안함
        "objects": confirmed_objects
    }

@app.post("/detect_objects")
async def detect_objects_from_client(image: UploadFile = File(...), process_crop: bool = Form(False)):
    global pending_objects
    try:
        logger.info("==== 객체 감지 요청 수신 (서버 처리 방식) ====")
        start_time = time.time()
        
        # 1. 이미지 디코딩 및 유효성 검사
        image_bytes = await image.read()
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img_cv is None or img_cv.size == 0:
            logger.error("유효하지 않은 이미지 데이터 수신")
            return JSONResponse(
                status_code=400,
                content={"status": "ERROR", "message": "유효하지 않은 이미지 데이터"}
            )
        
        # 원본 이미지 크기 저장
        original_height, original_width = img_cv.shape[:2]
        logger.info(f"원본 이미지 크기: {original_width}x{original_height}")
        
        # YOLO 모델이 기대하는 입력 크기 (YOLOv8 기본값: 640x640)
        target_size = 640
        
        # 이미지 리사이즈 (종횡비 유지)
        scale = min(target_size / original_width, target_size / original_height)
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        
        # 검은색 배경 생성
        resized = np.zeros((target_size, target_size, 3), dtype=np.uint8)
        
        # 이미지를 중앙에 배치
        dx = (target_size - new_width) // 2
        dy = (target_size - new_height) // 2
        resized[dy:dy+new_height, dx:dx+new_width] = cv2.resize(img_cv, (new_width, new_height))
        
        logger.info(f"YOLO 입력 크기: {target_size}x{target_size}, 리사이즈된 이미지 크기: {new_width}x{new_height}")
        
        if yolo_model is None:
            logger.error("YOLO 모델이 로드되지 않았습니다.")
            return JSONResponse(
                status_code=500,
                content={"status": "ERROR", "message": "YOLO 모델이 초기화되지 않았습니다."}
            )
        
        # 2. YOLO 추론 (고정 크기 입력 사용)
        results = await process_image_array(
            image=resized,
            yolo_model=yolo_model,
            detected_objects=detected_objects,
            image_size=(target_size, target_size)  # 고정 크기 사용
        )
        
        if isinstance(results, JSONResponse):
            return results

        # 3. bbox 좌표를 원본 이미지 크기로 변환
        current_time = time.time()
        enemy_objects = []  # EfficientNet 처리를 위한 적 객체 목록
        
        for obj in detected_objects:
            track_id = obj["track_id"]
            obj["timestamp"] = current_time
            
            # bbox 좌표 변환 (YOLO 출력 좌표 -> 원본 이미지 좌표)
            if "bbox" in obj:
                try:
                    x1, y1, x2, y2 = map(int, obj["bbox"])
                    
                    # YOLO 출력 좌표를 원본 이미지 좌표로 변환
                    x1 = max(0, int((x1 - dx) / scale))
                    y1 = max(0, int((y1 - dy) / scale))
                    x2 = min(original_width, int((x2 - dx) / scale))
                    y2 = min(original_height, int((y2 - dy) / scale))
                    
                    # 변환된 좌표 저장
                    obj["bbox"] = [x1, y1, x2, y2]
                    
                    # EfficientNet 처리를 위해 적 객체 수집
                    if process_crop and obj.get("className") == "enemy":
                        enemy_objects.append((x1, y1, x2, y2, track_id))
                        
                except Exception as e:
                    if logger.isEnabledFor(logging.ERROR):
                        logger.error(f"bbox 좌표 변환 오류 (track_id: {track_id}): {str(e)}")
            
            # pending_objects에 저장
            pending_objects[track_id] = obj
        
        # EfficientNet 처리는 별도의 스레드 풀로 한 번에 처리
        if enemy_objects:
            with ThreadPoolExecutor(max_workers=4) as executor:
                for x1, y1, x2, y2, track_id in enemy_objects:
                    crop_img = img_cv[y1:y2, x1:x2]
                    if crop_img.size > 0:
                        executor.submit(process_crop_sync, crop_img, track_id)
        
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
    # bullet_logs.append(log_msg)  # 사용안함
    return {"status": "OK"}

@app.get("/get_logs")
async def get_logs():
    # return {"logs": bullet_logs[-20:]}  # 사용안함
    return {"logs": []}

@app.post("/info")
async def receive_simulator_info(request: Request):
    global simulator_status
    data = await request.json()
    simulator_status["player_pos"] = data.get("playerPos", simulator_status["player_pos"])
    simulator_status["player_speed"] = data.get("playerSpeed", simulator_status["player_speed"])
    simulator_status["player_health"] = data.get("playerHealth", simulator_status["player_health"])
    simulator_status["player_turret_x"] = data.get("playerTurretX", simulator_status["player_turret_x"])
    simulator_status["player_turret_y"] = last_turret_y
    simulator_status["enemy_health"] = data.get("enemyHealth", simulator_status["enemy_health"])
    simulator_status["distance"] = data.get("distance", simulator_status["distance"])
    return {"status": "success"}

# @app.post("/set_roi")  # 사용안함
# async def set_roi(request: Request):
#     global size_x, size_y, DESIRED_SIZE
#     data = await request.json()
#     ROI["top"] = int(data.get("top", ROI["top"]))
#     ROI["left"] = int(data.get("left", ROI["left"]))
#     ROI["width"] = int(data.get("width", ROI["width"]))
#     ROI["height"] = int(data.get("height", ROI["height"]))
#     size_x = ROI["width"]
#     size_y = ROI["height"]
#     DESIRED_SIZE = (size_x, size_y)
#     return {"status": "success", "ROI": ROI}

# SERVER_IP = get_local_ip()  # 사용안함
# DASHBOARD_URL = f"http://{SERVER_IP}:8000/dashboard"  # 사용안함

if __name__ == "__main__":
    # print("🖥️ 대시보드 접속 주소:")  # 사용안함
    # print(f"👉 {DASHBOARD_URL}")  # 사용안함
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)