import os
import cv2
import shutil
import random
from collections import Counter

# 설정
dataset_dir = r"C:\Users\acorn\OneDrive\Desktop\Object-recognition.v18i.yolov8\train"  # 데이터셋 train 폴더 경로
output_dir = dataset_dir  # 증강된 파일을 원본 train 폴더에 추가
class_names = {0: "Enemy_Front", 1: "Enemy_Rear", 2: "Enemy_Side", -1: "Unlabeled"}  # 클래스 ID와 이름 매핑
target_classes = [0, 1]  # 증강할 클래스
brightness_alpha = 1.4  # 밝기 스케일
brightness_beta = 15    # 밝기 오프셋
delete_count = 2000  # 삭제할 라벨링 없는 파일 쌍 수

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

# 라벨링 없는 파일 쌍 찾기
def is_empty_label_file(label_path):
    try:
        with open(label_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return len(lines) == 0
    except Exception as e:
        print(f"Error reading {label_path}: {e}")
        return False

unlabeled_pairs = []
img_files = [f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png"))]
print(f"Found {len(img_files)} image files in {img_dir}")

for img_file in img_files:
    label_file = os.path.splitext(img_file)[0] + ".txt"
    label_path = os.path.join(label_dir, label_file)
    if os.path.exists(label_path) and is_empty_label_file(label_path):
        unlabeled_pairs.append((img_file, label_file))

print(f"Found {len(unlabeled_pairs)} unlabeled image-label pairs")

# 무작위로 2000개 삭제
if len(unlabeled_pairs) < delete_count:
    print(f"Warning: Only {len(unlabeled_pairs)} unlabeled pairs found, requested {delete_count} to delete")
    delete_count = len(unlabeled_pairs)

if delete_count > 0:
    pairs_to_delete = random.sample(unlabeled_pairs, delete_count)
    for img_file, label_file in pairs_to_delete:
        img_path = os.path.join(img_dir, img_file)
        label_path = os.path.join(label_dir, label_file)
        try:
            os.remove(img_path)
            print(f"Deleted image: {img_path}")
            os.remove(label_path)
            print(f"Deleted label: {label_path}")
        except Exception as e:
            print(f"Error deleting {img_path} or {label_path}: {e}")
else:
    print("No unlabeled pairs to delete")

# 밝기 조정 함수
def adjust_brightness(img):
    adjusted_img = cv2.convertScaleAbs(img, alpha=brightness_alpha, beta=brightness_beta)
    return adjusted_img

# 증강 처리
img_files = [f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png"))]
print(f"Found {len(img_files)} image files after deletion in {img_dir}")

for img_file in img_files:
    # 이미지 로드
    img_path = os.path.join(img_dir, img_file)
    img = cv2.imread(img_path)
    if img is None:
        print(f"Failed to load image: {img_path}")
        continue
    
    # 라벨 파일 로드
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
    
    # 대상 클래스(Enemy_Front 또는 Enemy_Rear)가 포함된 이미지인지 확인
    has_target_class = False
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
                has_target_class = True
                break
        except ValueError:
            print(f"Invalid class ID in {label_path}: {line}")
            continue
    
    if not has_target_class:
        continue
    
    # 이미지 밝기 조정
    adjusted_img = adjust_brightness(img)
    
    # 증강된 이미지 저장
    adjusted_img_file = f"bright_{img_file}"
    adjusted_img_path = os.path.join(img_output_dir, adjusted_img_file)
    try:
        cv2.imwrite(adjusted_img_path, adjusted_img)
    except Exception as e:
        print(f"Failed to save augmented image {adjusted_img_path}: {e}")
        continue
    
    # 원본 라벨 파일 복사
    adjusted_label_file = os.path.splitext(adjusted_img_file)[0] + ".txt"
    adjusted_label_path = os.path.join(label_output_dir, adjusted_label_file)
    try:
        shutil.copy(label_path, adjusted_label_path)
    except Exception as e:
        print(f"Failed to copy label file to {adjusted_label_path}: {e}")
        continue
    
    print(f"Augmented: {adjusted_img_file}")

print("Brightness augmentation completed.")

# 클래스 비율 확인 (라벨링 없는 이미지 포함)
class_counts = Counter()
label_files = [f for f in os.listdir(label_dir) if f.lower().endswith(".txt")]
print(f"Found {len(label_files)} label files in {label_dir}")

if not label_files:
    print("No label files found. Please check the label directory and file extensions.")
else:
    for label_file in label_files:
        label_path = os.path.join(label_dir, label_file)
        try:
            with open(label_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if is_empty_label_file(label_path):
                class_counts[-1] += 1  # Unlabeled 이미지 카운트
            else:
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) < 5:
                        print(f"Skipping invalid line in {label_file}: {line}")
                        continue
                    try:
                        class_id = int(parts[0])
                        class_counts[class_id] += 1
                    except ValueError:
                        print(f"Invalid class ID in {label_file}: {line}")
                        continue
        except Exception as e:
            print(f"Error reading {label_file}: {e}")
            continue

if class_counts:
    print("Class counts after augmentation and deletion:", {class_names[k]: v for k, v in class_counts.items()})
else:
    print("No classes counted. Check label files for valid data.")