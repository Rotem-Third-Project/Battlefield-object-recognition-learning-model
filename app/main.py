from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO
import tensorflow as tf
import shutil
import threading
import webbrowser
import os
import time
from pathlib import Path
import cv2
import numpy as np
from models.detect import detect as detect_func

# 탭 기본 설정
BASE_DIR = Path(__file__).resolve().parent
TMP_PATH = BASE_DIR / "tmp" / "temp_image.jpg"
CROSSHAIR_PATH = BASE_DIR / "static" / "img" / "crosshair.png"
EFFICIENTNET_MODEL_PATH = BASE_DIR / "models" / "real_efficientnetb0_model.h5"  # EfficientNet 모델 경로

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/tmp", StaticFiles(directory=BASE_DIR / "tmp"), name="tmp")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# 모델 로드
yolo_model = YOLO(BASE_DIR / "models" / "best.pt")
efficientnet_model = tf.keras.models.load_model(EFFICIENTNET_MODEL_PATH)

move_command_queue = []
action_command_queue = []
gear_level = 2
gear_weights = {1: 0.3, 2: 0.6, 3: 1.0}
current_position = (60, 27)

detected_objects = []

simulator_status = {
    "player_pos": {"x": 60, "y": 10, "z": 27.23},
    "player_speed": 0,
    "player_health": 100,
    "enemy_health": 100,
    "distance": 0
}

@app.on_event("startup")
async def clear_queues():
    move_command_queue.clear()
    action_command_queue.clear()
    detected_objects.clear()

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

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

@app.post("/send_move")
async def send_move(move: str = Form(...), weight: float = Form(...)):
    move_command_queue.append({"move": move, "weight": weight})
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/send_action")
async def send_action(turret: str = Form(...), weight: float = Form(...)):
    action_command_queue.append({"turret": turret, "weight": weight})
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/get_move")
async def get_move():
    if move_command_queue:
        return move_command_queue.pop(0)
    return {"move": "STOP", "weight": 1.0}

@app.get("/get_action")
async def get_action():
    if action_command_queue:
        return action_command_queue.pop(0)
    return {"turret": " ", "weight": 0.0}

@app.post("/detect")
async def detect_api(image: UploadFile = File(...)):
    return await detect_func(
        image=image,
        yolo_model=yolo_model,
        efficientnet_model=efficientnet_model,  # EfficientNet 모델 전달
        crosshair_path=CROSSHAIR_PATH,
        tmp_path=TMP_PATH,
        detected_objects=detected_objects
    )

@app.get("/get_detected_objects")
async def get_detected_objects():
    return {"objects": detected_objects}

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

@app.get("/init")
async def init():
    config = {
        "startMode": "start",
        "blStartX": 60,
        "blStartY": 10,
        "blStartZ": 27.23,
        "rdStartX": 59,
        "rdStartY": 10,
        "rdStartZ": 280
    }
    return JSONResponse(content=config)

@app.get("/get_status")
async def get_status():
    return simulator_status

@app.post("/info")
async def receive_simulator_info(request: Request):
    global simulator_status
    try:
        data = await request.json()

        simulator_status["player_pos"] = data.get("playerPos", simulator_status["player_pos"])
        simulator_status["player_speed"] = data.get("playerSpeed", simulator_status["player_speed"])
        simulator_status["player_health"] = data.get("playerHealth", simulator_status["player_health"])
        simulator_status["enemy_health"] = data.get("enemyHealth", simulator_status["enemy_health"])
        simulator_status["distance"] = data.get("distance", simulator_status["distance"])

        return {"status": "success", "message": "Simulator info updated"}

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

def open_browser():
    time.sleep(1)
    webbrowser.open("http://localhost:5000/dashboard")

if __name__ == "__main__":
    if os.environ.get("RUN_MAIN") != "true":
        threading.Thread(target=open_browser).start()
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True, access_log=False)