import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # KMP 라이브러리 중복 로드 관련 경고 방지

# FastAPI 관련 임포트
from fastapi import FastAPI, HTTPException, Request, Form, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# YOLO 객체 감지 관련
from ultralytics import YOLO
from models.detect import process_image_array

# 유틸리티
from pathlib import Path
import logging
from typing import List, Dict, Optional
import math
# 로깅 설정
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("app.main")

# 이미지 처리 관련
import cv2
import numpy as np
from PIL import Image
import base64

# 비동기 처리
import asyncio
import threading
import time

# 모델 로드
import tensorflow as tf

############################################################
# 🛰️ FastAPI 앱 & 리소스 초기화
############################################################

BASE_DIR = Path(__file__).resolve().parent

EFFICIENTNET_MODEL_PATH = BASE_DIR / "models" / "Efficientnet_weights" / "30000Efficient_weight.h5"
TEMP_PATH = BASE_DIR / "tmp" / "temp.jpg"
app = FastAPI()

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

# 앱 시작 시 로그
logger.info("🚀 서버 초기화 중...")
logger.info(f"📁 작업 디렉토리: {BASE_DIR}")
logger.info(f"💾 임시 파일 경로: {TEMP_PATH}")

# YOLO 모델 로드
try:
    logger.info("🔍 YOLO 모델 로드 중...")
    yolo_model = YOLO(BASE_DIR / "models" / "yolo_weights" / "best.pt")
    logger.info("✅ YOLO 모델 로드 완료")
