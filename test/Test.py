from ultralytics import YOLO
import cv2
import os

# 모델과 동영상 파일 경로 설정
model_path = r"C:\Users\acorn\OneDrive\Desktop\MyWork\Battlefield-object-recognition-learning-model\app\models\yolo_weights\best.pt"
video_path = r"C:\Users\acorn\OneDrive\Desktop\2025-05-01 10-29-44.mkv"
output_path = r"C:\Users\acorn\OneDrive\Desktop\output_detected_video.mp4"  # 결과 동영상 저장 경로

# YOLO 모델 로드
model = YOLO(model_path)

# 동영상 파일 열기
cap = cv2.VideoCapture(video_path)

# 동영상 속성 가져오기
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# 출력 동영상 설정
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # YOLO로 객체 감지
    results = model(frame)

    # 감지된 결과를 프레임에 렌더링
    annotated_frame = results[0].plot()  # 바운딩 박스와 라벨을 프레임에 그림

    # 결과 프레임을 출력 동영상에 쓰기
    out.write(annotated_frame)

# 리소스 해제
cap.release()
out.release()
cv2.destroyAllWindows()

print(f"감지 완료! 결과 동영상이 {output_path}에 저장되었습니다.")