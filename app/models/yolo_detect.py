from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
import numpy as np
import cv2
from pathlib import Path

async def detect(image: UploadFile = File(...), yolo_model=None, crosshair_path=None, tmp_path=None, detected_objects=None):
    try:
        # 이미지 로드
        image_bytes = await image.read()
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # YOLOv8으로 객체 탐지
        results = list(yolo_model.predict(img_cv, verbose=False, stream=True))
        detections = results[0].boxes.data.cpu().numpy()
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "ERROR", "message": str(e)})

    filtered_results = []
    class_names = ["Enemy_Front", "Enemy_Side", "Enemy_Rear"]  # YOLOv8 클래스

    # 위험 등급 매핑
    threat_levels = {
        "Enemy_Front": "LEVEL 3",
        "Enemy_Side": "LEVEL 2",
        "Enemy_Rear": "LEVEL 1"
    }

    # 위험 등급에 따른 바운딩 박스 색상 (BGR 형식)
    threat_colors = {
        "LEVEL 1": (0, 255, 0),    # 초록
        "LEVEL 2": (0, 165, 255),  # 주황
        "LEVEL 3": (0, 0, 255),    # 빨강
        "Normal": (128, 128, 128), # 회색 (기본값)
        "Unknown": (128, 128, 128) # 회색 (알 수 없는 경우)
    }

    # 크로스헤어 로드
    crosshair = cv2.imread(str(crosshair_path), cv2.IMREAD_UNCHANGED)
    crosshair = cv2.resize(crosshair, (65, 65), interpolation=cv2.INTER_AREA)

    for idx, box in enumerate(detections):
        class_id = int(box[5])
        if class_id in range(len(class_names)):  # 클래스 ID가 유효한 경우
            x1, y1, x2, y2 = map(int, box[:4])
            confidence = float(box[4])
            class_label = class_names[class_id]
            threat_level = threat_levels.get(class_label, "Unknown")

            # 크로스헤어 오버레이
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

            # 바운딩 박스 및 레이블 그리기
            box_color = threat_colors.get(threat_level, (128, 128, 128))
            cv2.rectangle(img_cv, (x1, y1), (x2, y2), box_color, 2)
            label = f"{class_label}: {confidence:.2f} ({threat_level})"
            cv2.putText(img_cv, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

            filtered_results.append({
                'className': class_label,
                'id': idx,
                'threat': threat_level,
                'bbox': [x1, y1, x2, y2],
                'confidence': confidence
            })

    detected_objects.clear()
    detected_objects.extend(filtered_results)

    cv2.imwrite(str(tmp_path), img_cv)

    return JSONResponse(content=filtered_results)