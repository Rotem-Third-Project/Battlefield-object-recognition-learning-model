<<<<<<< HEAD
print("remote success")
#fsdfsdsdfasdf

=======
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import torch
from ultralytics import YOLO

app = FastAPI()

model = YOLO('yolov8n.pt')

move_command = ["W", "W", "W", "D", "D", "D", "A", "A", "S", "S", "STOP"]
action_command = ["Q", "Q", "Q", "Q", "E", "E", "E", "E", "F", "F", "R", "R", "R", "R", "FIRE"]


@app.post('/detect')
async def detect(image: UploadFile = File(...)):
    image_path = 'temp_image.jpg'
    with open(image_path, "wb") as buffer:
        buffer.write(await image.read())

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

    return JSONResponse(filtered_results)


class InfoData(BaseModel):
    data: dict


@app.post('/info')
async def info(info_data: InfoData):
    print("Received /info data:", info_data.data)
    return {"status": "success", "message": "Data received"}


class PositionData(BaseModel):
    position: str


@app.post('/update_position')
async def update_position(position_data: PositionData):
    try:
        x, y, z = map(float, position_data.position.split(","))
        current_position = (int(x), int(z))
        print(f"Updated Position: {current_position}")
        return {"status": "OK", "current_position": current_position}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get('/get_move')
async def get_move():
    global move_command

    if move_command:
        command = move_command.pop(0)
        print(f"Sent Move Command: {command}")
        return {"move": command}
    else:
        return {"move": "STOP"}


@app.get('/get_action')
async def get_action():
    global action_command

    if action_command:
        command = action_command.pop(0)
        print(f"Sent Action Command: {command}")
        return {"turret": command}
    else:
        return {"turret": " "}


class BulletData(BaseModel):
    x: float
    y: float
    z: float
    hit: str


@app.post('/update_bullet')
async def update_bullet(bullet: BulletData):
    print(f"Bullet Impact at X={bullet.x}, Y={bullet.y}, Z={bullet.z}, Target={bullet.hit}")
    return {"status": "OK", "message": "Bullet impact data received"}


class DestinationData(BaseModel):
    destination: str


@app.post('/set_destination')
async def set_destination(dest_data: DestinationData):
    try:
        x_dest, y_dest, z_dest = map(float, dest_data.destination.split(","))
        print(f"Received destination: x={x_dest}, y={y_dest}, z={z_dest}")

        return {"status": "OK", "destination": {"x": x_dest, "y": y_dest, "z": z_dest}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid format: {str(e)}")


class ObstacleData(BaseModel):
    obstacle: dict


@app.post('/update_obstacle')
async def update_obstacle(obstacle_data: ObstacleData):
    print("Received obstacle data:", obstacle_data.obstacle)
    return {"status": "success", "message": "Obstacle data received"}
>>>>>>> bafcb3b73761b907bd2dea13760740b16d9219c7
