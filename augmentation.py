import os
import cv2
import shutil
import random
from collections import Counter

# 설정
dataset_dir = r"C:\Users\acorn\OneDrive\Desktop\EfficientnetData\train"  # 데이터셋 train 폴더 경로
output_dir = dataset_dir  # 증강된 파일을 원본 train 폴더에 추가
class_names = {0: "Enemy_Front", 1: "Enemy_Rear", 2: "Enemy_Side"}  # 클래스 ID와 이름 매핑
target_classes = [0, 1, 2]  # 증강할 클래스 (모두 포함)
brightness_alpha_1 = 1.4  # 1차 증강 밝기 스케일
brightness_beta_1 = 15    # 1차 증강 밝기 오프셋
brightness_alpha_2 = 1.2  # 2차 증강 밝기 스케일 (조금 낮춤)
brightness_beta_2 = 10    # 2차 증강 밝기 오프셋 (조금 낮춤)
target_count = 10000  # 목표 장수

# 디렉토리 확인
img_dir = os.path.join(dataset_dir, "images")
label_dir = os.path.join(dataset_dir, "labels")
img_output_dir = os.path.join(output_dir, "images")
label_output_dir = os.path.join(output_dir, "labels")

# 디렉토리 존재 여부 확인
if not os.path.exists(dataset_dir):
    print(f"Dataset directory not found: {dataset_dir}")
    exit(1)
if not os.path.exists(img_dir):
    print(f"Image directory not found: {img_dir}")
    exit(1)
if not os.path.exists(label_dir):
    print(f"Label directory not found: {label_dir}")
    exit(1)

os.makedirs(img_output_dir, exist_ok=True)
os.makedirs(label_output_dir, exist_ok=True)

