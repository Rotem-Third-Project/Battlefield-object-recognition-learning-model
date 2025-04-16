import cv2
from flask import Flask, request, jsonify
import os
import numpy as np
import torch
from ultralytics import YOLO
import datetime  # 타임스탬프 생성을 위해

# Deep SORT 패키지 임포트 (deep_sort_realtime 사용)
from deep_sort_realtime.deepsort_tracker import DeepSort

app = Flask(__name__)

# YOLO 모델 로드
model = YOLO("best_56000.pt")  # 미리 모델을 로드해두면 성능상 유리합니다.

# Deep SORT 트래커 초기화
tracker = DeepSort(max_age=30, n_init=3)

# 전역 변수: 바렐 중앙 좌표 및 허용 오차 설정
BARREL_X = 960
TOLERANCE = 50
# Action commands with weights (15+ variations)
action_command = []
# Move commands with weights (11+ variations)
SPEED = 1.0
move_command = [{"move": "W", "weight": SPEED}] * 30

# 칼만 필터 설정 (상태 벡터: [x, y, vx, vy], 측정: [x, y])
kalman = cv2.KalmanFilter(4, 2)
kalman.transitionMatrix = np.array(
    [[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32
)
kalman.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
kalman.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
kalman.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1
# 초기 상태 (예: 화면 중앙에 가까운 값으로 설정)
kalman.statePre = np.array([[960], [883], [0], [0]], dtype=np.float32)

# 전역 변수: 마지막 검출된 바운딩 박스 저장 (없으면 None)
last_candidate_box = None


def compute_turret_weight(dx, tolerance):
    abs_dx = abs(dx)
    if abs_dx <= tolerance:
        return 0.0
    extra = abs_dx - tolerance
    if extra <= 100:
        extra_weight = 0.1
    else:
        extra_weight = 0.1 + (extra - 100) * 0.008
    return min(extra_weight, 10.0)


@app.route("/detect", methods=["POST"])
def detect():
    global action_command, last_candidate_box
    action_command.clear()

    # 이미지 읽기 및 저장
    image = request.files["image"]
    # 임시 저장 파일은 계속 덮어쓰지 않고, 원본 이미지는 results 폴더에 저장할 예정
    image_path = "temp_image.jpg"
    image.save(image_path)

    results = model.track(image_path, persist=True, show=False)
    boxes = results[0].boxes
    detections = boxes.data.cpu().numpy()

    target_classes = {0: "Enemy", 1: "car", 7: "truck", 15: "rock"}
    result_json = []
    target_candidates = []

    def sigmoid(x):
        return 1 / (1 + np.exp(-x))

    # 후보 수집 및 후처리 (Enemy만 후보로 사용)
    for box in detections:
        class_id = int(box[5])
        if class_id in target_classes:
            raw_confidence = float(box[4])
            normalized_confidence = sigmoid(raw_confidence)
            detection_result = {
                "className": target_classes[class_id],
                "bbox": [float(coord) for coord in box[:4]],
                "confidence": normalized_confidence,
            }
            result_json.append(detection_result)
            if target_classes[class_id] in ["Enemy", "car"]:
                print(
                    "Enemy confidence:",
                    detection_result["confidence"],
                    target_classes[class_id],
                )
        if class_id == 0:  # Enemy만 추적 대상으로 사용
            x1, y1, x2, y2 = box[:4]
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            dist = abs(cx - BARREL_X)
            target_candidates.append((dist, cx, cy, box))

    # 이미지 로드
    img = cv2.imread(image_path)

    # 현재 타임스탬프 생성 (밀리초까지 포함, 예: "YYYY-MM-DD HH:MM:SS.mmm")
    now = datetime.datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    cv2.putText(
        img, timestamp_str, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2
    )

    # 칼만 필터 예측 단계 항상 수행
    predicted_state = kalman.predict()

    if target_candidates:
        target_candidates.sort(key=lambda x: x[0])
        _, cx, cy, candidate_box = target_candidates[0]

        # YOLO 검출된 중심 좌표로 칼만 필터 보정
        measurement = np.array([[np.float32(cx)], [np.float32(cy)]])
        corrected_state = kalman.correct(measurement)
        kx, ky = corrected_state[:2].flatten()
        print(
            "[Kalman] 측정값:",
            measurement.flatten(),
            "보정된 상태:",
            corrected_state.flatten(),
        )

        last_candidate_box = candidate_box  # 원본 바운딩박스 저장

        dx = kx - BARREL_X
        weight = compute_turret_weight(dx, TOLERANCE)
        if dx > TOLERANCE:
            action_command.append({"turret": "E", "weight": weight})
        elif dx < -TOLERANCE:
            action_command.append({"turret": "Q", "weight": weight})
        else:
            action_command.append({"turret": " ", "weight": 0.0})
        print(
            f"[Detection+Kalman] cx: {cx:.2f}, 보정 후: ({kx:.2f}, {ky:.2f}), dx: {dx:.2f}, weight: {weight:.2f}"
        )

        # 원본(이동 전) 바운딩박스 : YOLO에서 검출한 바운딩박스 (초록색)
        x1, y1, x2, y2 = candidate_box[:4]
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(
            img,
            "Original",
            (int(x1), int(y1) - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            2,
        )
        cv2.circle(img, (int(cx), int(cy)), radius=5, color=(0, 255, 0), thickness=-1)

        # 이동 후(보정 후) 바운딩박스: 원본 박스와 동일 크기로 중심만 수정 (빨간색)
        width = x2 - x1
        height = y2 - y1
        corrected_box = [
            kx - width / 2,
            ky - height / 2,
            kx + width / 2,
            ky + height / 2,
        ]
        cv2.rectangle(
            img,
            (int(corrected_box[0]), int(corrected_box[1])),
            (int(corrected_box[2]), int(corrected_box[3])),
            (0, 0, 255),
            2,
        )
        cv2.putText(
            img,
            "Corrected",
            (int(corrected_box[0]), int(corrected_box[1]) - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            2,
        )
        # 터렛 이동 명령이 있을 경우 이동 거리도 표시
        if weight > 0.0:
            turret_text = f"Turret Move: {weight:.2f}"
            cv2.putText(
                img,
                turret_text,
                (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 255),
                2,
            )
    else:
        # YOLO 검출이 없을 시 예측 상태 사용 및 이전 박스 크기 적용
        kx, ky = predicted_state[:2].flatten()
        dx = kx - BARREL_X
        weight = compute_turret_weight(dx, TOLERANCE)
        if dx > TOLERANCE:
            action_command.append({"turret": "E", "weight": weight})
        elif dx < -TOLERANCE:
            action_command.append({"turret": "Q", "weight": weight})
        else:
            action_command.append({"turret": " ", "weight": 0.0})
        print(
            "[Kalman] 대상 미검출 - 예측 상태:",
            predicted_state.flatten(),
            f", weight: {weight:.2f}",
        )

        if last_candidate_box is not None:
            x1, y1, x2, y2 = last_candidate_box[:4]
            width = x2 - x1
            height = y2 - y1
        else:
            width, height = 100, 100

        corrected_box = [
            kx - width / 2,
            ky - height / 2,
            kx + width / 2,
            ky + height / 2,
        ]
        cv2.rectangle(
            img,
            (int(corrected_box[0]), int(corrected_box[1])),
            (int(corrected_box[2]), int(corrected_box[3])),
            (0, 0, 255),
            2,
        )
        cv2.putText(
            img,
            "Predicted",
            (int(corrected_box[0]), int(corrected_box[1]) - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            2,
        )
        cv2.circle(img, (int(kx), int(ky)), radius=5, color=(0, 0, 255), thickness=-1)
        if weight > 0.0:
            turret_text = f"Turret Move: {weight:.2f}"
            cv2.putText(
                img,
                turret_text,
                (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 255),
                2,
            )

    # Deep SORT 통합 (추적 정보 출력)
    ds_detections = []
    for det in detections:
        bbox = [float(x) for x in det[:4]]
        conf = float(det[4])
        class_id = int(det[5])
        ds_det = [bbox, conf, class_id]
        ds_detections.append(ds_det)

    tracks = tracker.update_tracks(ds_detections, frame=img)
    for track in tracks:
        if track.is_confirmed():
            bbox = track.to_tlbr()  # [x1, y1, x2, y2]
            print(f"Track {track.track_id}: {bbox}")

    print("Action Command Queue:", action_command)

    for detection in result_json:
        bbox = detection["bbox"]
        class_name = detection["className"]
        x1_det, y1_det, x2_det, y2_det = map(int, bbox)
        cv2.rectangle(img, (x1_det, y1_det), (x2_det, y2_det), (255, 255, 0), 2)
        cv2.putText(
            img,
            class_name,
            (x1_det, y1_det - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 0),
            2,
        )

    # 결과 이미지를 저장할 폴더 생성 (존재하지 않으면)
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)
    # 파일명은 타임스탬프 기반 (특수문자 제거)
    filename = now.strftime("%Y%m%d_%H%M%S_%f")[:-3] + ".jpg"
    annotated_image_path = os.path.join(results_dir, filename)
    cv2.imwrite(annotated_image_path, img)
    print(f"Annotated image saved as: {annotated_image_path}")

    return jsonify(result_json)


@app.route("/info", methods=["POST"])
def info():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON received"}), 400
    print("📨 /info data received:", data)
    return jsonify({"status": "success", "control": ""})


@app.route("/update_position", methods=["POST"])
def update_position():
    data = request.get_json()
    if not data or "position" not in data:
        return jsonify({"status": "ERROR", "message": "Missing position data"}), 400
    try:
        x, y, z = map(float, data["position"].split(","))
        current_position = (int(x), int(z))
        print(f"📍 Position updated: {current_position}")
        return jsonify({"status": "OK", "current_position": current_position})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 400


@app.route("/get_move", methods=["GET"])
def get_move():
    global move_command
    if move_command:
        command = move_command.pop(0)
        print(f"🚗 Move Command: {command}")
        return jsonify(command)
    else:
        return jsonify({"move": "STOP", "weight": 1.0})


@app.route("/get_action", methods=["GET"])
def get_action():
    global action_command
    if action_command:
        command = action_command.pop(0)
        print(f"🔫 Action Command: {command}")
        return jsonify(command)
    else:
        return jsonify({"turret": " ", "weight": 0.0})


@app.route("/update_bullet", methods=["POST"])
def update_bullet():
    data = request.get_json()
    if not data:
        return jsonify({"status": "ERROR", "message": "Invalid request data"}), 400
    print(
        f"💥 Bullet Impact at X={data.get('x')}, Y={data.get('y')}, Z={data.get('z')}, Target={data.get('hit')}"
    )
    return jsonify({"status": "OK", "message": "Bullet impact data received"})


@app.route("/set_destination", methods=["POST"])
def set_destination():
    data = request.get_json()
    if not data or "destination" not in data:
        return jsonify({"status": "ERROR", "message": "Missing destination data"}), 400
    try:
        x, y, z = map(float, data["destination"].split(","))
        print(f"🎯 Destination set to: x={x}, y={y}, z={z}")
        return jsonify({"status": "OK", "destination": {"x": x, "y": y, "z": z}})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": f"Invalid format: {str(e)}"}), 400


@app.route("/update_obstacle", methods=["POST"])
def update_obstacle():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
    print("🪨 Obstacle Data:", data)
    return jsonify({"status": "success", "message": "Obstacle data received"})


@app.route("/init", methods=["GET"])
def init():
    config = {
        "startMode": "start",  # Options: "start" or "pause"
        "blStartX": 60,  # Blue Start Position
        "blStartY": 10,
        "blStartZ": 27.23,
        "rdStartX": 59,  # Red Start Position
        "rdStartY": 10,
        "rdStartZ": 280,
    }
    print("🛠️ Initialization config sent via /init:", config)
    return jsonify(config)


@app.route("/start", methods=["GET"])
def start():
    print("🚀 /start command received")
    return jsonify({"control": ""})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
