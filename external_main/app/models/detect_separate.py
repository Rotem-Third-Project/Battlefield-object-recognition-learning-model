from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
import numpy as np
import cv2
from pathlib import Path
from deep_sort_realtime.deepsort_tracker import DeepSort
import math

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
        polygon=False,  # 다각형 ROI 사용 여부
    )
except Exception as e:
    tracker = None

BARREL_X = 960
BARREL_Y = 883
TOLERANCE = 15

def compute_turret_weight(delta, tolerance=TOLERANCE):
    abs_delta = abs(delta)
    if abs_delta <= tolerance:
        return 0.0
    extra = abs_delta - tolerance
    if extra <= 200:
        return 0.1
    elif extra <= 300:
        return 0.5
    elif extra <= 500:
        return 0.8
    return 1.0

def predict_distance_front(y1, y2):
    y_len = y2 - y1
    return round(-0.080115*y_len + 0.000849*y_len**2 - 0.000003*y_len**3 + 3.126158, 4)

def predict_distance_side(y1, y2):
    y_len = y2 - y1
    return round(-0.052057*y_len + 0.000291*y_len**2 + 2.936584, 4)

def predict_distance_rear(y1, y2):
    y_len = y2 - y1
    return round(-0.045228*y_len + 0.000245*y_len**2 + 2.449860, 4)

def calculate_aiming_angle(distance_km: float, velocity_mps: float) -> float:
    g = 15
    R = distance_km * 1000
    ratio = (R * g) / (velocity_mps ** 2)
    if not -1 <= ratio <= 1:
        raise ValueError("명중 불가능한 조건")
    theta_rad = 0.5 * math.asin(ratio)
    return math.degrees(theta_rad)

def prioritize_by_class_and_area(detected_objects):
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



## yolo 객체 탐지 함수
async def process_image_array(
    image=None,
    yolo_model=None
):
    global TARGET
    try:
        img_cv = image
        if img_cv is None:
            return JSONResponse(
                status_code=400, content={"status": "ERROR", "message": "Invalid image"}
            )

        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)

        # YOLOv8으로 객체 탐지
        try:
            results = list(yolo_model.predict(img_cv, verbose=False, stream=True))
            detections_yolo = results[0].boxes.data.cpu().numpy()
            return img_cv, img_rgb, detections_yolo ###이미지, 객체 결과 반환
        
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"status": "ERROR", "message": f"YOLO error: {str(e)}"},
            )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "ERROR", "message": str(e)}
        )
    


def tracking(detections_yolo, img_rgb): ### yolo result 함수 인자로 받음
    target_classes = {0: "enemy", 2: "car", 7: "truck", 15: "rock"} ##yolo에도 필요한가?

    tracks = []
    if tracker:
        # DeepSORT 입력 리스트 생성
        deepsort_input_for_tracking = []
        for i, box_data in enumerate(detections_yolo):
            x1_ds, y1_ds, x2_ds, y2_ds, conf_ds, class_id_ds_float = box_data
            class_id_ds = int(class_id_ds_float)
            if class_id_ds in target_classes:  # target_classes는 YOLO class id -> name 맵
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
    else:
        tracks = []

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
    
    return  yolo_idx_to_track_id

       
def efficientnet_code(img_cv, detections_yolo, yolo_idx_to_track_id, img_rgb, efficientnet_model):
    target_classes = {0: "enemy", 2: "car", 7: "truck", 15: "rock"}
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
    filtered_results = []

    for idx, box in enumerate(detections_yolo):
        class_id = int(box[5])
        if class_id in target_classes:
            x1, y1, x2, y2 = map(int, box[:4])
            confidence = float(box[4])
            yolo_class_name = target_classes[class_id]

            current_track_id = yolo_idx_to_track_id.get(idx)

            ## efficientnet
            final_class_label_for_display = yolo_class_name
            prob_for_display = confidence
            threat_level_for_display = "Normal"

            if yolo_class_name == "enemy":
                    cropped_image = img_rgb[y1:y2, x1:x2]
                    if cropped_image.shape[0] == 0 or cropped_image.shape[1] == 0:
                        efficientnet_class_label = "Unknown"
                        efficientnet_prob = 0.0
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

    return