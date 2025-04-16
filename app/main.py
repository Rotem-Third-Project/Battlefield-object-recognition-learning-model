from fastapi import FastAPI, File, UploadFile, Request, WebSocket, WebSocketDisconnect, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import torch
from ultralytics import YOLO
import shutil
import json
import threading
import webbrowser
import requests

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

model = YOLO('yolov8n.pt')
connected_clients = []

move_command_queue = []
action_command_queue = []
gear_level = 2
gear_weights = {1: 0.3, 2: 0.6, 3: 1.0}

# ✅ MJPEG 프록시: Unity에서 MJPEG로 내보낸 영상 중계
@app.get("/proxy_stream")
def proxy_stream():
    def stream():
        r = requests.get("http://localhost:8080/video.mjpg", stream=True)  # Unity에서 내보낸 MJPEG 주소
        for chunk in r.iter_content(chunk_size=1024):
            yield chunk
    return StreamingResponse(stream(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.post("/input_key")
async def input_key(key: str = Form(...)):
    global gear_level
    if key in ["W", "A", "S", "D"]:
        move_command_queue.append({
            "move": key,
            "weight": gear_weights[gear_level]
        })
        print(f"🕹️ 입력: {key}, 기어 {gear_level}, 가중치 {gear_weights[gear_level]}")
    elif key == "P" and gear_level < 3:
        gear_level += 1
        print(f"🔺 기어 업: {gear_level}")
    elif key == "L" and gear_level > 1:
        gear_level -= 1
        print(f"🔻 기어 다운: {gear_level}")
    return {"gear": gear_level}

@app.post("/send_move")
async def send_move(move: str = Form(...), weight: float = Form(...)):
    move_command_queue.append({"move": move, "weight": weight})
    print(f"✅ 수신된 이동 명령: {move_command_queue[-1]}")
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/send_action")
async def send_action(turret: str = Form(...), weight: float = Form(...)):
    action_command_queue.append({"turret": turret, "weight": weight})
    print(f"✅ 수신된 포탑 명령: {action_command_queue[-1]}")
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/detect")
async def detect(image: UploadFile = File(...)):
    image_path = "temp_image.jpg"
    with open(image_path, "wb") as f:
        shutil.copyfileobj(image.file, f)

    results = model(image_path)
    detections = results[0].boxes.data.cpu().numpy()

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
    return filtered_results

@app.post("/info")
async def info(request: Request):
    data = await request.json()
    print("📨 /info data received:", data)
    for client in connected_clients:
        await client.send_text(json.dumps(data))
    return {"status": "success", "control": ""}

@app.post("/update_position")
async def update_position(request: Request):
    data = await request.json()
    if "position" not in data:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": "Missing position data"})
    try:
        x, y, z = map(float, data["position"].split(","))
        current_position = f"{int(x)}, {int(z)}"

        user_agent = request.headers.get("user-agent", "").lower()
        if "unity" not in user_agent:
            print(f"📍 Position updated: {current_position}")

        for client in connected_clients:
            await client.send_text(json.dumps({"position": current_position}))
        return {"status": "OK", "current_position": current_position}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": str(e)})

@app.get("/get_move")
async def get_move():
    if move_command_queue:
        command = move_command_queue.pop(0)
        print(f"🚗 이동 명령 송신: {command}")
        return command
    return {"move": "STOP", "weight": 1.0}

@app.get("/get_action")
async def get_action():
    if action_command_queue:
        command = action_command_queue.pop(0)
        print(f"🔫 포탑 명령 송신: {command}")
        return command
    return {"turret": "", "weight": 0.0}

@app.post("/update_bullet")
async def update_bullet(request: Request):
    data = await request.json()
    print(f"💥 Bullet Impact at X={data.get('x')}, Y={data.get('y')}, Z={data.get('z')}, Target={data.get('hit')}")
    return {"status": "OK", "message": "Bullet impact data received"}

@app.post("/set_destination")
async def set_destination(request: Request):
    data = await request.json()
    if "destination" not in data:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": "Missing destination data"})
    try:
        x, y, z = map(float, data["destination"].split(","))
        print(f"🎯 Destination set to: x={x}, y={y}, z={z}")
        return {"status": "OK", "destination": {"x": x, "y": y, "z": z}}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": f"Invalid format: {str(e)}"})

@app.post("/update_obstacle")
async def update_obstacle(request: Request):
    data = await request.json()
    print("🪨 Obstacle Data:", data)
    return {"status": "success", "message": "Obstacle data received"}

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
    print("🛠️ Initialization config sent via /init:", config)
    return config

@app.get("/start")
async def start():
    print("🚀 /start command received")
    return {"control": ""}

def open_browser():
    import time
    time.sleep(1)
    webbrowser.open("http://localhost:5000/dashboard")

if __name__ == "__main__":
    threading.Thread(target=open_browser).start()
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
