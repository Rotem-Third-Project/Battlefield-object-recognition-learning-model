from flask import Flask, request, jsonify, Response
import threading, queue, time
import mss, io
import cv2, numpy as np
from PIL import Image
#----------------------------------------------------------------------
#pip install mss


# 디스플레이 해상도
disp_x, disp_y = 2560, 1440

# 캡처 영역 크기
size_x, size_y = 1900, 1020
DESIRED_SIZE = (size_x, size_y)

# ROI를 화면 정중앙에 두고 싶다면
ROI = {
    'top':    int((disp_y - size_y) // 2),
    'left':   int((disp_x - size_x) // 2),
    'width':  size_x,
    'height': size_y
}

FPS = 120
INTERVAL = 1.0 / FPS

# 버퍼 큐 (최대 2프레임 대기)
capture_q = queue.Queue(maxsize=2)
stream_q  = queue.Queue(maxsize=2)

app = Flask(__name__)
latest_info_data = {}
local = {}
move_command = []
action_command = []

def capture_loop():
    with mss.mss() as sct:
        while True:
            img = sct.grab(ROI)
            if not capture_q.full():
                capture_q.put(img)

def encode_loop():
    while True:
        sct_img = capture_q.get()

        # 1) mss로부터 가져온 RGB byte → numpy 배열
        arr = np.frombuffer(sct_img.rgb, dtype=np.uint8) \
                .reshape(sct_img.height, sct_img.width, 3)

        # 2) RGB → BGR 변환
        # (cv2.cvtColor 혹은 슬라이스 방식 중 하나만 쓰세요)
        # 방법 A: 슬라이스
        #arr = arr[:, :, ::-1]
        # 방법 B: cv2.cvtColor
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        # 3) 리사이즈
        small = cv2.resize(arr, DESIRED_SIZE, interpolation=cv2.INTER_LINEAR)

        # 4) JPEG 인코딩
        _, jpeg = cv2.imencode('.jpg', small,
                               [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        data = jpeg.tobytes()

        # 5) 큐에 넣기
        if not stream_q.full():
            stream_q.put(data)



def generate_mjpeg():
    """stream_q에서 프레임을 꺼내 MJPEG 바운더리와 함께 yield"""
    while True:
        frame = stream_q.get()
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
        )

# 최적화된 video_feed
@app.route('/video_feed', methods=['GET'])
def video_feed():
    return Response(
        generate_mjpeg(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
#----------------------------------------------------------------------------------
# --- 이하 기존 엔드포인트들 그대로 유지 ---
@app.route('/detect', methods=['POST'])
def detect():
    image = request.files.get('image')
    if not image:
        return jsonify({"error": "No image received"}), 400

    image_path = 'temp_image.jpg'
    image.save(image_path)

    results = model(image_path)
    detections = results[0].boxes.data.gpu().numpy()

    target_classes = {0: "person", 2: "car", 7: "truck", 15: "rock"}
    filtered_results = []
    for box in detections:
        class_id = int(box[5])
        if class_id in target_classes:
            filtered_results.append({
                'className': target_classes[class_id],
                'bbox': [float(coord) for coord in box[:4]],
                'confidence': float(box[4])
            })

    return jsonify(filtered_results)

@app.route('/info', methods=['POST'])
def info():
    global latest_info_data
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    latest_info_data = data
    return jsonify({"status": "success", "control": ""})

@app.route('/update_position', methods=['POST'])
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

@app.route('/get_move', methods=['GET'])
def get_move():
    global move_command
    if move_command:
        command = move_command.pop(0)
        print(f"🚗 Move Command: {command}")
        return jsonify(command)
    else:
        return jsonify({"move": "", "weight": 1.0})

@app.route('/init', methods=['GET'])
def init():
    config = {
        "startMode": "start",
        "blStartX": 60, "blStartY": 10, "blStartZ": 27.23,
        "rdStartX": 59, "rdStartY": 10, "rdStartZ": 280
    }
    print("🛠️ /init:", config)
    return jsonify(config)

@app.route('/start', methods=['GET'])
def start():
    print("🚀 /start")
    return jsonify({"control": ""})

@app.route('/get_info', methods=['GET'])
def get_info():
    return jsonify(latest_info_data)

@app.route('/local', methods=['GET'])
def local_api():
    return jsonify(local)

@app.route('/set_command', methods=['POST'])
def set_command():
    global move_command
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()
    steer_deg = data.get("steer_deg")
    key = data.get("key")
    duration = data.get("duration")
    if steer_deg is None or key is None or duration is None:
        return jsonify({"error": "Missing fields"}), 400
    move_command = [{"move": key, "weight": duration}]
    print(f"Received Command: steer_deg={steer_deg}, key={key}, duration={duration}")
    return jsonify({"status": "success"}), 200

@app.route('/get_action', methods=['GET'])
def get_action():
    return jsonify({"status": "OK", "message": "get_action is not implemented yet."})

if __name__ == '__main__':
    # 파이프라인 스레드 시작
    threading.Thread(target=capture_loop, daemon=True).start()
    threading.Thread(target=encode_loop,  daemon=True).start()

    # 가능하면 gunicorn+gevent 로 배포하세요
    app.run(host='0.0.0.0', port=5000, threaded=True)

