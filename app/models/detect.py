# detect.py
import cv2
import numpy as np
from fastapi.responses import JSONResponse
from fastapi import UploadFile, File

async def detect_target(
    image: UploadFile,
    model,
    action_command_queue,
    BARREL_X,
    BARREL_Y,
    TOLERANCE,
    CROSSHAIR_PATH,
    latest_frame,
    frame_lock
):
    try:
        print("📥 이미지 수신 시작")
        image_bytes = await image.read()
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        print("🧠 YOLO 추적 시작")

<<<<<<< HEAD
        results = model.track(img_cv, persist=True, show=False)
        print("✅ YOLO 추적 완료")
=======
            results = model.track(img_cv, persist=True, show=False)
            result = results[0]
            boxes = result.boxes
            track_ids = result.boxes.id
            detections = boxes.data.cpu().numpy()
            track_ids = track_ids.cpu().numpy() if track_ids is not None else [-1] * len(detections)
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "ERROR", "message": str(e)})
>>>>>>> bf2edecbafc73bc89011de04c909978d8a46400f

        result = results[0]
        boxes = result.boxes
        track_ids = result.boxes.id
        detections = boxes.data.cpu().numpy()
        track_ids = track_ids.cpu().numpy() if track_ids is not None else [-1] * len(detections)

    except Exception as e:
        print("🔥 detect() 에러:", str(e))
        return JSONResponse(status_code=500, content={"status": "ERROR", "message": str(e)})

    target_classes = {0: "Enemy", 1: "car", 7: "truck", 15: "rock"}
    result_json = []
    action_command_queue.clear()
    target_candidates = []

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
        dx, dy = cx - BARREL_X, cy - BARREL_Y

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
    with frame_lock:
        latest_frame = resized_img.copy()

    return JSONResponse(content=result_json)
