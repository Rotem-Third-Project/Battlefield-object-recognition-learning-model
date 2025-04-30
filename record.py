import cv2
import os

video_path = 'try.mkv'  # 네 영상 파일명
output_dir = 'try'        # 저장할 폴더

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
print(f"FPS: {fps}")  # 60.0 나올 거야

count = 0
saved = 0

#frame_interval = int(fps / 20)  # 60 / 20 = 3 → 3프레임마다 1장 저장
frame_interval = int(fps / 2)


while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    if count % frame_interval == 0:
        filename = os.path.join(output_dir, f'frame_{saved:04d}.jpg')
        cv2.imwrite(filename, frame)
        saved += 1

    count += 1

cap.release()
print(f"{saved}장의 프레임 저장 완료!")
