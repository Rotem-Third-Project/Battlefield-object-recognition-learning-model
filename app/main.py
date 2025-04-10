from flask import Flask, request, jsonify
from ultralytics import YOLO
import numpy as np
import cv2

app = Flask(__name__)  # 플라스크 객체 선언
current_position = None


@app.route("/", methods=["GET"])
# 라우트 멍령어: 함수 실행하기 위해 어떤 URL 사용할 것인가 지정, '/' -> 루트이다
# 헬로월드 켓 매소드로 받아보기
def home():
    return "hello world"


model = YOLO("yolov8n.pt")  # 미리 모델을 로드해두는 게 성능면에서 좋음

BARREL_X = 960
TOLERANCE = 200
action_command = []
move_command = []

kalman = cv2.KalmanFilter(4, 2)
kalman.transitionMatrix = np.array(
    [[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32
)
kalman.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
kalman.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
kalman.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1
kalman.statePre = np.array([[960], [883], [0], [0]], dtype=np.float32)


@app.route("/detect", methods=["POST"])
def detect():
    global action_command
    action_command.clear()

    image = request.files["image"]
    image_path = "temp_image.jpg"
    image.save(image_path)

    results = model.track(image_path, persist=True)
    boxes = results[0].boxes
    detections = boxes.data.cpu().numpy()

    target_classes = {0: "person", 2: "car", 7: "truck", 15: "rock"}
    result_json = []
    target_candidates = []

    # 후보 수집
    for box in detections:
        class_id = int(box[5])
        if class_id in target_classes:
            result_json.append(
                {
                    "className": target_classes[class_id],
                    "bbox": [float(coord) for coord in box[:4]],
                    "confidence": float(box[4]),
                }
            )

        if class_id == 0:  # person만 추적 대상으로
            x1, y1, x2, y2 = box[:4]
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            dist = abs(cx - BARREL_X)
            target_candidates.append((dist, cx, cy, box))

    # 타겟 선택 및 조준 판단
    if target_candidates:
        # 중앙과 가까운 순으로 정렬
        target_candidates.sort(key=lambda x: x[0])
        _, cx, cy, _ = target_candidates[0]

        # Kalman 필터 예측 + 보정
        kalman.predict()
        measurement = np.array([[np.float32(cx)], [np.float32(cy)]])
        corrected = kalman.correct(measurement)
        kx, ky = corrected[:2].flatten()

        dx = kx - BARREL_X

        if dx > TOLERANCE:
            action_command.append("E")
        elif dx < -TOLERANCE:
            action_command.append("Q")
        else:
            action_command.append(" ")

        print(f"[Kalman] cx: {cx:.2f}, kx: {kx:.2f}, dx: {dx:.2f}")
    else:
        action_command.append(" ")
        print("[Kalman] 타겟 없음 - 정지")

    print("Action Command Queue:", action_command)
    return jsonify(result_json)


@app.route(
    "/set_destination", methods=["POST"]
)  # 이미지 수신을 위한 약속된 도메인, post 방식
def set_destination():
    """
    유니티에서 목표 지점을 설정하면 현재 위치를 기반으로 최단 경로를 계산하여 이동 명령을 생성하는 API
    """
    global move_command, current_position, target_path
    data = request.json
    destination = data.get("destination")
    # obstacles = data.get("obstacles", [])
    print(destination)
    try:
        return jsonify({"status": "OK", "message": "success"})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 400


@app.route("/get_action", methods=["GET"])
def get_action():
    """Provides the next turret action command to the simulator."""
    global action_command

    if action_command:
        command = action_command.pop(0)
        print(f"Sent Action Command: {command}")
        return jsonify({"turret": command})
    else:
        return jsonify({"turret": " "})


@app.route("/get_move", methods=["GET"])
def get_move():
    """Provides the next movement command to the simulator."""
    global move_command

    if move_command:
        command = move_command.pop(0)
        print(f"Sent Move Command: {command}")
        return jsonify({"move": command})
    else:
        return jsonify({"move": "STOP"})


@app.route(
    "/update_position", methods=["POST"]
)  # 이미지 수신을 위한 약속된 도메인, post 방식
def update_position():
    """
    유니티에서 현재 위치를 주기적으로 전송하면 이를 저장하는 API
    """
    global current_position
    data = request.json
    position = data.get("position")

    try:
        x, y, z = map(float, position.split(","))
        current_position = (int(x), int(z))  # y는 높이값이므로 무시
        print(position)
        return jsonify({"status": "OK", "current+position": current_position})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 400


# 서버 구동을 위한 메인 함수 필요
if __name__ == "__main__":
    app.run(
        host="0.0.0.0", port=5000
    )  # app을 실행해라, 호스트는 0.0.0.0 -> 외부에서도 접근 가능?, 포트는 5000번으로
