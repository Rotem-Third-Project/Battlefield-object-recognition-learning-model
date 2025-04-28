import cv2
from flask import Flask, request, jsonify
import numpy as np
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

app = Flask(__name__)

# YOLO 모델 로드 (미리 로드하여 추론 속도 향상)
model = YOLO("best.pt")

# 전역 변수: 기준(바렐) 중앙 좌표와 터렛 이동 허용 오차 설정
BARREL_X = 960  # 포신 중앙 x좌표
BARREL_Y = 883  # 포신 중앙 y좌표
TOLERANCE = 15  # 터렛 이동 허용 오차 (픽셀 단위)
action_command = []  # 터렛 등 액션 명령 저장 (예: {'turret': 'E', 'weight': 1.0})
SPEED = 1.0  # 이동 가중치
move_command = [{"move": "W", "weight": SPEED}] * 60

# (이전 코드에 칼만 필터가 있었으나, 현재는 사용하지 않으므로 제거)

# 전역 변수: 마지막 검출된 바운딩 박스 저장 (없으면 None)
last_candidate_box = None

# 기본 예시 (YAML 없이)
tracker = DeepSort(
    max_age=15,
    n_init=1,
    max_iou_distance=0.5,
    max_cosine_distance=0.4,
    nn_budget=100,
    embedder="mobilenet",  # appearance 모델 선택
    half=True,  # FP16 사용 여부
    embedder_gpu=True,  # GPU 사용 여부
)


def compute_turret_weight_X(delta, tolerance):
    """
    delta와 tolerance를 기반으로 터렛 회전 가중치(weight)를 계산합니다.
    extra가 속한 구간에 따라 weight를 고정된 값으로 반환합니다.
    """
    abs_delta = abs(delta)
    if abs_delta <= tolerance:
        return 0.0

    extra = abs_delta - tolerance

    if extra <= 200:
        return 0.1
    elif extra <= 300:
        return 0.5
    elif extra <= 500:
        return 0.7
    elif extra <= 900:
        return 1.0
    else:
        return 1.0


def compute_turret_weight_Y(delta, tolerance):
    """
    delta와 tolerance를 기반으로 터렛 회전 가중치(weight)를 계산합니다.
    extra가 속한 구간에 따라 weight를 고정된 값으로 반환합니다.
    """
    abs_delta = abs(delta)
    if abs_delta <= tolerance:
        return 0.0

    extra = abs_delta - tolerance

    if extra <= 200:
        return 0.1
    elif extra <= 300:
        return 0.2
    elif extra <= 500:
        return 0.5
    elif extra <= 900:
        return 1.0
    else:
        return 1.0


