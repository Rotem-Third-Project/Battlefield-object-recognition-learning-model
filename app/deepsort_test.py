import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import logging
from pathlib import Path
import cv2
# 1. 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. YOLOv8 모델 로드 (사전 훈련된 coco 모델)
yolo_model = YOLO("models/yolo_weights/best.pt")  # 원하는 모델로 경로 변경

# 3. DeepSORT 트래커 초기화
tracker = DeepSort(
    max_age=30,
    n_init=1,
    max_iou_distance=0.6,
    max_cosine_distance=0.5,
    nn_budget=200,
    embedder="mobilenet",
    embedder_model_name="mobilenetv2_x1_0",
    embedder_wts=None,
    half=True,
    embedder_gpu=True,
    polygon=False,
)



# 4. IoU 함수
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


# 5. 동영상 객체 탐지 + 트래킹
def process_video(video_path, output_path=None):
    target_classes = {
        0: "person",
        2: "car",
        7: "truck",
        15: "dog",
    }  # COCO class id 예시
    cap = cv2.VideoCapture(str(video_path))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = None
    if output_path:
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = list(yolo_model.predict(frame, verbose=False, stream=True))
        detections_yolo = results[0].boxes.data.cpu().numpy()
        CONF_THRESHOLD = 0.5  # 0.25~0.4 추천
        detections_yolo = detections_yolo[detections_yolo[:, 4] > CONF_THRESHOLD]
        # DeepSORT 입력 변환
        deepsort_input_for_tracking = []
        for i, box_data in enumerate(detections_yolo):
            x1_ds, y1_ds, x2_ds, y2_ds, conf_ds, class_id_ds_float = box_data
            class_id_ds = int(class_id_ds_float)
            if class_id_ds in target_classes:
                w_ds = x2_ds - x1_ds
                h_ds = y2_ds - y1_ds
                deepsort_input_for_tracking.append(
                    (
                        [x1_ds, y1_ds, w_ds, h_ds],
                        conf_ds,
                        str(target_classes[class_id_ds]),
                    )
                )

        # 트래킹
        tracks = (
            tracker.update_tracks(deepsort_input_for_tracking, frame=img_rgb)
            if deepsort_input_for_tracking
            else []
        )

        # 트랙별로 박스/ID 시각화
        for track in tracks:
            if not track.is_confirmed():
                continue
            ltrb = track.to_ltrb()
            track_id = track.track_id
            x1, y1, x2, y2 = map(int, ltrb)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"ID:{track_id}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

        # 프레임 출력 또는 저장
        cv2.imshow("Object Tracking", frame)
        if out:
            out.write(frame)
        if cv2.waitKey(1) == 27:  # ESC to quit
            break
        frame_idx += 1

    cap.release()
    if out:
        out.release()
    cv2.destroyAllWindows()
    logger.info("Done!")


if __name__ == "__main__":
    video_path = "one30.mp4"  # 분석할 동영상 파일 경로
    output_path = "one30_deepsort_____s.mp4"  # 저장할 파일명 (없으면 저장 X)
    process_video(video_path, output_path)