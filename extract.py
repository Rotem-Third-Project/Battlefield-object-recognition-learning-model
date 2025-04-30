import cv2
import os
import sys
print(cv2.__version__)
# ✅ 콘솔 인코딩을 UTF-8로 설정
sys.stdout.reconfigure(encoding='utf-8')


# ✅ 영상 폴더 경로
folder_path = r'C:\Users\acorn\Videos'

# ✅ 공통 저장 폴더
output_dir = os.path.join(folder_path, 'extracted_frames')
os.makedirs(output_dir, exist_ok=True)

# ✅ 허용되는 영상 확장자
video_extensions = ['.mp4', '.avi', '.mkv', '.mov']

# ✅ 저장될 프레임 전체 시퀀스 번호 (전역)
global_frame_count = 0

# ✅ 폴더 내 모든 영상 반복
for file_name in os.listdir(folder_path):
    if not any(file_name.lower().endswith(ext) for ext in video_extensions):
        continue

    filepath = os.path.join(folder_path, file_name)
    video = cv2.VideoCapture(filepath)

    if not video.isOpened():
        print("Could not Open :", filepath)
        continue

    length = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video.get(cv2.CAP_PROP_FPS)

    print(f"\n📂 처리 중: {file_name} | 프레임 수: {length} | FPS: {fps}")

    # ✅ 1초에 5프레임 저장
    interval = int(fps // 5)
    if interval < 1:
        interval = 1

    count = 0

    while video.isOpened():
        ret, image = video.read()
        if not ret:
            break

        if count % interval == 0:
            filename = os.path.join(output_dir, f"Front_{global_frame_count:04d}.jpg")
            cv2.imwrite(filename, image)
            print(f"Saved: {filename}")
            global_frame_count += 1

        count += 1

    video.release()

print("\n✅ 모든 영상 처리 및 저장 완료!")
