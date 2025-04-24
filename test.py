# 🚀 FastAPI + YOLO + BoT-SORT 통합 서버

from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO
import shutil
import threading
import webbrowser
import os
import time
import cv2
import numpy as np
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware




# 기본 설정
BASE_DIR = Path(__file__).resolve().parent
TMP_PATH = BASE_DIR / "tmp" / "temp_image.jpg"
TMP_WORK_PATH = BASE_DIR / "tmp" / "temp_image_working.jpg"
CROSSHAIR_PATH = BASE_DIR / "static" / "img" / "crosshair.png"

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/tmp", StaticFiles(directory=BASE_DIR / "tmp"), name="tmp")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모델 로드
model = YOLO(BASE_DIR / "models" / "best.pt")

# 전역 변수
BARREL_X = 960
BARREL_Y = 883
TOLERANCE = 15
move_command_queue = []
action_command_queue = []
gear_level = 2
gear_weights = {1: 0.3, 2: 0.6, 3: 1.0}
current_position = (0, 0)

@app.on_event("startup")
async def startup_event():
    move_command_queue.clear()
    action_command_queue.clear()

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

@app.post("/send_move")
async def send_move(move: str = Form(...), weight: float = Form(...)):
    move_command_queue.append({"move": move, "weight": weight})
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/send_action")
async def send_action(turret: str = Form(...), weight: float = Form(...)):
    action_command_queue.append({"turret": turret, "weight": weight})
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/detect")
async def detect(image: UploadFile = File(...)):
    with open(TMP_WORK_PATH, "wb") as f:
        shutil.copyfileobj(image.file, f)

    try:
        results = model.track(str(TMP_WORK_PATH), persist=True, show=False, tracker='custom_botsort.yaml')
        result = results[0]
        boxes = result.boxes
        track_ids = result.boxes.id
        detections = boxes.data.cpu().numpy()
        track_ids = track_ids.cpu().numpy() if track_ids is not None else [-1] * len(detections)
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "ERROR", "message": str(e)})

    target_classes = {0: "Enemy", 1: "car", 7: "truck", 15: "rock"}
    result_json = []
    action_command_queue.clear()
    target_candidates = []
    
    img_cv = cv2.imread(str(TMP_WORK_PATH))
    crosshair = cv2.imread(str(CROSSHAIR_PATH), cv2.IMREAD_UNCHANGED)
    crosshair = cv2.resize(crosshair, (60, 60), interpolation=cv2.INTER_AREA)
    

    for i, box in enumerate(detections):
        class_id = int(box[5])
        if class_id in target_classes:
            x1, y1, x2, y2 = box[:4]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            conf = float(box[4])
            track_id = int(track_ids[i])
            label = f"{target_classes[class_id]}_{track_id if track_id != -1 else 'unknown'}"
            result_json.append({"className": label, "bbox": [x1, y1, x2, y2], "confidence": conf})
            if class_id == 0:
                dist = abs(cx - BARREL_X)
                target_candidates.append((dist, cx, cy, box))

    if target_candidates:
        target_candidates.sort(key=lambda x: x[0])
        _, cx, cy, _ = target_candidates[0]
        dx = cx - BARREL_X
        dy = cy - BARREL_Y

        def turret_weight(delta, axis):
            abs_d = abs(delta)
            if abs_d <= TOLERANCE: return 0.0
            extra = abs_d - TOLERANCE
            if extra <= 200: return 0.1
            if extra <= 300: return 0.2 if axis == 'y' else 0.4
            if extra <= 500: return 0.5
            return 1.0

        weight_x = turret_weight(dx, 'x')
        weight_y = turret_weight(dy, 'y')
        if dx > TOLERANCE:
            action_command_queue.append({"turret": "E", "weight": weight_x})
        elif dx < -TOLERANCE:
            action_command_queue.append({"turret": "Q", "weight": weight_x})
        if dy > TOLERANCE:
            action_command_queue.append({"turret": "F", "weight": weight_y})
        elif dy < -TOLERANCE:
            action_command_queue.append({"turret": "R", "weight": weight_y})
        if abs(dx) <= TOLERANCE and abs(dy) <= TOLERANCE:
            action_command_queue.append({"turret": " ", "weight": 0.0})
        
    resized_img = cv2.resize(img_cv, (0, 0), fx=0.6, fy=0.6)
    cv2.imwrite(str(TMP_WORK_PATH), resized_img)
    TMP_WORK_PATH.replace(TMP_PATH)  # ✨ 완성된 프레임만 교체

    return JSONResponse(content=result_json)

@app.get("/video_feed")
def video_feed():
    def generate():
        while True:
            if TMP_WORK_PATH.exists():
                frame = cv2.imread(str(TMP_WORK_PATH))
                if frame is None:
                    time.sleep(0.005)
                    continue
                _, buffer = cv2.imencode(".jpg", frame)
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            time.sleep(0.016)
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

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

@app.post("/update_bullet")
async def update_bullet(request: Request):
    data = await request.json()
    print(f"\U0001F4A5 Bullet Impact at X={data.get('x')}, Y={data.get('y')}, Z={data.get('z')}, Target={data.get('hit')}")
    return {"status": "OK", "message": "Bullet impact data received"}

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

@app.post("/update_obstacle")
async def update_obstacle(request: Request):
    data = await request.json()
    print("\U0001FAA8 Obstacle Data:", data)
    return {"status": "success", "message": "Obstacle data received"}

@app.get("/init")
async def init():
    return {
        "startMode": "start",
        "blStartX": 60, "blStartY": 10, "blStartZ": 27.23,
        "rdStartX": 59, "rdStartY": 10, "rdStartZ": 280
    }

@app.get("/start")
async def start():
    return {"control": ""}

# 브라우저 자동 실행
if __name__ == "__main__":
    if os.environ.get("RUN_MAIN") != "true":
        threading.Thread(target=lambda: webbrowser.open("http://localhost:5000/dashboard")).start()
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True, access_log=False)
