import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # KMP 라이브러리 중복 로드 관련 경고 방지

# FastAPI 관련 임포트
from fastapi import FastAPI, HTTPException, Request, Form, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query

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
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("app.main")

# 디버깅 모드 설정 (환경변수로 제어 가능)
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"
if DEBUG_MODE:
    logger.setLevel(logging.DEBUG)
    logging.getLogger("app.auto_aim").setLevel(logging.DEBUG)
    logger.info("🐛 디버깅 모드 활성화")
else:
    logger.setLevel(logging.INFO)
    logging.getLogger("app.auto_aim").setLevel(logging.INFO)

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
from models.auto_aim import auto_aim_calculate

############################################################
# 🛰️ FastAPI 앱 & 리소스 초기화
############################################################

BASE_DIR = Path(__file__).resolve().parent
CROSSHAIR_PATH = BASE_DIR / "static" / "img" / "crosshair.png"
EFFICIENTNET_MODEL_PATH = (
    BASE_DIR / "models" / "Efficientnet_weights" / "30000Efficient_weight.h5"
)
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
fire = []
bullet_logs = []
turret_pitch_angle = 0.0
gear_level = 2
gear_weights = {1: 0.3, 2: 0.6, 3: 1.0}
last_turret_y = 0.0
TARGET = 30.0  # 초기값
error1 = 0.0

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
    "turret_pitch": 0.0,
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
    "enemy_side": 0.5,
    "enemy_rear": 0.25,
    "unknown": 0.0,
}

############################################################
# 🌐 FastAPI 엔드포인트
############################################################


# # 📌 대시보드 렌더
# @app.get("/dashboard", response_class=HTMLResponse)
# async def dashboard(request: Request):
#     return templates.TemplateResponse("dashboard.html", {"request": request})


# 📌 키 입력 처리
@app.post("/input_key")
async def input_key(data: dict):
    key = data.get("key")
    action = data.get("action")
    if not key or not action:
        raise HTTPException(status_code=400, detail="key 또는 action이 누락됨")

    print(f"받은 데이터: {data}")
    global move_command_queue, horizontal_command_queue, vertical_command_queue, gear_level, fire
    if key in ["W", "A", "S", "D"]:
        if action == "down":
            move_command_queue.append({"move": key, "weight": gear_weights[gear_level]})
            print(f"이동 큐 업데이트: {move_command_queue}")
        elif action == "up":
            move_command_queue.clear()
            move_command_queue.append({"move": "STOP"})
            print(f"이동 큐 초기화 및 업데이트: {move_command_queue}")
    elif key in ["Q", "E"]:
        if action == "down":
            horizontal_command_queue.append({"turret": key, "weight": 1.0})
            print(f"수평 큐 업데이트: {horizontal_command_queue}")
        elif action == "up":
            horizontal_command_queue.clear()
            horizontal_command_queue.append({"turret": "STOP"})
            print(f"수평 큐 초기화 및 업데이트: {horizontal_command_queue}")
    elif key in ["R", "F"]:
        if action == "down":
            vertical_command_queue.append({"turret": key, "weight": 1.0})
            print(f"수직 큐 업데이트: {vertical_command_queue}")
        elif action == "up":
            vertical_command_queue.clear()
            vertical_command_queue.append({"turret": "STOP"})
            print(f"수직 큐 초기화 및 업데이트: {vertical_command_queue}")
    elif action == "down":
        if key == " ":
            fire.clear()  # 발사 명령 추가 전에 큐 비우기
            fire.append({"turret": "FIRE"})
            print(f"🎯 발사 큐 업데이트: {fire}")
            logger.info(f"🎯 발사 명령 추가됨 - 큐 상태: {fire}")
        elif key == "P" and gear_level < 3:
            gear_level += 1
            print(f"기어 증가: {gear_level}")
        elif key == "L" and gear_level > 1:
            gear_level -= 1
            print(f"기어 감소: {gear_level}")
    return {"status": "success", "gear_level": gear_level}


