from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
import numpy as np
import cv2
from pathlib import Path

async def detect(image: UploadFile = File(...), yolo_model=None, efficientnet_model=None, crosshair_path=None, tmp_path=None, detected_objects=None):
    try:
        # 이미지 로드
        image_bytes = await image.read()
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)

        # YOLOv8으로 객체 탐지
        results = list(yolo_model.predict(img_cv, verbose=False, stream=True))
        detections = results[0].boxes.data.cpu().numpy()
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "ERROR", "message": str(e)})

    target_classes = {0: "enemy", 2: "car", 7: "truck", 15: "rock"}
    filtered_results = []
    class_names = ["Enemy_Front", "Enemy_Rear", "Enemy_Side"]  # EfficientNet 클래스

    # 위험 등급 매핑
    threat_levels = {
        "Enemy_Front": "LEVEL 3",
        "Enemy_Rear": "LEVEL 1",
        "Enemy_Side": "LEVEL 2"
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
        if class_id in target_classes:
            x1, y1, x2, y2 = map(int, box[:4])
            confidence = float(box[4])
            class_name = target_classes[class_id]

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

            # EfficientNet으로 분류 (enemy 클래스일 경우만)
            if class_name == "enemy":
                # 이미지 크롭
                cropped_image = img_rgb[y1:y2, x1:x2]
                if cropped_image.shape[0] == 0 or cropped_image.shape[1] == 0:
                    class_label = "Unknown"
                    prob = 0.0
                    threat_level = "Unknown"
                else:
                    # EfficientNet 입력 전처리
                    cropped_image = cv2.resize(cropped_image, (224, 224))
                    cropped_image = cropped_image / 255.0  # 정규화
                    cropped_image = np.expand_dims(cropped_image, axis=0)  # 배치 차원 추가

                    # EfficientNet으로 분류
                    predictions = efficientnet_model.predict(cropped_image, verbose=0)
                    predicted_class = np.argmax(predictions[0])
                    class_label = class_names[predicted_class]
                    prob = float(predictions[0][predicted_class])
                    threat_level = threat_levels.get(class_label, "Unknown")  # 위험 등급 설정
            else:
                class_label = class_name
                prob = confidence
                threat_level = "Normal"  # enemy 외 클래스는 기본값

            # 바운딩 박스 및 레이블 그리기
            box_color = threat_colors.get(threat_level, (128, 128, 128))  # 위험 등급에 따른 색상
            cv2.rectangle(img_cv, (x1, y1), (x2, y2), box_color, 2)
            label = f"{class_label}: {prob:.2f} ({threat_level})"
            cv2.putText(img_cv, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

            filtered_results.append({
                'className': class_label,
                'id': idx,
                'threat': threat_level,  # 위험 등급 반영
                'bbox': [x1, y1, x2, y2],
                'confidence': prob
            })

    detected_objects.clear()
    detected_objects.extend(filtered_results)

    cv2.imwrite(str(tmp_path), img_cv)

    return JSONResponse(content=filtered_results)