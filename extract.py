import cv2
import os

print(cv2.__version__)

filepath = './s2 1 90 270.mkv'
video = cv2.VideoCapture(filepath)

if not video.isOpened():
    print("Could not Open :", filepath)
    exit(0)
    
length = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = video.get(cv2.CAP_PROP_FPS)

print("length :", length)
print("width :", width)
print("height :", height)
print("fps :", fps)

# 저장 폴더 생성
output_dir = filepath[:-4]
try:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
except OSError:
    print('Error: Creating directory. ' + output_dir)

# 1초에 5프레임 저장하려면 몇 프레임마다 저장할지 계산
interval = int(fps // 5)
if interval < 1:
    interval = 1  # fps가 5 미만일 때는 모든 프레임 저장

count = 0
saved_frame_count = 0

while video.isOpened():
    ret, image = video.read()
    if not ret:
        break

    if count % interval == 0:
        filename = os.path.join(output_dir, f"{saved_frame_count:04d}.jpg")
        cv2.imwrite(filename, image)
        print('Saved frame number :', count)
        saved_frame_count += 1

    count += 1

video.release()