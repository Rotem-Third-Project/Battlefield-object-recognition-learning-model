import os
import cv2
import random
from collections import Counter
import tensorflow as tf

# ── GPU 설정 ──
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)

# 설정
dataset_dir = r"C:\Users\user\Downloads\EfficientnetData\EfficientnetData\train"
output_dir  = r"C:\Users\user\Desktop\crop"
class_names = ["Enemy_Front","Enemy_Rear","Enemy_Side"]
img_size    = (240, 240)    # EfficientNet-B1 권장 해상도

# 출력 디렉토리 생성
for cls in class_names:
    os.makedirs(os.path.join(output_dir, cls), exist_ok=True)

img_dir   = os.path.join(dataset_dir, "images")
label_dir = os.path.join(dataset_dir, "labels")

# 크롭 추적용
cropped_images_per_class = {cls: [] for cls in class_names}

# TF 리사이즈 함수 (GPU에서 실행)
def tf_resize(image, size):
    img = tf.convert_to_tensor(image, dtype=tf.uint8)
    img = tf.image.resize(img, size)
    return tf.cast(img, tf.uint8).numpy()

# 이미지 크롭 → 저장
for img_file in os.listdir(img_dir):
    if not img_file.lower().endswith((".jpg",".png")): continue

    path = os.path.join(img_dir, img_file)
    img  = cv2.imread(path)
    if img is None:
        print("Failed to load:", path)
        continue
    H, W = img.shape[:2]

    lbl_path = os.path.join(label_dir, os.path.splitext(img_file)[0]+".txt")
    if not os.path.exists(lbl_path):
        print("Label missing:", lbl_path)
        continue

    lines = [l.strip() for l in open(lbl_path, encoding="utf-8") if l.strip()]
    if not lines: continue

    for idx, line in enumerate(lines):
        parts = line.split()
        if len(parts)<5:
            print("Bad label:", line); continue

        cid = int(parts[0])
        xc,yc,w,h = map(float, parts[1:5])
        xc, yc, w, h = xc*W, yc*H, w*W, h*H

        x1,y1 = int(xc-w/2), int(yc-h/2)
        x2,y2 = int(xc+w/2), int(yc+h/2)

        crop = img[max(y1,0):min(y2,H), max(x1,0):min(x2,W)]
        if crop.size==0:
            print("Empty crop:", img_file, idx); continue

        # GPU에서 리사이즈
        crop = tf_resize(crop, img_size)

        cls_name = class_names[cid]
        out_fname = f"train_{img_file}_{idx}.jpg"
        out_path  = os.path.join(output_dir, cls_name, out_fname)
        cv2.imwrite(out_path, crop)
        cropped_images_per_class[cls_name].append(out_path)

# 클래스별 개수 출력
cropped_counts = Counter()
for cls in class_names:
    cnt = len(cropped_images_per_class[cls])
    cropped_counts[cls] = cnt
    print(f"Initial cropped images for {cls}: {cnt}")

min_count = min(cropped_counts.values())
print(f"Minimum class count: {min_count}. Balancing to this count.")

# 초과 삭제
for cls in class_names:
    excess = cropped_counts[cls] - min_count
    if excess>0:
        to_del = random.sample(cropped_images_per_class[cls], excess)
        for p in to_del:
            try:
                os.remove(p)
            except: pass
        cropped_images_per_class[cls] = [p for p in cropped_images_per_class[cls] if p not in to_del]

# 최종 개수
for cls in class_names:
    final = len([f for f in os.listdir(os.path.join(output_dir,cls)) if f.lower().endswith((".jpg",".png"))])
    print(f"Final images for {cls} after balancing: {final}")

print("Cropping and balancing completed.")
