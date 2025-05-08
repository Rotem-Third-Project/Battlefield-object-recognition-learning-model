from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
import numpy as np
import cv2
from pathlib import Path
import logging
import math

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def prioritize_by_class_and_area(detected_objects, img_shape=None):
    logger.info("Prioritizing detected objects with weighted scoring")
    if not detected_objects:
        logger.info("No objects to prioritize")
        return []

    # 클래스별 가중치
    class_priority = {
        "Enemy_Front": 1.0,  # 최고 우선순위
        "Enemy_Side": 0.6,   # 중간
        "Enemy_Rear": 0.3,   # 최저
        "car": 0.1,
        "truck": 0.1,
        "rock": 0.1
    }

    # 이미지 크기 처리
    if img_shape is not None:
        img_height, img_width = img_shape[:2]
        max_distance = math.sqrt(img_width**2 + img_height**2)  # 최대 거리 (대각선)
        logger.info(f"Using img_shape: {img_width}x{img_height}")
    else:
        logger.warning("img_shape not provided, using default 1920x1080 for distance calculation")
        img_width, img_height = 1920, 1080
        max_distance = math.sqrt(img_width**2 + img_height**2)

    # 세로 길이 최대값 계산
    heights = [(obj['bbox'][3] - obj['bbox'][1]) for obj in detected_objects]
    max_height = max(heights) if heights else 1.0

    # 가중치 계산
    scored_objects = []
    for obj in detected_objects:
        # 1. 클래스 가중치
        class_score = class_priority.get(obj['className'], 0.1)

        # 2. 세로 길이 가중치
        height = obj['bbox'][3] - obj['bbox'][1]
        height_score = height / max_height if max_height > 0 else 0.0

        # 3. 포신과의 거리 가중치 (Unity 화면 중심 = 크로스헤어)
        center_x = (obj['bbox'][0] + obj['bbox'][2]) / 2
        center_y = (obj['bbox'][1] + obj['bbox'][3]) / 2
        distance = math.sqrt((center_x - img_width/2)**2 + (center_y - img_height/2)**2)
        distance_score = 1.0 - (distance / max_distance) if max_distance > 0 else 0.0

        # 종합 점수
        total_score = (0.5 * class_score) + (0.3 * height_score) + (0.2 * distance_score)
        scored_objects.append({
            'obj': obj,
            'total_score': total_score,
            'class_score': class_score,
            'height_score': height_score,
            'distance_score': distance_score
        })
        logger.info(f"Object ID={obj['id']}, Class={obj['className']}, "
                    f"TotalScore={total_score:.3f} (Class={class_score:.2f}, "
                    f"Height={height_score:.2f}, Distance={distance_score:.2f})")

    # 점수 내림차순 정렬
    scored_objects.sort(key=lambda x: x['total_score'], reverse=True)

    # 순위 부여
    prioritized = [item['obj'] for item in scored_objects]
    for i, obj in enumerate(prioritized, 1):
        obj['rank'] = i

    logger.info(f"Prioritized objects with ranks: {[obj['rank'] for obj in prioritized]}")
    return prioritized