# 📌 이동 명령 요청
@app.get("/get_move")
async def get_move():
    global move_command_queue
    if move_command_queue:
        command = move_command_queue.pop(0)
        print(f"이동 명령: {command}")
        return command
    return {"move": "STOP"}


# 📌 객체 감지 결과 제공
@app.get("/get_detected_objects")
async def get_detected_objects():
    return {"objects": detected_objects}


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
            raise HTTPException(
                status_code=400, detail="유효하지 않은 이미지 파일입니다."
            )
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
                    x1, y1, x2, y2 = (
                        max(0, x1),
                        max(0, y1),
                        min(img_cv.shape[1], x2),
                        min(img_cv.shape[0], y2),
                    )
                    if x2 > x1 and y2 > y1:
                        crop_img = img_cv[y1:y2, x1:x2]
                        _, encoded_crop = cv2.imencode(
                            ".jpg", crop_img, [int(cv2.IMWRITE_JPEG_QUALITY), 50]
                        )
                        crop_base64 = base64.b64encode(encoded_crop).decode("utf-8")
                        cropped_images[obj["track_id"]] = crop_base64
        elapsed_time = time.time() - start_time
        return {
            "status": "success",
            "objects": local_detected_objects,
            "process_time_ms": int(elapsed_time * 1000),
        }
    except Exception as e:
        logger.error(f"❌ 객체 감지 오류: {str(e)}")
        return JSONResponse(
            status_code=500, content={"status": "ERROR", "message": str(e)}
        )


async def process_crop_batch_async(
    crop_imgs: List[np.ndarray],
    track_ids: List[int],
    pending_objects: Dict,
    confirmed_objects: List,
):
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
            direction = (
                class_names[class_idx] if class_idx < len(class_names) else "unknown"
            )
            threat = {
                "enemy_front": "LEVEL 3",
                "enemy_side": "LEVEL 2",
                "enemy_rear": "LEVEL 1",
                "unknown": "Normal",
            }.get(direction, "Normal")
            if track_id in pending_objects:
                obj = pending_objects.pop(track_id)
                obj.update(
                    {
                        "threat": threat,
                        "direction": direction,
                        "direction_confidence": confidence,
                    }
                )
                existing = next(
                    (o for o in confirmed_objects if o["track_id"] == track_id), None
                )
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
        max_height = (
            max((obj["bbox"][3] - obj["bbox"][1]) for obj in objects) if objects else 1
        )

        # 우선순위 점수 계산
        updated_objects = []
        for obj in objects:
            # 1. 방향 점수
            direction = (
                obj.get("direction", "unknown")
                if obj.get("className") == "enemy"
                else obj.get("className", "unknown")
            )
            dir_score = direction_weights.get(direction, 0.0)

            # 2. 바운딩 박스 세로 길이 제곱
            x1, y1, x2, y2 = obj.get("bbox", [0, 0, 0, 0])
            height = y2 - y1
            size_score = (height**2) / (max_height**2) if max_height > 0 else 0.0

            # 3. 직선(x=712)으로부터의 수직 거리
            box_center_x = (x1 + x2) / 2
            distance = abs(box_center_x - line_x)
            distance_score = (
                1.0 - (distance / max_distance) if max_distance > 0 else 0.0
            )

            # 4. 최종 우선순위 점수
            total_score = (
                DIRECTION_WEIGHT * dir_score
                + SIZE_WEIGHT * size_score
                + DISTANCE_WEIGHT * distance_score
            )
            obj["priority_score"] = total_score
            updated_objects.append(obj)

        # 점수 기준으로 정렬하고 rank 부여
        sorted_objects = sorted(
            updated_objects, key=lambda x: x.get("priority_score", 0), reverse=True
        )
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
                    content={
                        "status": "ERROR",
                        "message": "감지된 객체 또는 크롭 이미지가 없습니다.",
                    },
                )
        crop_imgs = []
        track_ids = []
        pending_objects = {}
        for track_id, crop_base64 in cropped_images.items():
            image_bytes = base64.b64decode(crop_base64)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            crop_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if crop_img is not None and crop_img.size > 0:
                obj = next(
                    (o for o in detected_objects if o["track_id"] == track_id), None
                )
                if obj:
                    crop_imgs.append(crop_img)
                    track_ids.append(track_id)
                    pending_objects[track_id] = obj
        confirmed_objects = []
        if crop_imgs:
            await process_crop_batch_async(
                crop_imgs, track_ids, pending_objects, confirmed_objects
            )
        remaining_objects = [
            obj
            for obj in detected_objects
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
            "process_time_ms": int(elapsed_time * 1000),
        }
    except Exception as e:
        logger.error(f"❌ 객체 감지 및 후처리 오류: {str(e)}")
        return JSONResponse(
            status_code=500, content={"status": "ERROR", "message": str(e)}
        )

