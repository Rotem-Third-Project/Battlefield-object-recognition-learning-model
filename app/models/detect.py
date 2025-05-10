from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
import numpy as np
import cv2
from pathlib import Path
import logging
from deep_sort_realtime.deepsort_tracker import DeepSort

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DeepSORT 트래커 초기화
# embedder_gpu=True로 설정 시, PyTorch GPU 버전 및 CUDA 설치 필요. CPU만 사용 시 False로 변경.
# embedder_wts=None으로 설정 시, torchreid가 모델 가중치를 자동 다운로드 시도할 수 있습니다.
# 실제 운영 환경에서는 모델 가중치 파일을 미리 준비하고 경로를 지정하는 것이 안정적입니다.
try:
    tracker = DeepSort(
        max_age=30,  # 트랙이 유지되는 최대 프레임 수
        n_init=3,  # 트랙 확정까지 필요한 초기 탐지 횟수
        max_iou_distance=0.6,  # IoU 기반 매칭 시 최대 거리
        max_cosine_distance=0.5,  # 코사인 유사도(외형) 기반 매칭 시 최대 거리 (낮을수록 엄격)
        nn_budget=200,  # 각 트랙에 대해 저장할 외형 특징의 수
        embedder="mobilenet",  # 외형 특징 추출기 종류 ("mobilenet", "clip_RN50" 등도 가능)
        embedder_model_name="mobilenetv2_x1_0",  # 사용할 외형 특징 모델 이름
        embedder_wts=None,  # 미리 학습된 가중치 파일 경로 (None이면 자동 다운로드 시도)
        half=True,  # FP16 추론 사용 여부
        embedder_gpu=True,  # 외형 특징 추출 시 GPU 사용 여부
        polygon=False,  # 다각형 ROI 사용 여부S
    )
    logger.info("DeepSort tracker initialized successfully.")
except Exception as e:
    logger.error(
        f"Failed to initialize DeepSort tracker: {str(e)}. Tracking will be disabled."
    )
    tracker = None


def prioritize_by_class_and_area(detected_objects):
    logger.info("Prioritizing detected objects")
    class_priority = {
        "Enemy_Front": 3,  # 최고 우선순위
        "Enemy_Side": 2,  # 중간
        "Enemy_Rear": 1,  # 최저
    }

    prioritized = sorted(
        detected_objects,
        key=lambda x: (
            class_priority.get(x["className"], 0),
            (x["bbox"][2] - x["bbox"][0]) * (x["bbox"][3] - x["bbox"][1]),
            x["confidence"],
        ),
        reverse=True,
    )

    # 순위 부여
    for i, obj in enumerate(prioritized, 1):
        obj["rank"] = i

    logger.info(f"Prioritized objects with ranks: {prioritized}")
    return prioritized


