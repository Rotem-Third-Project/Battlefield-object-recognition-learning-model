import cv2
from flask import Flask, request, jsonify
import os
import numpy as np
import torch
from ultralytics import YOLO

app = Flask(__name__)

# YOLO 모델 로드 (미리 로드하여 추론 속도 향상)
model = YOLO("yolov12_weight.pt")

# 전역 변수: 기준(바렐) 중앙 좌표와 터렛 이동 허용 오차 설정
BARREL_X = 960  # 포신 중앙 x좌표
BARREL_Y = 883  # 포신 중앙 y좌표
TOLERANCE = 15  # 터렛 이동 허용 오차 (픽셀 단위)
action_command = []  # 터렛 등 액션 명령 저장 (예: {'turret': 'E', 'weight': 1.0})
SPEED = 0.5  # 이동 가중치
move_command = [{"move": "W", "weight": SPEED}] * 60

# (이전 코드에 칼만 필터가 있었으나, 현재는 사용하지 않으므로 제거)

# 전역 변수: 마지막 검출된 바운딩 박스 저장 (없으면 None)
last_candidate_box = None


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
        return 0.4
    elif extra <= 500:
        return 0.5
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
    global action_command, last_candidate_box
    action_command.clear()

    # 이미지 수신 및 저장
    image = request.files["image"]
    image_path = "temp_image.jpg"
    image.save(image_path)

<<<<<<< HEAD
    # YOLO 모델로 객체 검출 (deep_sort 추적도 포함)
    results = model.track(image_path, persist=True, show=False, conf = 0.5)
    boxes = results[0].boxes
    detections = boxes.data.cpu().numpy()
=======
    # YOLO 객체 추적
    results = model.track(image_path, persist=True, show=False)
    detections = results[0].boxes.data.cpu().numpy()
>>>>>>> 1dc3599869f7b32552eb6e3b39c1d75d1302b8c0

    target_classes = {0: "Enemy", 1: "car", 7: "truck", 15: "rock"}
    result_json = []
    target_candidates = []

    def sigmoid(x):
        return 1 / (1 + np.exp(-x))

    # 'Enemy' 클래스만 후보로 수집
    for box in detections:
        class_id = int(box[5])
        if class_id in target_classes:
            conf = sigmoid(float(box[4]))
            result_json.append(
                {
                    "className": target_classes[class_id],
                    "bbox": [float(c) for c in box[:4]],
                    "confidence": conf,
                }
            )
        if class_id == 0:
            x1, y1, x2, y2 = box[:4]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            dist = abs(cx - BARREL_X)
            target_candidates.append((dist, cx, cy, box))

    # 최적 타겟 선택
    if target_candidates:
        target_candidates.sort(key=lambda x: x[0])
        _, cx, cy, candidate_box = target_candidates[0]

        dx = cx - BARREL_X
        dy = cy - BARREL_Y

        # x, y 축별로 weight 계산
        weight_x = compute_turret_weight_X(dx, TOLERANCE)
        weight_y = compute_turret_weight_Y(dy, TOLERANCE)

        # 수평 회전 (Q/E)
        if dx > TOLERANCE:
            action_command.append({"turret": "E", "weight": weight_x})
        elif dx < -TOLERANCE:
            action_command.append({"turret": "Q", "weight": weight_x})

        # 수직 회전 (R/F)
        if dy > TOLERANCE:
            action_command.append({"turret": "F", "weight": weight_y})
            print("actionnnnnnnnnn", action_command)
        elif dy < -TOLERANCE:
            action_command.append({"turret": "R", "weight": weight_y})
            print("actionnnnnnnnnn", action_command)
        # 둘 다 오차 범위 내에 있으면 정지
        if abs(dx) <= TOLERANCE and abs(dy) <= TOLERANCE:
            action_command.append({"turret": " ", "weight": 0.0})

        print(
            f"[Detection] cx: {cx:.2f}, cy: {cy:.2f}, dx: {dx:.2f}, dy: {dy:.2f}, "
            f"wx: {weight_x:.2f}, wy: {weight_y:.2f}"
        )

    else:
        # 검출 대상 없을 때
        print("No target detected.")
        action_command.append({"turret": " ", "weight": 0.0})

    print("Action Command Queue:", action_command)
    return jsonify(result_json)


@app.route("/info", methods=["POST"])
def info():
    """
    /info 엔드포인트는 JSON 형식의 데이터를 수신하여, 처리 여부를 반환합니다.
    """
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON received"}), 400
    print("📨 /info data received:", data)
    return jsonify({"status": "success", "control": ""})


@app.route("/update_position", methods=["POST"])
def update_position():
    """
    /update_position 엔드포인트는 "position" 키를 포함한 JSON 데이터를 수신하여,
    현재 위치를 업데이트하고 그 결과를 반환합니다.
    """
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
    """
    /get_move 엔드포인트는 미리 정의된 이동 명령(move_command) 중 하나를 반환합니다.
    """
    global move_command
    if move_command:
        command = move_command.pop(0)
        print(f"🚗 Move Command: {command}")
        return jsonify(command)
    else:
        return jsonify({"move": "STOP", "weight": 1.0})


@app.route("/get_action", methods=["GET"])
def get_action():
    """
    /get_action 엔드포인트는 터렛 등 액션 명령(action_command) 중 하나를 반환합니다.
    """
    global action_command
    if action_command:
        command = action_command.pop(0)
        print(f"🔫 Action Command: {command}")
        return jsonify(command)
    else:
        return jsonify({"turret": " ", "weight": 0.0})


@app.route("/update_bullet", methods=["POST"])
def update_bullet():
    """
    /update_bullet 엔드포인트는 총알 충돌 데이터를 수신하여 로그에 출력하고 응답을 반환합니다.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "ERROR", "message": "Invalid request data"}), 400
    print(
        f"💥 Bullet Impact at X={data.get('x')}, Y={data.get('y')}, Z={data.get('z')}, Target={data.get('hit')}"
    )
    return jsonify({"status": "OK", "message": "Bullet impact data received"})


@app.route("/set_destination", methods=["POST"])
def set_destination():
    """
    /set_destination 엔드포인트는 목적지 데이터를 수신하여, 설정된 목적지를 반환합니다.
    """
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
    """
    /update_obstacle 엔드포인트는 장애물 데이터를 수신하여 처리 결과를 반환합니다.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
    print("🪨 Obstacle Data:", data)
    return jsonify({"status": "success", "message": "Obstacle data received"})


@app.route("/init", methods=["GET"])
def init():
    """
    /init 엔드포인트는 시뮬레이션 시작 시 초기 설정 값을 반환합니다.
    """
    config = {
        "startMode": "start",  # "start" 또는 "pause" 중 선택
        "blStartX": 60,  # Blue 팀 시작 X 좌표
        "blStartY": 10,
        "blStartZ": 27.23,
        "rdStartX": 59,  # Red 팀 시작 X 좌표
        "rdStartY": 10,
        "rdStartZ": 280,
    }
    print("🛠️ Initialization config sent via /init:", config)
    return jsonify(config)


@app.route("/start", methods=["GET"])
def start():
    """
    /start 엔드포인트는 시뮬레이션 시작 명령을 수신하면 제어 신호를 반환합니다.
    """
    print("🚀 /start command received")
    return jsonify({"control": ""})


if __name__ == "__main__":
    # Flask 서버를 호스트 0.0.0.0의 포트 5000에서 실행합니다.
    app.run(host="0.0.0.0", port=5000)