######################### 상태 변수 추가
is_auto_aim_enabled = False

@app.post("/set_auto_aim")
async def set_auto_aim(data: dict):
    global is_auto_aim_enabled
    dataset = data.get("auto_aim", False)
    print(dataset)
    is_auto_aim_enabled = dataset
    logger.info(f"🤖 자동 조준 상태 업데이트: {is_auto_aim_enabled}")
    return {"status": "success", "auto_aim": is_auto_aim_enabled}

# 📌 포탑 조작 명령 요청
@app.get("/get_action")
async def get_action(auto_aim: bool = Query(True)):
    global is_auto_aim_enabled, vertical_command_queue, horizontal_command_queue, last_turret_y, TARGET, detected_objects, error1

    logger.debug(f"🎮 get_action 호출 - detected_objects 수: {len(detected_objects)}")

    # 1. 발사 명령을 가장 높은 우선순위로 처리
    if fire:
        print(f"🎯 발사 명령 처리: {fire}")
        logger.info(f"🎯 발사 명령 실행 - 큐 상태: {fire}")
        command = fire.pop(0)
        fire.clear()  # 발사 명령 처리 후 큐 비우기
        return command

    # 2. Auto-aim 로직 실행
    if auto_aim:
        # Auto-aim 계산을 위한 타겟 선택
        target_object = None
        if detected_objects:
            enemy_objects = [
                obj for obj in detected_objects if obj.get("className") == "enemy"
            ]
            logger.debug(f"🎯 적 객체 수: {len(enemy_objects)}")
            logger.debug(
                f"🎯 전체 detected_objects: {[obj.get('className') for obj in detected_objects]}"
            )

            if enemy_objects:
                target_object = enemy_objects[0]
                logger.debug(f"🎯 선택된 타겟: {target_object}")
            else:
                logger.debug("🎯 적 객체가 없습니다")
        else:
            logger.debug("🎯 탐지된 객체가 없습니다")

        # Auto-aim 계산 수행
        if target_object and target_object.get("bbox"):
            try:
                bbox = target_object["bbox"]
                direction = target_object.get("direction")

                logger.debug(
                    f"🎯 Auto-aim 계산 시작 - bbox: {bbox}, direction: {direction}"
                )

                # auto_aim_calculate 호출
                if direction == "enemy_front":
                    aim_result = auto_aim_calculate(
                        bbox, direction=direction, velocity_mps=237.86
                    )
                    error1 = aim_result.get("dx_from_barrel", None)
                    set_target(aim_result.get("aiming_angle_deg"))
                elif direction == "enemy_side":
                    aim_result = auto_aim_calculate(
                        bbox, direction=direction, velocity_mps=234.59
                    )
                    error1 = aim_result.get("dx_from_barrel", None)
                    set_target(aim_result.get("aiming_angle_deg"))
                elif direction == "enemy_rear":
                    aim_result = auto_aim_calculate(
                        bbox, direction=direction, velocity_mps=224.31
                    )
                    error1 = aim_result.get("dx_from_barrel", None)
                    set_target(aim_result.get("aiming_angle_deg"))

                logger.debug(f"🎯 Auto-aim 결과: {aim_result}")

                if is_auto_aim_enabled == True and "error" not in aim_result:
                    horizontal_cmd = aim_result.get("horizontal_command")
                    logger.debug(
                        f"🔄 수평 명령 확인: '{horizontal_cmd}' (타입: {type(horizontal_cmd)})"
                    )

                    if horizontal_cmd and horizontal_cmd != " ":
                        logger.debug(
                            f"🔄 수평 명령 큐 클리어 전: {horizontal_command_queue}"
                        )

                        new_command = {
                            "turret": horizontal_cmd,
                            "weight": aim_result.get("horizontal_weight", 1.0),
                        }
                        horizontal_command_queue.append(new_command)

            except Exception as e:
                import traceback

                logger.error(f"❌ Auto-aim 계산 오류: {str(e)}")

        # 수직 조준 로직 (TARGET 기반)
        if is_auto_aim_enabled == True and last_turret_y != 0.0:
            error = TARGET - last_turret_y
            direction = "R" if error > 0 else "F"
            w = min(0.15 * abs(error), 1.0)
            vertical_command_queue.clear()
            vertical_command_queue.append({"turret": direction, "weight": w})
        else:
            vertical_command_queue = []

    # 3. 수평/수직 명령 처리
    logger.debug(f"🎮 수평 큐 내용: {horizontal_command_queue}")
    logger.debug(f"🎮 수직 큐 내용: {vertical_command_queue}")

    if horizontal_command_queue:
        command = horizontal_command_queue.pop(0)
        logger.debug(f"🎮 수평 명령 반환: {command}")
        return command
    if vertical_command_queue:
        command = vertical_command_queue.pop(0)
        logger.debug(f"🎮 수직 명령 반환: {command}")
        return command

    logger.debug("🎮 기본 명령 반환: 정지")
    return {"turret": " ", "weight": 0.0}


