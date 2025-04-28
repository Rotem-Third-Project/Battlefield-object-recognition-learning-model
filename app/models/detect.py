from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
import numpy as np
import cv2
from pathlib import Path

# 모델과 경로는 함수 인자로 받을 거야
async def detect(image: UploadFile = File(...), model=None, crosshair_path=None, tmp_path=None, detected_objects=None):
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

    crosshair = cv2.imread(str(crosshair_path), cv2.IMREAD_UNCHANGED)
    crosshair = cv2.resize(crosshair, (65, 65), interpolation=cv2.INTER_AREA)

    for idx, box in enumerate(detections):
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
                'id': idx,
                'threat': "Normal",
                'bbox': [x1, y1, x2, y2],
                'confidence': confidence
            })

    detected_objects.clear()
    detected_objects.extend(filtered_results)

    cv2.imwrite(str(tmp_path), img_cv)

    return JSONResponse(content=filtered_results)
