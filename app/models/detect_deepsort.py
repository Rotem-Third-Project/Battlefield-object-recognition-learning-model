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


async def process_image_array(
    image=None,
    yolo_model=None
):
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
            yolo_boxes=detections_yolo[:,:4]
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"status": "ERROR", "message": f"YOLO error: {str(e)}"},
            )

        target_classes = {0: "enemy", 2: "car", 7: "truck", 15: "rock"}

        tracks = []
        if tracker:
            # DeepSORT 입력 리스트 생성
            deepsort_input_for_tracking = []
            for box_data in enumerate(detections_yolo):
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

        return img_cv, yolo_boxes, yolo_idx_to_track_id
    except Exception as e:
        print(f"[process_image_array] 에러: {e}")
        return None, None, None