# 📌 상태 정보 제공
@app.get("/get_status")
async def get_status():
    global simulator_status, turret_pitch_angle, last_turret_y, TARGET, horizontal_command_queue, error1
    simulator_status["turret_pitch"] = turret_pitch_angle
    error = 10.0
    try:
        if (
            len(horizontal_command_queue) == 0
            and last_turret_y is not None
            and TARGET is not None
        ):
            error = float(TARGET) - float(last_turret_y)
    except Exception as e:
        error = 10.0
    return {
        **simulator_status,
        "error": error,
        "dx_from_barrel": error1,
    }


# 📌 시뮬레이터 정보 수신
@app.post("/info")
async def receive_simulator_info(request: Request):
    global simulator_status, last_turret_y
    data = await request.json()
    last_turret_y = data.get("playerTurretY")
    simulator_status["player_pos"] = data.get(
        "playerPos", simulator_status["player_pos"]
    )
    simulator_status["player_speed"] = data.get(
        "playerSpeed", simulator_status["player_speed"]
    )
    simulator_status["player_health"] = data.get(
        "playerHealth", simulator_status["player_health"]
    )
    simulator_status["enemy_health"] = data.get(
        "enemyHealth", simulator_status["enemy_health"]
    )
    simulator_status["distance"] = data.get("distance", simulator_status["distance"])
    simulator_status["is_info_received"] = True
    simulator_status["last_info_time"] = time.time()
    simulator_status["player_turret_y"] = data.get(
        "playerTurretY", simulator_status["player_turret_y"]
    )
    simulator_status["player_turret_x"] = data.get(
        "playerTurretX", simulator_status["player_turret_x"]
    )
    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000, access_log=False)