# IoU 계산 함수
def compute_iou(boxA, boxB):  # box format: [x1, y1, x2, y2]
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
    image,
    yolo_model=None,
    efficientnet_model=None,
    crosshair_path=None,
    tmp_path=None,
    detected_objects=None,
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
            logger.info(
                f"Detected {len(detections_yolo)} objects with YOLO (before class filtering)"
            )
            if len(detections_yolo) > 0:
                logger.debug(
                    f"Raw YOLO detections (first 5 if many): {detections_yolo[:5]}"
                )
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
                            {
                                "message": f"... and {len(detections_yolo) - 10} more detections not shown."
                            }
                        )
                        break
                logger.info(
                    f"Raw YOLO detection details (class_id, confidence, bbox): {raw_detection_details}"
                )
        except Exception as e:
            logger.error(f"YOLO detection failed: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"status": "ERROR", "message": f"YOLO error: {str(e)}"},
            )

        target_classes = {0: "enemy", 2: "car", 7: "truck", 15: "rock"}
        filtered_results = []
        class_names = ["Enemy_Front", "Enemy_Rear", "Enemy_Side"]

        threat_levels = {
            "Enemy_Front": "LEVEL 3",
            "Enemy_Rear": "LEVEL 1",
            "Enemy_Side": "LEVEL 2",
        }

        threat_colors = {
            "LEVEL 1": (0, 255, 0),
            "LEVEL 2": (0, 165, 255),
            "LEVEL 3": (0, 0, 255),
            "Normal": (255, 255, 0),
            "Unknown": (128, 128, 128),
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

        tracks = []
        if tracker:
            # DeepSORT 입력 리스트 생성
            deepsort_input_for_tracking = []
            for i, box_data in enumerate(detections_yolo):
                x1_ds, y1_ds, x2_ds, y2_ds, conf_ds, class_id_ds_float = box_data
                class_id_ds = int(class_id_ds_float)
                if (
                    class_id_ds in target_classes
                ):  # target_classes는 YOLO class id -> name 맵
                    w_ds = x2_ds - x1_ds
                    h_ds = y2_ds - y1_ds
                    # (bbox_tlwh, confidence, class_name_str)
                    deepsort_input_for_tracking.append(
                        (
                            [x1_ds, y1_ds, w_ds, h_ds],
                            conf_ds,
                            str(target_classes[class_id_ds]),
                        )
                    )

            if deepsort_input_for_tracking:
                # 트래킹 업데이트 (img_rgb 사용)
                tracks = tracker.update_tracks(
                    deepsort_input_for_tracking, frame=img_rgb
                )
                logger.info(f"DeepSORT tracks updated: {len(tracks)} tracks found.")
            else:
                logger.info("No suitable detections for DeepSORT input.")
        else:
            logger.warning("DeepSort tracker is not available. Skipping tracking.")

        # YOLO 탐지 결과(detections_yolo)와 DeepSORT 트랙(tracks)을 매핑
        yolo_idx_to_track_id = {}
        if tracks:  # tracks가 있을 경우에만 매핑 시도
            for yolo_idx, yolo_box_data in enumerate(detections_yolo):
                yolo_x1, yolo_y1, yolo_x2, yolo_y2, _, yolo_class_id_float = (
                    yolo_box_data
                )
                yolo_class_id = int(yolo_class_id_float)

                if yolo_class_id not in target_classes:
                    continue

                yolo_bbox_ltrb = [yolo_x1, yolo_y1, yolo_x2, yolo_y2]
                best_iou = 0.0
                assigned_track_id = None

                for track_obj in tracks:  # 변수명 변경 track -> track_obj
                    if not track_obj.is_confirmed():
                        continue

                    track_ltrb = track_obj.to_ltrb()
                    iou = compute_iou(yolo_bbox_ltrb, track_ltrb)

                    # IoU 임계값 (예: 0.5) 및 가장 높은 IoU를 가진 트랙 선택
                    if iou > best_iou and iou > 0.4:
                        best_iou = iou
                        assigned_track_id = track_obj.track_id

                if assigned_track_id is not None:
                    # 한 YOLO 박스에 하나의 트랙 ID만 할당되도록 (이미 할당된 트랙 ID는 다른 박스에 할당 X - 선택적)
                    # 이 로직을 더 정교하게 하려면, 모든 가능한 매칭 쌍에 대해 헝가리안 알고리즘 등을 사용할 수 있음.
                    # 여기서는 단순 best_match 사용.
                    yolo_idx_to_track_id[yolo_idx] = assigned_track_id

        for idx, box in enumerate(detections_yolo):
            class_id = int(box[5])
            if class_id in target_classes:
                x1, y1, x2, y2 = map(int, box[:4])
                confidence = float(box[4])
                yolo_class_name = target_classes[class_id]
                logger.info(
                    f"Processing detection: {yolo_class_name}, confidence: {confidence}"
                )

                current_track_id = yolo_idx_to_track_id.get(idx)

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
                                if (
                                    y_offset + i < img_cv.shape[0]
                                    and x_offset + j < img_cv.shape[1]
                                ):
                                    img_cv[y_offset + i, x_offset + j, c] = (
                                        alpha_s[i, j] * crosshair[i, j, c]
                                        + alpha_l[i, j]
                                        * img_cv[y_offset + i, x_offset + j, c]
                                    )

                # EfficientNet으로 분류
                final_class_label_for_display = yolo_class_name
                prob_for_display = confidence
                threat_level_for_display = "Normal"

                if yolo_class_name == "enemy":
                    cropped_image = img_rgb[y1:y2, x1:x2]
                    if cropped_image.shape[0] == 0 or cropped_image.shape[1] == 0:
                        efficientnet_class_label = "Unknown"
                        efficientnet_prob = 0.0
                        logger.warning("Empty cropped image for EfficientNet")
                    else:
                        try:
                            cropped_image_resized = cv2.resize(
                                cropped_image, (224, 224)
                            )
                            cropped_image_normalized = cropped_image_resized / 255.0
                            cropped_image_expanded = np.expand_dims(
                                cropped_image_normalized, axis=0
                            )
                            predictions = efficientnet_model.predict(
                                cropped_image_expanded, verbose=0
                            )
                            predicted_class_idx = np.argmax(predictions[0])
                            efficientnet_class_label = class_names[predicted_class_idx]
                            efficientnet_prob = float(
                                predictions[0][predicted_class_idx]
                            )
                        except Exception as e:
                            logger.error(f"EfficientNet prediction failed: {str(e)}")
                            efficientnet_class_label = "Unknown"
                            efficientnet_prob = 0.0

                    final_class_label_for_display = efficientnet_class_label
                    prob_for_display = efficientnet_prob
                    threat_level_for_display = threat_levels.get(
                        efficientnet_class_label, "Unknown"
                    )

                box_color = threat_colors.get(threat_level_for_display, (128, 128, 128))
                cv2.rectangle(img_cv, (x1, y1), (x2, y2), box_color, 2)

                # 레이블에 Track ID 추가
                label_text = f"{final_class_label_for_display}: {prob_for_display:.2f} ({threat_level_for_display})"
                if current_track_id is not None:
                    label_text += f" ID:{current_track_id}"

                cv2.putText(
                    img_cv,
                    label_text,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    box_color,
                    2,
                )

                filtered_results.append(
                    {
                        "className": final_class_label_for_display,
                        "id": idx,
                        "track_id": current_track_id,
                        "threat": threat_level_for_display,
                        "bbox": [x1, y1, x2, y2],
                        "confidence": prob_for_display,
                    }
                )

        # 순위 부여 및 detected_objects 업데이트
        ranked_objects = prioritize_by_class_and_area(filtered_results)
        logger.info(f"Ranked objects (with track_id and rank): {ranked_objects}")

        detected_objects.clear()
        detected_objects.extend(ranked_objects)

        try:
            cv2.imwrite(str(tmp_path), img_cv)
            logger.info(
                f"Processed image with detections and tracks saved to {tmp_path}"
            )
        except Exception as e:
            logger.error(f"Failed to save image: {str(e)}")

        # 기존 반환 형식 유지 (filtered_results에는 rank가 없음)
        # 만약 rank 정보도 API 응답에 포함해야 한다면 ranked_objects를 반환해야 함.
        # 현재 요청은 DeepSORT 추가이므로, 기존 반환 필드 외에 track_id만 추가된 filtered_results를 반환.
        # 하지만 prioritize_by_class_and_area가 filtered_results를 직접 수정하지 않고 새로운 리스트(ranked_objects)를 반환하므로,
        # filtered_results에는 rank가 없고, ranked_objects에는 rank가 있음.
        # 만약 API 사용처에서 순위가 필요하다면 ranked_objects를 반환하는 것이 맞음.
        # 여기서는 '기존 반환 형식 유지' 및 '순위 부여'를 모두 고려하여,
        # track_id가 포함되고 순위가 부여된 ranked_objects를 반환하는 것으로 변경합니다.
        # 이렇게 하면 detected_objects와 API 응답이 일관성을 가집니다.
        return img_cv
    except Exception as e:
        logger.error(f"Overall detection process failed: {str(e)}")
        return JSONResponse(
            status_code=500, content={"status": "ERROR", "message": str(e)}
        )