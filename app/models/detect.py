from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
import numpy as np
import cv2
from pathlib import Path
from deep_sort_realtime.deepsort_tracker import DeepSort
import math
import logging
import tensorflow as tf
import time
import base64

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DeepSort 트래커 초기화
try:
    tracker = DeepSort(
        max_age=60,
        n_init=3,
        max_iou_distance=0.7,
        max_cosine_distance=0.4,
        nn_budget=200,
        embedder="mobilenet",
        embedder_model_name="mobilenetv2_x1_0",
        embedder_wts=None,
        half=True,
        embedder_gpu=True,
        polygon=False,
    )
    logger.info("DeepSort tracker initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize DeepSort tracker: {str(e)}. Tracking will be disabled.")
    tracker = None

# IoU 계산 함수
def compute_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    iou = (
        interArea / float(boxAArea + boxBArea - interArea)
        if (boxAArea + boxBArea - interArea) > 0
        else 0
    )
    return iou

async def process_image_array(
    image=None,
    yolo_model=None,
    detected_objects=None,
    image_size=(2560, 1440),
):
    try:
        logger.info("Starting image detection")
        img_cv = image
        if img_cv is None:
            logger.error("Failed to decode image")
            return JSONResponse(
                status_code=400, content={"status": "ERROR", "message": "Invalid image"}
            )

        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        logger.info("Image loaded and converted to RGB")

        # YOLOv8으로 객체 탐지
        try:
            results = list(yolo_model.predict(img_cv, verbose=False, stream=True))
            detections_yolo = results[0].boxes.data.cpu().numpy()
            logger.info(f"Detected {len(detections_yolo)} objects with YOLO")
            if len(detections_yolo) > 0:
                logger.debug(f"Raw YOLO detections (first 5 if many): {detections_yolo[:5]}")
                raw_detection_details = []
                for i, det_box in enumerate(detections_yolo):
                    raw_class_id = int(det_box[5])
                    raw_confidence = float(det_box[4])
                    raw_detection_details.append(
                        {
                            "original_idx": i,
                            "class_id": raw_class_id,
                            "confidence": raw_confidence,
                            "bbox_ltrb": det_box[:4].tolist(),
                        }
                    )
                    if i >= 10 and len(detections_yolo) > 10:
                        raw_detection_details.append(
                            {"message": f"... and {len(detections_yolo) - 10} more detections not shown."}
                        )
                        break
                logger.info(f"Raw YOLO detection details: {raw_detection_details}")
        except Exception as e:
            logger.error(f"YOLO detection failed: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"status": "ERROR", "message": f"YOLO error: {str(e)}"},
            )
        
        target_classes = {0: "enemy", 2: "car", 7: "truck", 15: "rock"}
        filtered_objects = []

        tracks = []
        if tracker:
            deepsort_input_for_tracking = []
            for i, box_data in enumerate(detections_yolo):
                x1_ds, y1_ds, x2_ds, y2_ds, conf_ds, class_id_ds_float = box_data
                class_id_ds = int(class_id_ds_float)
                if class_id_ds in target_classes:
                    w_ds = x2_ds - x1_ds
                    h_ds = y2_ds - y1_ds
                    deepsort_input_for_tracking.append(
                        ([x1_ds, y1_ds, w_ds, h_ds], conf_ds, str(target_classes[class_id_ds]))
                    )
            if deepsort_input_for_tracking:
                tracks = tracker.update_tracks(deepsort_input_for_tracking, frame=img_rgb)
                logger.info(f"DeepSORT tracks updated: {len(tracks)} tracks found.")
            else:
                logger.info("No suitable detections for DeepSORT input.")
        else:
            logger.warning("DeepSort tracker is not available. Skipping tracking.")
            
        yolo_idx_to_track_id = {}
        if tracks:
            for yolo_idx, yolo_box_data in enumerate(detections_yolo):
                yolo_x1, yolo_y1, yolo_x2, yolo_y2, _, yolo_class_id_float = yolo_box_data
                yolo_class_id = int(yolo_class_id_float)
                if yolo_class_id not in target_classes:
                    continue
                yolo_bbox_ltrb = [yolo_x1, yolo_y1, yolo_x2, yolo_y2]
                best_iou = 0.0
                assigned_track_id = None
                for track_obj in tracks:
                    if not track_obj.is_confirmed():
                        continue
                    track_ltrb = track_obj.to_ltrb()
                    iou = compute_iou(yolo_bbox_ltrb, track_ltrb)
                    if iou > best_iou and iou > 0.5:
                        best_iou = iou
                        assigned_track_id = track_obj.track_id
                if assigned_track_id is not None:
                    yolo_idx_to_track_id[yolo_idx] = assigned_track_id

        for idx, box in enumerate(detections_yolo):
            class_id = int(box[5])
            if class_id in target_classes:
                x1, y1, x2, y2 = map(int, box[:4])
                confidence = float(box[4])
                yolo_class_name = target_classes[class_id]
                logger.info(f"Processing detection: {yolo_class_name}, confidence: {confidence}")
                current_track_id = yolo_idx_to_track_id.get(idx, f"temp_{idx}")

                crop_data = None
                if yolo_class_name == "enemy":
                    cropped = img_cv[y1:y2, x1:x2]
                    if cropped.size > 0:
                        _, buffer = cv2.imencode('.jpg', cropped)
                        crop_data = base64.b64encode(buffer).decode('utf-8')
                        logger.info(f"Encoded crop image for track_id: {current_track_id}")

                obj = {
                    "className": yolo_class_name,
                    "track_id": current_track_id,
                    "bbox": [x1, y1, x2, y2],
                    "confidence": confidence
                }
                
                filtered_objects.append(obj)

        detected_objects.clear()
        detected_objects.extend(filtered_objects)
        return filtered_objects
    except Exception as e:
        logger.error(f"Overall detection process failed: {str(e)}")
        return JSONResponse(
            status_code=500, content={"status": "ERROR", "message": str(e)}
        )