async def detect(image: UploadFile = File(...), yolo_model=None, efficientnet_model=None, crosshair_path=None, tmp_path=None, detected_objects=None):
    try:
        logger.info("Starting image detection")
        image_bytes = await image.read()
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img_cv is None:
            logger.error("Failed to decode image")
            return JSONResponse(status_code=400, content={"status": "ERROR", "message": "Invalid image"})
        
        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        logger.info("Image loaded and converted to RGB")

        # YOLOv8으로 객체 탐지
        try:
            results = list(yolo_model.predict(img_cv, verbose=False, stream=True))
            detections = results[0].boxes.data.cpu().numpy()
            logger.info(f"Detected {len(detections)} objects with YOLO")
        except Exception as e:
            logger.error(f"YOLO detection failed: {str(e)}")
            return JSONResponse(status_code=500, content={"status": "ERROR", "message": f"YOLO error: {str(e)}"})

        target_classes = {0: "enemy", 2: "car", 7: "truck", 15: "rock"}
        filtered_results = []
        class_names = ["Enemy_Front", "Enemy_Rear", "Enemy_Side"]

        threat_levels = {
            "Enemy_Front": "LEVEL 3",
            "Enemy_Rear": "LEVEL 1",
            "Enemy_Side": "LEVEL 2"
        }

        threat_colors = {
            "LEVEL 1": (0, 255, 0),
            "LEVEL 2": (0, 165, 255),
            "LEVEL 3": (0, 0, 255),
            "Normal": (128, 128, 128),
            "Unknown": (128, 128, 128)
        }

        # 크로스헤어 로드
        try:
            crosshair = cv2.imread(str(crosshair_path), cv2.IMREAD_UNCHANGED)
            if crosshair is None:
                raise ValueError("Crosshair image not found")
            crosshair = cv2.resize(crosshair, (65, 65), interpolation=cv2.INTER_AREA)
            logger.info("Crosshair loaded")
        except Exception as e:
            logger.error(f"Failed to load crosshair: {str(e)}")
            crosshair = None

        for idx, box in enumerate(detections):
            class_id = int(box[5])
            if class_id in target_classes:
                x1, y1, x2, y2 = map(int, box[:4])
                confidence = float(box[4])
                class_name = target_classes[class_id]
                logger.info(f"Processing detection: {class_name}, confidence: {confidence}")

                # 크로스헤어 오버레이
                if crosshair is not None:
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

                # EfficientNetB0으로 분류
                if class_name == "enemy":
                    cropped_image = img_rgb[y1:y2, x1:x2]
                    if cropped_image.shape[0] == 0 or cropped_image.shape[1] == 0:
                        class_label = "Unknown"
                        prob = 0.0
                        threat_level = "Unknown"
                        logger.warning("Empty cropped image for EfficientNetB0")
                    else:
                        try:
                            cropped_image = cv2.resize(cropped_image, (224, 224))
                            cropped_image = cropped_image / 255.0
                            cropped_image = np.expand_dims(cropped_image, axis=0)
                            predictions = efficientnet_model.predict(cropped_image, verbose=0)
                            predicted_class = np.argmax(predictions[0])
                            class_label = class_names[predicted_class]
                            prob = float(predictions[0][predicted_class])
                            threat_level = threat_levels.get(class_label, "Unknown")
                            logger.info(f"EfficientNetB0 classified: {class_label}, prob: {prob}")
                        except Exception as e:
                            logger.error(f"EfficientNetB0 prediction failed: {str(e)}")
                            class_label = "Unknown"
                            prob = 0.0
                            threat_level = "Unknown"
                else:
                    class_label = class_name
                    prob = confidence
                    threat_level = "Normal"

                box_color = threat_colors.get(threat_level, (128, 128, 128))
                cv2.rectangle(img_cv, (x1, y1), (x2, y2), box_color, 2)
                label = f"{class_label}: {prob:.2f} ({threat_level})"
                cv2.putText(img_cv, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

                filtered_results.append({
                    'className': class_label,
                    'id': idx,
                    'threat': threat_level,
                    'bbox': [x1, y1, x2, y2],
                    'confidence': prob
                })

        # 순위 부여 및 detected_objects 업데이트
        ranked_objects = prioritize_by_class_and_area(filtered_results, img_cv.shape)
        logger.info(f"Ranked objects: {ranked_objects}")

        detected_objects.clear()
        detected_objects.extend(ranked_objects)

        try:
            cv2.imwrite(str(tmp_path), img_cv)
            logger.info("Image saved to tmp_path")
        except Exception as e:
            logger.error(f"Failed to save image: {str(e)}")

        # 기존 반환 형식 유지
        return JSONResponse(content=filtered_results)
    except Exception as e:
        logger.error(f"Detection failed: {str(e)}")
        return JSONResponse(status_code=500, content={"status": "ERROR", "message": str(e)})