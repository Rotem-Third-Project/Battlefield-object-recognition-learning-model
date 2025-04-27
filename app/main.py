from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO
import shutil
import threading
import webbrowser
import os
import time
import asyncio
from pathlib import Path
import cv2
import numpy as np

# 📌 경로 설정
BASE_DIR = Path(__file__).resolve().parent
TMP_PATH = BASE_DIR / "tmp" / "temp_image.jpg"
CROSSHAIR_PATH = BASE_DIR / "static" / "img" / "crosshair.png"

# 📌 서버 초기화
app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/tmp", StaticFiles(directory=BASE_DIR / "tmp"), name="tmp")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# 📌 YOLO 모델 로드
model = YOLO(BASE_DIR / "models" / "best.pt")

# 📌 글로벌 상태
move_command_queue = []
action_command_queue = []
gear_level = 2
gear_weights = {1: 0.3, 2: 0.6, 3: 1.0}
current_position = (0, 0)

# 📌 시뮬레이터 HUD 상태
simulator_status = {
    "player_pos": {"x": 0, "y": 0, "z": 0},
    "player_speed": 0,
    "player_health": 100,
    "enemy_health": 100,
    "distance": 0,
}

# 📌 서버 시작 시 큐 비우기
@app.on_event("startup")
async def clear_command_queues():
    move_command_queue.clear()
    action_command_queue.clear()

# 📌 대시보드 페이지
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# 📌 키 입력 처리
@app.post("/input_key")
async def input_key(key: str = Form(...)):
    global gear_level
    if key in ["W", "A", "S", "D"]:
        move_command_queue.append({"move": key, "weight": gear_weights[gear_level]})
    elif key == "P" and gear_level < 3:
        gear_level += 1
    elif key == "L" and gear_level > 1:
        gear_level -= 1
    return {"gear": gear_level}

# 📌 이동 명령 전송
@app.post("/send_move")
async def send_move(move: str = Form(...), weight: float = Form(...)):
    move_command_queue.append({"move": move, "weight": weight})
    return RedirectResponse(url="/dashboard", status_code=303)

# 📌 포탑 명령 전송
@app.post("/send_action")
async def send_action(turret: str = Form(...), weight: float = Form(...)):
    action_command_queue.append({"turret": turret, "weight": weight})
    return RedirectResponse(url="/dashboard", status_code=303)

# 📌 이동 명령 가져오기
@app.get("/get_move")
async def get_move():
    if move_command_queue:
        return move_command_queue.pop(0)
    return {"move": "STOP", "weight": 1.0}

# 📌 액션 명령 가져오기
@app.get("/get_action")
async def get_action():
    if action_command_queue:
        return action_command_queue.pop(0)
    return {"turret": " ", "weight": 0.0}

# 📌 YOLO 탐지 (메모리 직접 처리)
@app.post("/detect")
async def detect(image: UploadFile = File(...)):
    try:
        image_bytes = await image.read()
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        results = list(model.predict(img_cv, verbose=False, stream=True))
        detections = results[0].boxes.data.cpu().numpy()
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "ERROR", "message": str(e)})

    target_classes = {0: "enemy", 2: "car", 7: "truck", 15: "rock"}
    filtered_results = []

    crosshair = cv2.imread(str(CROSSHAIR_PATH), cv2.IMREAD_UNCHANGED)
    crosshair = cv2.resize(crosshair, (65, 65), interpolation=cv2.INTER_AREA)

    for box in detections:
        class_id = int(box[5])
        if class_id in target_classes:
            x1, y1, x2, y2 = map(int, box[:4])
            confidence = float(box[4])
            class_name = target_classes[class_id]

            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            h, w = crosshair.shape[:2]
            x_offset = max(cx - w // 2, 0)
            y_offset = max(cy - h // 2, 0)

            for c in range(3):
                alpha_s = crosshair[:, :, 3] / 255.0
                alpha_l = 1.0 - alpha_s
                for i in range(h):
                    for j in range(w):
                        if y_offset + i < img_cv.shape[0] and x_offset + j < img_cv.shape[1]:
                            img_cv[y_offset + i, x_offset + j, c] = (
                                alpha_s[i, j] * crosshair[i, j, c] +
                                alpha_l[i, j] * img_cv[y_offset + i, x_offset + j, c]
                            )

            filtered_results.append({
                'className': class_name,
                'bbox': [x1, y1, x2, y2],
                'confidence': confidence
            })

    cv2.imwrite(str(TMP_PATH), img_cv)

    return JSONResponse(content=filtered_results)

# 📌 MJPEG 스트리밍 (JPEG 퀄리티 최적화)
@app.get("/video_feed")
def video_feed():
    def generate():
        while True:
            if TMP_PATH.exists():
                frame = cv2.imread(str(TMP_PATH))
                if frame is None:
                    time.sleep(0.005)
                    continue
                _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                )
            time.sleep(0.016)
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

# 📌 위치 업데이트
@app.post("/update_position")
async def update_position(request: Request):
    global current_position
    data = await request.json()
    if "position" not in data:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": "Missing position data"})
    try:
        x, y, z = map(float, data["position"].split(","))
        current_position = (int(x), int(z))
        return {"status": "OK", "current_position": current_position}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": str(e)})

# 📌 탄환 충돌 업데이트
@app.post("/update_bullet")
async def update_bullet(request: Request):
    data = await request.json()
    return {"status": "OK", "message": "Bullet impact data received"}

# 📌 목적지 설정
@app.post("/set_destination")
async def set_destination(request: Request):
    data = await request.json()
    if "destination" not in data:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": "Missing destination data"})
    try:
        x, y, z = map(float, data["destination"].split(","))
        return {"status": "OK", "destination": {"x": x, "y": y, "z": z}}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": f"Invalid format: {str(e)}"})

# 📌 장애물 업데이트
@app.post("/update_obstacle")
async def update_obstacle(request: Request):
    data = await request.json()
    return {"status": "success", "message": "Obstacle data received"}

# 📌 초기화 정보
@app.get("/init")
async def init():
    return {
        "startMode": "start",
        "blStartX": 60,
        "blStartY": 10,
        "blStartZ": 27.23,
        "rdStartX": 59,
        "rdStartY": 10,
        "rdStartZ": 280
    }

# 📌 게임 시작
@app.get("/start")
async def start():
    return {"control": ""}

# 📌 시뮬레이터 정보 수신
@app.post("/info")
async def receive_simulator_info(request: Request):
    try:
        data = await request.json()

        simulator_status["player_pos"] = data.get("playerPos", {})
        simulator_status["player_speed"] = data.get("playerSpeed", 0)
        simulator_status["player_health"] = data.get("playerHealth", 100)
        simulator_status["enemy_health"] = data.get("enemyHealth", 100)
        simulator_status["distance"] = data.get("distance", 0)

        return JSONResponse(content={"status": "success", "message": "Data received"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

# 📌 HUD 실시간 상태 요청
@app.get("/get_status")
async def get_status():
    return {
        "player_pos": simulator_status.get("player_pos", {}),
        "player_speed": simulator_status.get("player_speed", 0),
        "player_health": simulator_status.get("player_health", 100),
        "enemy_health": simulator_status.get("enemy_health", 100),
        "distance": simulator_status.get("distance", 0)
    }

# 📌 서버 실행 시 브라우저 자동 열기
def open_browser():
    time.sleep(1)
    webbrowser.open("http://localhost:5000/dashboard")

# 📌 서버 실행
if __name__ == "__main__":
    if os.environ.get("RUN_MAIN") != "true":
        threading.Thread(target=open_browser).start()
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True, access_log=False)
