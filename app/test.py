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
BARREL_X = 960  # 기준 좌표 (예: 화면 중앙 x좌표)
TOLERANCE = 15  # 터렛 이동 허용 오차 (픽셀 단위)
action_command = []  # 터렛 등 액션 명령 저장 (예: {'turret': 'E', 'weight': 1.0})
SPEED = 0.5
move_command = [{"move": "W", "weight": SPEED}] * 60

# (이전 코드에 칼만 필터가 있었으나, 현재는 사용하지 않으므로 제거)

# 전역 변수: 마지막 검출된 바운딩 박스 저장 (없으면 None)
last_candidate_box = None


def compute_turret_weight(dx, tolerance):
    """
    터렛 이동 거리를 결정하기 위해, 기준 좌표(BARREL_X)와의 수평 차이(dx)에 따라
    가중치(이동량)를 비선형 방식으로 계산합니다.

    - abs(dx) <= tolerance 인 경우, 이동할 필요가 없으므로 0.0을 반환합니다.
    - abs(dx) > tolerance 인 경우, 초과한 거리(extra)를 (abs(dx) - tolerance)로 계산합니다.
      이 값을 100픽셀 단위로 정규화한 후, 3.5 제곱(power 3.5)을 취하고 0.1을 곱하여 weight를 산출합니다.
      예를 들어, extra가 100픽셀이면 weight = 0.1 * (1)**3.5 = 0.1,
             extra가 200픽셀이면 weight = 0.1 * (2)**3.5 (즉, 비선형적으로 증가함).
    - 최종 weight가 10.0을 초과할 경우, 최대값 10.0으로 제한하여 반환합니다.
    """
    abs_dx = abs(dx)
    if abs_dx <= tolerance:
        return 0.0
    extra = abs_dx - tolerance
    extra_weight = 0.1 * (extra / 100) ** 3.5
    return min(extra_weight, 100.0)


@app.route("/detect", methods=["POST"])
def detect():
    global action_command, last_candidate_box
    action_command.clear()

    # 이미지를 수신하여 임시 파일로 저장 (YOLO 추론용)
    image = request.files["image"]
    image_path = "temp_image.jpg"
    image.save(image_path)

    # YOLO 모델로 객체 검출 (deep_sort 추적도 포함)
    results = model.track(image_path, persist=True, show=False, conf = 0.5)
    boxes = results[0].boxes
    detections = boxes.data.cpu().numpy()

    target_classes = {0: "Enemy", 1: "car", 7: "truck", 15: "rock"}
    result_json = []
    target_candidates = []

    def sigmoid(x):
        return 1 / (1 + np.exp(-x))

    # 검출된 객체들 중 'Enemy' 클래스만 후보로 선정
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
            if class_id == 0:
                print(
                    "Enemy confidence:",
                    detection_result["confidence"],
                    target_classes[class_id],
                )
        if class_id == 0:  # 'Enemy' 클래스만 터렛 이동 기준으로 사용
            x1, y1, x2, y2 = box[:4]
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            dist = abs(cx - BARREL_X)
            target_candidates.append((dist, cx, cy, box))

    # 이미지 로드
    img = cv2.imread(image_path)

    if target_candidates:
        # 후보들 중 기준(중앙)과의 거리가 가장 가까운 객체를 선택
        target_candidates.sort(key=lambda x: x[0])
        _, cx, cy, candidate_box = target_candidates[0]

        # 원본 검출된 중심 좌표를 기준으로 터렛 이동 계산
        dx = cx - BARREL_X
        weight = compute_turret_weight(dx, TOLERANCE)
        if dx > TOLERANCE:
            action_command.append({"turret": "E", "weight": weight})
        elif dx < -TOLERANCE:
            action_command.append({"turret": "Q", "weight": weight})
        else:
            action_command.append({"turret": " ", "weight": 0.0})
        print(f"[Detection] cx: {cx:.2f}, dx: {dx:.2f}, weight: {weight:.2f}")

        # 원본 바운딩 박스 (초록색) 표시
        x1, y1, x2, y2 = candidate_box[:4]

    else:
        # 후보 객체가 없으면 터렛 명령 없이 "No Detection" 텍스트를 이미지에 표시
        print("No target detected.")
        action_command.append({"turret": " ", "weight": 0.0})

    print("Action Command Queue:", action_command)

    # 반환 시 JSON 형식으로 검출 결과를 전달합니다.
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