# 라벨링 없는 파일 확인 함수
def is_empty_label_file(label_path):
    try:
        with open(label_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return len(lines) == 0
    except Exception as e:
        print(f"Error reading {label_path}: {e}")
        return False

# 라벨링 없는 파일 삭제
unlabeled_pairs = []
img_files = [f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png"))]
print(f"Found {len(img_files)} image files in {img_dir}")

for img_file in img_files:
    label_file = os.path.splitext(img_file)[0] + ".txt"
    label_path = os.path.join(label_dir, label_file)
    if os.path.exists(label_path) and is_empty_label_file(label_path):
        unlabeled_pairs.append((img_file, label_file))

print(f"Found {len(unlabeled_pairs)} unlabeled image-label pairs")

# 모든 Unlabeled 파일 삭제
for img_file, label_file in unlabeled_pairs:
    img_path = os.path.join(img_dir, img_file)
    label_path = os.path.join(label_dir, label_file)
    try:
        os.remove(img_path)
        print(f"Deleted image: {img_path}")
        os.remove(label_path)
        print(f"Deleted label: {label_path}")
    except Exception as e:
        print(f"Error deleting {img_path} or {label_path}: {e}")

# 클래스별 파일 리스트 수집
class_image_map = {0: [], 1: [], 2: []}  # 클래스별 이미지 파일 리스트
# Unlabeled 삭제 후 남은 이미지 파일 목록 갱신
img_files = [f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png"))]
print(f"Found {len(img_files)} image files after deletion in {img_dir}")

for img_file in img_files:
    label_file = os.path.splitext(img_file)[0] + ".txt"
    label_path = os.path.join(label_dir, label_file)
    if not os.path.exists(label_path):
        print(f"Label file not found: {label_path}")
        continue

    try:
        with open(label_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading label file {label_path}: {e}")
        continue

    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            print(f"Invalid label format in {label_path}: {line}")
            continue
        try:
            class_id = int(parts[0])
            if class_id in target_classes:
                class_image_map[class_id].append(img_file)
                break  # 한 이미지에 여러 객체가 있을 수 있으므로 첫 번째 객체만 고려
        except ValueError:
            print(f"Invalid class ID in {label_path}: {line}")
            continue

# 클래스별 이미지 수 확인
for class_id in target_classes:
    print(f"{class_names[class_id]}: {len(class_image_map[class_id])} images")

# 밝기 조정 함수
def adjust_brightness(img, alpha, beta):
    adjusted_img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
    return adjusted_img

# 1차 증강: 모든 이미지를 2배로 늘리기
for class_id in target_classes:
    for img_file in class_image_map[class_id]:
        # 이미지 로드
        img_path = os.path.join(img_dir, img_file)
        img = cv2.imread(img_path)
        if img is None:
            print(f"Failed to load image: {img_path}")
            continue

        # 라벨 파일 경로
        label_file = os.path.splitext(img_file)[0] + ".txt"
        label_path = os.path.join(label_dir, label_file)

        # 1차 증강 이미지 생성
        adjusted_img = adjust_brightness(img, brightness_alpha_1, brightness_beta_1)

        # 증강된 이미지 저장
        adjusted_img_file = f"bright1_{img_file}"
        adjusted_img_path = os.path.join(img_output_dir, adjusted_img_file)
        try:
            cv2.imwrite(adjusted_img_path, adjusted_img)
        except Exception as e:
            print(f"Failed to save augmented image {adjusted_img_path}: {e}")
            continue

        # 라벨 파일 복사
        adjusted_label_file = os.path.splitext(adjusted_img_file)[0] + ".txt"
        adjusted_label_path = os.path.join(label_output_dir, adjusted_label_file)
        try:
            shutil.copy(label_path, adjusted_label_path)
        except Exception as e:
            print(f"Failed to copy label file to {adjusted_label_path}: {e}")
            continue

        print(f"1st Augmented: {adjusted_img_file} for class {class_names[class_id]}")

# 클래스별 증강 후 이미지 수 확인
class_image_map_after_first = {0: [], 1: [], 2: []}
img_files = [f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png"))]
for img_file in img_files:
    label_file = os.path.splitext(img_file)[0] + ".txt"
    label_path = os.path.join(label_dir, label_file)
    if not os.path.exists(label_path):
        continue

    try:
        with open(label_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading label file {label_path}: {e}")
        continue

    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            class_id = int(parts[0])
            if class_id in target_classes:
                class_image_map_after_first[class_id].append(img_file)
                break
        except ValueError:
            continue

for class_id in target_classes:
    print(f"After 1st augmentation, {class_names[class_id]}: {len(class_image_map_after_first[class_id])} images")

# 2차 증강: 부족한 장수만큼 추가 증강
for class_id in target_classes:
    current_count = len(class_image_map_after_first[class_id])
    additional_needed = target_count - current_count
    if additional_needed <= 0:
        print(f"No additional augmentation needed for {class_names[class_id]}")
        continue

    # 원본 이미지에서 무작위로 선택하여 추가 증강
    original_images = class_image_map[class_id]  # 원본 이미지 사용
    for i in range(additional_needed):
        img_file = random.choice(original_images)
        img_path = os.path.join(img_dir, img_file)
        img = cv2.imread(img_path)
        if img is None:
            print(f"Failed to load image: {img_path}")
            continue

        label_file = os.path.splitext(img_file)[0] + ".txt"
        label_path = os.path.join(label_dir, label_file)

        # 2차 증강 이미지 생성
        adjusted_img = adjust_brightness(img, brightness_alpha_2, brightness_beta_2)

        # 증강된 이미지 저장
        adjusted_img_file = f"bright2_{i}_{img_file}"
        adjusted_img_path = os.path.join(img_output_dir, adjusted_img_file)
        try:
            cv2.imwrite(adjusted_img_path, adjusted_img)
        except Exception as e:
            print(f"Failed to save 2nd augmented image {adjusted_img_path}: {e}")
            continue

        # 라벨 파일 복사
        adjusted_label_file = os.path.splitext(adjusted_img_file)[0] + ".txt"
        adjusted_label_path = os.path.join(label_output_dir, adjusted_label_file)
        try:
            shutil.copy(label_path, adjusted_label_path)
        except Exception as e:
            print(f"Failed to copy label file to {adjusted_label_path}: {e}")
            continue

        print(f"2nd Augmented: {adjusted_img_file} for class {class_names[class_id]}")

# 최종 클래스별 이미지 수 확인
final_class_counts = Counter()
label_files = [f for f in os.listdir(label_dir) if f.lower().endswith(".txt")]
for label_file in label_files:
    label_path = os.path.join(label_dir, label_file)
    try:
        with open(label_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                class_id = int(parts[0])
                final_class_counts[class_id] += 1
                break
            except ValueError:
                continue
    except Exception as e:
        print(f"Error reading {label_file}: {e}")

print("Final class counts after all augmentations:")
for class_id in target_classes:
    print(f"{class_names[class_id]}: {final_class_counts[class_id]} images")