except Exception as e:
    logger.error(f"❌ YOLO 모델 로드 실패: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    # 모델 로드 실패시 None으로 설정
    yolo_model = None
efficientnet_model = tf.keras.models.load_model(EFFICIENTNET_MODEL_PATH, compile=False)

############################################################
# 🧠 상태 변수들
############################################################

cropped_images = {}  # {track_id: base64_image}
cropped_images_lock = threading.Lock()
move_command_queue = []
horizontal_command_queue = []
vertical_command_queue = []
bullet_logs = []
turret_pitch_angle = 0.0
gear_level = 2
gear_weights = {1: 0.3, 2: 0.6, 3: 1.0}
last_turret_y = None
TARGET = 9.42  # 초기값

detected_objects = []

simulator_status = {
    "player_pos": {"x": 60, "y": 10, "z": 27.23},
    "player_speed": 0,
    "player_health": 100,
    "enemy_health": 100,
    "distance": 0,
    "is_info_received": False,
    "last_info_time": 0,
    "player_turret_y": 0.0,
    "player_turret_x": 0.0,
    "turret_pitch": 0.0
}
def set_target(val: float):
    global TARGET
    TARGET = val

# 우선순위 계산을 위한 가중치 정의
DIRECTION_WEIGHT = 0.9
SIZE_WEIGHT = 0.07
DISTANCE_WEIGHT = 0.03
direction_weights = {
    "enemy_front": 1.0,
    "enemy_side": 0.4,
    "enemy_rear": 0.2,
    "unknown": 0.0
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
        "roi": None,  # ROI 미정의
        "objects": detected_objects
    }

# 📌 클라이언트 이미지로 객체 감지
@app.post("/detect_objects")
async def detect_objects_from_client(image: UploadFile = File(...)):
    try:
        logger.info("==== 객체 감지 요청 수신 (서버 처리 방식) ====")
        start_time = time.time()
        image_bytes = await image.read()
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img_cv is None:
            raise HTTPException(status_code=400, detail="유효하지 않은 이미지 파일입니다.")
        local_detected_objects = []
        results = await process_image_array(
            image=img_cv,
            yolo_model=yolo_model,
            detected_objects=local_detected_objects,
        )
        with cropped_images_lock:
            cropped_images.clear()
            detected_objects[:] = local_detected_objects
            for obj in local_detected_objects:
                if obj["className"] == "enemy" and obj["track_id"] is not None:
                    x1, y1, x2, y2 = obj["bbox"]
                    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(img_cv.shape[1], x2), min(img_cv.shape[0], y2)
                    if x2 > x1 and y2 > y1:
                        crop_img = img_cv[y1:y2, x1:x2]
                        _, encoded_crop = cv2.imencode('.jpg', crop_img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                        crop_base64 = base64.b64encode(encoded_crop).decode('utf-8')
                        cropped_images[obj["track_id"]] = crop_base64
        elapsed_time = time.time() - start_time
        return {
            "status": "success",
            "objects": local_detected_objects,
            "process_time_ms": int(elapsed_time * 1000)
        }
    except Exception as e:
        logger.error(f"❌ 객체 감지 오류: {str(e)}")
        return JSONResponse(status_code=500, content={"status": "ERROR", "message": str(e)})

async def process_crop_batch_async(crop_imgs: List[np.ndarray], track_ids: List[int], pending_objects: Dict, confirmed_objects: List):
    """
    배치 크롭 이미지 처리 (EfficientNet)
    """
    try:
        loop = asyncio.get_event_loop()
        def predict_batch():
            img_arrays = [cv2.resize(img, (224, 224)) / 255.0 for img in crop_imgs]
            img_arrays = np.array(img_arrays)
            return efficientnet_model.predict(img_arrays, verbose=0)
        predictions = await loop.run_in_executor(None, predict_batch)
        for track_id, pred in zip(track_ids, predictions):
            class_idx = np.argmax(pred)
            confidence = float(pred[class_idx])
            class_names = ["enemy_front", "enemy_rear", "enemy_side"]
            direction = class_names[class_idx] if class_idx < len(class_names) else "unknown"
            threat = {
                "enemy_front": "LEVEL 3",
                "enemy_side": "LEVEL 2",
                "enemy_rear": "LEVEL 1",
                "unknown": "Normal"
            }.get(direction, "Normal")
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
    except Exception as e:
        logger.error(f"배치 크롭 이미지 처리 오류: {str(e)}")

def calculate_priorities(objects: List[Dict]) -> List[Dict]:
    """
    우선순위 계산
    - 방향 (앞 > 옆 > 뒤)
    - 바운딩 박스 세로 길이 제곱
    - 직선 (x=712, y=245~1032)으로부터의 수직 거리 (가까울수록 높음)
    
    Args:
        objects: 탐지된 객체 리스트, 각 객체는 className, bbox, direction 등을 포함
    
    Returns:
        우선순위가 계산된 객체 리스트 (priority_score와 rank 포함)
    """
    try:
        if not objects:
            return objects

        # 직선 기준점 (AutoHotkey 좌표)
        line_x = 712  # 직선 x=712
        max_distance = 1280  # 화면 너비로 최대 거리 설정 (임의로 1280 사용)
        max_height = max((obj["bbox"][3] - obj["bbox"][1]) for obj in objects) if objects else 1

        # 우선순위 점수 계산
        updated_objects = []
        for obj in objects:
            # 1. 방향 점수
            direction = obj.get("direction", "unknown") if obj.get("className") == "enemy" else obj.get("className", "unknown")
            dir_score = direction_weights.get(direction, 0.0)

            # 2. 바운딩 박스 세로 길이 제곱
            x1, y1, x2, y2 = obj.get("bbox", [0, 0, 0, 0])
            height = y2 - y1
            size_score = (height ** 2) / (max_height ** 2) if max_height > 0 else 0.0

            # 3. 직선(x=712)으로부터의 수직 거리
            box_center_x = (x1 + x2) / 2
            distance = abs(box_center_x - line_x)
            distance_score = 1.0 - (distance / max_distance) if max_distance > 0 else 0.0

            # 4. 최종 우선순위 점수
            total_score = (
                DIRECTION_WEIGHT * dir_score +
                SIZE_WEIGHT * size_score +
                DISTANCE_WEIGHT * distance_score
            )
            obj["priority_score"] = total_score
            updated_objects.append(obj)

        # 점수 기준으로 정렬하고 rank 부여
        sorted_objects = sorted(updated_objects, key=lambda x: x.get("priority_score", 0), reverse=True)
        for rank, obj in enumerate(sorted_objects, 1):
            obj["rank"] = rank

        return sorted_objects

    except Exception as e:
        logger.error(f"우선순위 계산 오류: {str(e)}")
        return objects

@app.post("/detect_objects_with_postprocessing")
async def detect_objects_with_postprocessing(image: UploadFile = File(...)):
    try:
        logger.info("==== 객체 감지 후처리 요청 수신 ====")
        start_time = time.time()
        with cropped_images_lock:
            if not detected_objects:
                return JSONResponse(
                    status_code=400,
                    content={"status": "ERROR", "message": "감지된 객체 또는 크롭 이미지가 없습니다."}
                )
        crop_imgs = []
        track_ids = []
        pending_objects = {}
        for track_id, crop_base64 in cropped_images.items():
            image_bytes = base64.b64decode(crop_base64)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            crop_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if crop_img is not None and crop_img.size > 0:
                obj = next((o for o in detected_objects if o["track_id"] == track_id), None)
                if obj:
                    crop_imgs.append(crop_img)
                    track_ids.append(track_id)
                    pending_objects[track_id] = obj
        confirmed_objects = []
        if crop_imgs:
            await process_crop_batch_async(crop_imgs, track_ids, pending_objects, confirmed_objects)
        remaining_objects = [
            obj for obj in detected_objects 
            if obj["track_id"] not in pending_objects or obj["className"] != "enemy"
        ]
        local_processed_objects = confirmed_objects + remaining_objects

        # track_id 기준으로 중복 제거
        unique_objects = {}
        for obj in local_processed_objects:
            tid = obj.get("track_id")
            if tid is not None:
                unique_objects[tid] = obj
            else:
                unique_objects[id(obj)] = obj
        local_processed_objects = list(unique_objects.values())

        # 우선순위 계산
        local_processed_objects = calculate_priorities(local_processed_objects)
        with cropped_images_lock:
            detected_objects[:] = local_processed_objects
        elapsed_time = time.time() - start_time
        return {
            "status": "success",
            "objects": local_processed_objects,
            "process_time_ms": int(elapsed_time * 1000)
        }
    except Exception as e:
        logger.error(f"❌ 객체 감지 및 후처리 오류: {str(e)}")
        return JSONResponse(status_code=500, content={"status": "ERROR", "message": str(e)})

# 📌 상태 정보 제공
@app.get("/get_status")
async def get_status():
    simulator_status["turret_pitch"] = turret_pitch_angle
    return {
        **simulator_status,
    }

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
    simulator_status["player_turret_y"] = data.get("playerTurretY", simulator_status["player_turret_y"])
    simulator_status["player_turret_x"] = data.get("playerTurretX", simulator_status["player_turret_x"])
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, access_log=False)
