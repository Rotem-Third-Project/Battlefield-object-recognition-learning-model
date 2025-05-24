from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
import numpy as np
import cv2
from pathlib import Path
from deep_sort_realtime.deepsort_tracker import DeepSort
import math
import logging
import time

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
        polygon=False,  # 다각형 ROI 사용 여부
    )
    logger.info("DeepSort tracker initialized successfully.")
except Exception as e:
    logger.error(
        f"Failed to initialize DeepSort tracker: {str(e)}. Tracking will be disabled."
    )
    tracker = None

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
    yolo_model=None,
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

        # 이미지 정보 로깅
        logger.info(f"입력 이미지 크기: {img_cv.shape}")
        
        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        logger.info("Image loaded and converted to RGB")

        # YOLOv8으로 객체 탐지
        try:
            logger.info("YOLO 모델로 객체 탐지 시작")
            if yolo_model is None:
                logger.error("YOLO 모델이 초기화되지 않았습니다.")
                return JSONResponse(
                    status_code=500, 
                    content={"status": "ERROR", "message": "YOLO model is not initialized"}
                )
                
            start_time = time.time()
            results = list(yolo_model.predict(img_cv, verbose=False, stream=True))
            yolo_time = time.time() - start_time
            logger.info(f"YOLO 추론 시간: {yolo_time:.4f}초")
            
            if not results or len(results) == 0:
                logger.warning("YOLO 모델이 결과를 반환하지 않았습니다.")
                detected_objects.clear()
                return []
                
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
            else:
                logger.warning("YOLO 탐지 결과가 없습니다.")
        except Exception as e:
            logger.error(f"YOLO detection failed: {str(e)}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={"status": "ERROR", "message": f"YOLO error: {str(e)}"},
            )
        
        target_classes = {0: "enemy", 2: "car", 7: "truck", 15: "rock"}
        logger.info(f"타겟 클래스: {target_classes}")

        tracks = []
        filtered_objects=[]
        
        # DeepSORT 트래킹 시도
        try:
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
                    logger.info(f"DeepSORT 입력 객체 수: {len(deepsort_input_for_tracking)}")
                    # 트래킹 업데이트 (img_rgb 사용)
                    try:
                        tracks = tracker.update_tracks(
                            deepsort_input_for_tracking, frame=img_rgb
                        )
                        logger.info(f"DeepSORT tracks updated: {len(tracks)} tracks found.")
                    except Exception as tracker_error:
                        logger.error(f"DeepSORT 트래킹 오류: {str(tracker_error)}")
                        import traceback
                        logger.error(f"트래킹 상세 오류: {traceback.format_exc()}")
                else:
                    logger.info("No suitable detections for DeepSORT input.")
            else:
                logger.warning("DeepSort tracker is not available. Skipping tracking.")
        except Exception as track_error:
            logger.error(f"트래킹 처리 중 예외 발생: {str(track_error)}")
            import traceback
            logger.error(f"트래킹 전체 오류: {traceback.format_exc()}")
            
        
        # YOLO 탐지 결과(detections_yolo)와 DeepSORT 트랙(tracks)을 매핑
        try:
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
                    
                logger.info(f"YOLO-Track 매핑 결과: {len(yolo_idx_to_track_id)}개 매핑됨")
        except Exception as mapping_error:
            logger.error(f"YOLO-Track 매핑 오류: {str(mapping_error)}")
            import traceback
            logger.error(f"매핑 상세 오류: {traceback.format_exc()}")

        try:
            # 최종 결과 생성
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
                    
                    # 클래스명에 따른 위험 등급 설정
                    threat_level = "Normal"
                    if yolo_class_name == "enemy":
                        # 적 객체에 대한 위험도 설정 (거리, 방향 등에 따라 조정 가능)
                        if confidence > 0.8:
                            threat_level = "LEVEL 3"  # 고위험
                        elif confidence > 0.5:
                            threat_level = "LEVEL 2"  # 중위험
                        else:
                            threat_level = "LEVEL 1"  # 저위험
                    
                    filtered_objects.append(
                        {
                            "className": yolo_class_name,
                            "track_id": current_track_id,
                            "bbox": [x1, y1, x2, y2],
                            "confidence": confidence,
                            "threat": threat_level,
                        }
                    )
            
            logger.info(f"최종 결과 객체 수: {len(filtered_objects)}")
        except Exception as result_error:
            logger.error(f"결과 생성 오류: {str(result_error)}")
            import traceback
            logger.error(f"결과 상세 오류: {traceback.format_exc()}")

        # 결과 업데이트 및 반환
        try:
            if detected_objects is not None:
                detected_objects.clear()
                detected_objects.extend(filtered_objects)
                logger.info(f"detected_objects 목록 업데이트 완료 ({len(detected_objects)}개)")
            else:
                logger.warning("detected_objects가 None입니다")
            
            return filtered_objects
        except Exception as update_error:
            logger.error(f"결과 업데이트 오류: {str(update_error)}")
            import traceback
            logger.error(f"업데이트 상세 오류: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500, 
                content={"status": "ERROR", "message": f"Result update error: {str(update_error)}"}
            )
    except Exception as e:
        logger.error(f"Overall detection process failed: {str(e)}")
        import traceback
        logger.error(f"전체 프로세스 오류: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500, content={"status": "ERROR", "message": str(e)}
        )