from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import numpy as np
import torch
from ultralytics import YOLO
import shutil

app = FastAPI()

# Load YOLO model
model = YOLO('yolov8n.pt')

# Global command lists
move_command = ["W", "W", "W", "D", "D", "D", "A", "A", "S", "S", "STOP"]
action_command = ["Q", "Q", "Q", "Q", "E", "E", "E", "E", "F", "F", "R", "R", "R", "R", "FIRE"]

# Pydantic models
class PositionData(BaseModel):
    position: str

class DestinationData(BaseModel):
    destination: str

class BulletData(BaseModel):
    x: float
    y: float
    z: float
    hit: str

@app.post("/detect")
async def detect(image: UploadFile = File(...)):
    """Object detection from uploaded image"""
    temp_path = "temp_image.jpg"
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(image.file, f)

    results = model(temp_path)
    detections = results[0].boxes.data.cpu().numpy()

    target_classes = {0: "person", 2: "car", 7: "truck", 15: "rock"}
    filtered = []
    for box in detections:
        class_id = int(box[5])
        if class_id in target_classes:
            filtered.append({
                "className": target_classes[class_id],
                "bbox": [float(coord) for coord in box[:4]],
                "confidence": float(box[4])
            })
    return filtered


@app.post("/info")
async def info(request: Request):
    """Receive general data from simulator"""
    try:
        data = await request.json()
        print("Received /info data:", data)
        return {"status": "success", "message": "Data received"}
    except Exception:
        return JSONResponse(status_code=400, content={"error": "No JSON received"})


@app.post("/update_position")
async def update_position(data: PositionData):
    try:
        x, y, z = map(float, data.position.split(","))
        current_position = (int(x), int(z))  # Ignore height
        print(f"Updated Position: {current_position}")
        return {"status": "OK", "current_position": current_position}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": str(e)})


@app.get("/get_move")
async def get_move():
    global move_command
    if move_command:
        command = move_command.pop(0)
        print(f"Sent Move Command: {command}")
        return {"move": command}
    return {"move": "STOP"}


@app.get("/get_action")
async def get_action():
    global action_command
    if action_command:
        command = action_command.pop(0)
        print(f"Sent Action Command: {command}")
        return {"turret": command}
    return {"turret": " "}


@app.post("/update_bullet")
async def update_bullet(data: BulletData):
    print(f"Bullet Impact at X={data.x}, Y={data.y}, Z={data.z}, Target={data.hit}")
    return {"status": "OK", "message": "Bullet impact data received"}


@app.post("/set_destination")
async def set_destination(data: DestinationData):
    try:
        x_dest, y_dest, z_dest = map(float, data.destination.split(","))
        print(f"Received destination: x={x_dest}, y={y_dest}, z={z_dest}")
        return {
            "status": "OK",
            "destination": {
                "x": x_dest,
                "y": y_dest,
                "z": z_dest
            }
        }
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": f"Invalid format: {str(e)}"})


@app.post("/update_obstacle")
async def update_obstacle(request: Request):
    try:
        data = await request.json()
        print("Received obstacle data:", data)
        return {"status": "success", "message": "Obstacle data received"}
    except Exception:
        return JSONResponse(status_code=400, content={'status': 'error', 'message': 'No data received'})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000)