@app.route("/detect", methods=["POST"])
def detect():
    global action_command
    action_command.clear()

    # 1) 이미지 수신 및 저장
    image = request.files["image"]
    image_path = "temp_image.jpg"
    image.save(image_path)
    annotated_path = "annotated_" + (image.filename or "temp.jpg")
    img = cv2.imread(image_path)

    # YOLO 모델로 객체 검출 (deep_sort 추적도 포함)
    results = model.track(image_path, persist=True, show=False, conf=0.5)
    boxes = results[0].boxes
    detections = boxes.data.cpu().numpy()
    detections = results[0].boxes.data.cpu().numpy()

    # 3) Deep SORT 입력 리스트 생성 (픽셀 좌표 그대로)
    target_classes = {0: "Enemy", 1: "car", 7: "truck", 15: "rock"}
    detection_list = []
    scale = 3.5  # 이미지 확대 비율
    for box in detections:
        x1, y1, x2, y2, conf, cid = box
        w = x2 - x1
        h = y2 - y1
        cid = int(cid)
        print(
            f"[DEEPSORT INPUT] x1={x1:.1f}, y1={y1:.1f}, x2={x2:.1f}, y2={y2:.1f}, w={x2-x1:.1f}, h={y2-y1:.1f}"
        )
        if cid in target_classes:
            # 🔹 1. 박스 확장
            x1, y1, x2, y2 = map(float, (x1, y1, x2, y2))
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            w, h = (x2 - x1) * scale, (y2 - y1) * scale
            new_x1, new_y1 = cx - w / 2, cy - h / 2
            new_x2, new_y2 = cx + w / 2, cy + h / 2
            ltrb_box = [new_x1, new_y1, new_x2, new_y2]

            # 🔹 2. 이미지 크기 안으로 제한
            img_h, img_w = img.shape[:2]
            new_x1, new_y1 = max(0, new_x1), max(0, new_y1)
            new_x2, new_y2 = min(img_w - 1, new_x2), min(img_h - 1, new_y2)

            # 🔹 3. DeepSort용 리스트에 추가 (tlwh 형식)
            detection_list.append(
                (
                    [new_x1, new_y1, new_x2 - new_x1, new_y2 - new_y1],
                    float(conf),
                    target_classes[cid],
                )
            )

    # 4) 트래킹 업데이트
    tracks = tracker.update_tracks(detection_list, frame=img)

    # 5) detection_list 인덱스 → track_id 매핑 (IoU 확률 기반)
    def compute_iou(b1, b2):
        xA = max(b1[0], b2[0])
        yA = max(b1[1], b2[1])
        xB = min(b1[2], b2[2])
        yB = min(b1[3], b2[3])
        inter = max(0, xB - xA) * max(0, yB - yA)
        area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
        return inter / (area1 + area2 - inter) if (area1 + area2 - inter) > 0 else 0

    # 5) detection_list 인덱스 → track_id 매핑
    track_to_det = {}
    for track in tracks:
        if not track.is_confirmed():
            continue
        l, t, r, b = map(int, track.to_ltrb())  # ★ 수정
        track_box = [l, t, r, b]

        best_iou, best_idx = 0.0, None
        for idx, det in enumerate(detection_list):
            yolo_box = det[0]
            iou = compute_iou(ltrb_box, track_box)
            if iou > best_iou:
                best_iou, best_idx = iou, idx

        if best_iou >= 0.01:  # 임계값 상황에 맞게
            track_to_det[best_idx] = track.track_id

    # 6) 시각화: YOLO 박스(초록) + DeepSort 트랙 박스(빨강)
    # 6-1) YOLO detection boxes
    # YOLO 박스 시각화 및 좌표 출력
    for idx, box in enumerate(detections):
        x1, y1, x2, y2, conf, cid = box
        x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
        if int(cid) in target_classes:
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)  # 초록색 YOLO 박스
            cv2.putText(
                img,
                f"{target_classes[int(cid)]}:{conf:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2,
            )
            # YOLO 박스 좌표 출력
            print(f"YOLO 박스 {idx}: ({x1}, {y1}, {x2}, {y2})")

    # DeepSort 트랙박스 시각화 및 좌표 출력
    for track in tracks:
        if not track.is_confirmed():
            continue
        tid = track.track_id

        # ① 매칭된 YOLO 박스가 있으면 — 그걸 그대로 사용
        matched = False
        for det_idx, mapped_tid in track_to_det.items():
            if mapped_tid == tid:
                l, t, r, b = detection_list[det_idx][0]
                matched = True
                break
        if not matched:
            l, t, r, b = map(int, track.to_ltrb())
            print(f"[TRACK ID {tid}] box={l},{t},{r},{b} / w={r-l}, h={b-t}")
            # l, t, r, b = detection_list[det_idx][0]  # YOLO LTRB (정확)
            print(l, t, r, b)
        else:
            # ② 탐지가 없었던 트랙은 Kalman 예측값 그대로
            l, t, r, b = map(int, track.to_ltrb())
            print(f"else, l={l}, t={t}, r={r}, b={b}")
            print(f"[TRACK ID {tid}] box={l},{t},{r},{b} / w={r-l}, h={b-t}")
        cv2.rectangle(img, (l, t), (r, b), (0, 0, 255), 2)
        cv2.putText(
            img,
            f"Track-{tid}",
            (l, t - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            2,
        )

    # 7) JSON 응답 생성: className에 트랙 ID 포함
    def sigmoid(x):
        return 1 / (1 + np.exp(-x))

    result_json = []
    for idx, box in enumerate(detections):
        cid = int(box[5])
        if cid in target_classes:
            conf = sigmoid(float(box[4]))
            name = target_classes[cid]
            tid = track_to_det.get(idx)
            class_name = f"{name}-{tid}" if tid is not None else name
            result_json.append(
                {
                    "className": class_name,
                    "bbox": [float(c) for c in box[:4]],
                    "confidence": conf,
                }
            )

    # 8) 어노테이션 이미지 저장
    cv2.imwrite(annotated_path, img)

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
        "startMode": "start",
        "blStartX": 60,
        "blStartY": 10,
        "blStartZ": 27.23,
        "rdStartX": 59,
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
    app.run(host="0.0.0.0", port=5000, threaded=True)
