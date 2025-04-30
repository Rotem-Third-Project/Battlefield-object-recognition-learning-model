import os
import cv2
import random
from collections import Counter

# 설정
dataset_dir = r"C:\Users\acorn\OneDrive\Desktop\EfficientnetData\train"
output_dir = r"C:\Users\acorn\OneDrive\Desktop\real_efficientnet_dataset"
class_names = ["Enemy_Front", "Enemy_Rear", "Enemy_Side"]  # Unlabeled 제외
img_size = (224, 224)

# 출력 디렉토리 생성
for class_name in class_names:
    os.makedirs(os.path.join(output_dir, class_name), exist_ok=True)

img_dir = os.path.join(dataset_dir, "images")
label_dir = os.path.join(dataset_dir, "labels")

# 클래스별 크롭된 이미지 추적
cropped_images_per_class = {class_name: [] for class_name in class_names}

# 이미지 크롭 및 저장
for img_file in os.listdir(img_dir):
    if not img_file.lower().endswith((".jpg", ".png")):
        continue

    img_path = os.path.join(img_dir, img_file)
    img = cv2.imread(img_path)
    if img is None:
        print(f"Failed to load image: {img_path}")
        continue
    img_height, img_width = img.shape[:2]

    label_file = os.path.splitext(img_file)[0] + ".txt"
    label_path = os.path.join(label_dir, label_file)
    if not os.path.exists(label_path):
        print(f"Label file not found: {label_path}")
        continue

    with open(label_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines or all(not line.strip() for line in lines):  # Unlabeled 제외
        continue

    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            print(f"Invalid label format in {label_path}: {line}")
            continue

        class_id = int(parts[0])
        x_center, y_center, width, height = map(float, parts[1:5])

        x_center *= img_width
        y_center *= img_height
        width *= img_width
        height *= img_height

        x1 = int(x_center - width / 2)
        y1 = int(y_center - height / 2)
        x2 = int(x_center + width / 2)
        y2 = int(y_center + height / 2)

        cropped_img = img[max(y1, 0):min(y2, img_height), max(x1, 0):min(x2, img_width)]
        if cropped_img.size == 0:
            print(f"Empty crop in {img_file}, box {idx}")
            continue

        cropped_img = cv2.resize(cropped_img, img_size)
        class_name = class_names[class_id]
        output_filename = f"train_{img_file}_{idx}.jpg"
        output_path = os.path.join(output_dir, class_name, output_filename)
        cv2.imwrite(output_path, cropped_img)

        # 크롭된 이미지 추적
        cropped_images_per_class[class_name].append(output_path)

# 클래스별 크롭된 이미지 개수 계산 및 출력
cropped_counts = Counter()
for class_name in class_names:
    count = len(cropped_images_per_class[class_name])
    cropped_counts[class_name] = count
    print(f"Initial cropped images for {class_name}: {count}")

# 가장 적은 클래스 장수 기준 설정
min_count = min(cropped_counts.values())
print(f"Minimum class count: {min_count}. Balancing all classes to this count.")

# 초과된 이미지 삭제
for class_name in class_names:
    current_count = cropped_counts[class_name]
    if current_count > min_count:
        excess_count = current_count - min_count
        # 초과된 이미지 중 랜덤으로 선택하여 삭제
        images_to_delete = random.sample(cropped_images_per_class[class_name], excess_count)
        for image_path in images_to_delete:
            try:
                os.remove(image_path)
                print(f"Deleted excess image: {image_path}")
            except Exception as e:
                print(f"Error deleting {image_path}: {e}")
        # 삭제 후 남은 이미지 업데이트
        cropped_images_per_class[class_name] = [img for img in cropped_images_per_class[class_name] if img not in images_to_delete]

# 최종 클래스별 이미지 개수 확인
final_counts = Counter()
for class_name in class_names:
    final_count = len([f for f in os.listdir(os.path.join(output_dir, class_name)) if f.lower().endswith((".jpg", ".png"))])
    final_counts[class_name] = final_count
    print(f"Final images for {class_name} after balancing: {final_count}")

print("Cropping and balancing completed.")