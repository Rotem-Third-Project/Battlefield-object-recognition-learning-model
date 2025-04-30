import os

# 폴더 경로 설정
images_folder = "C:/Users/acorn/OneDrive/Desktop/yolov81/train/images"
labels_folder = "C:/Users/acorn/OneDrive/Desktop/yolov81/train/labels"

# 시작 인덱스 설정
start_index = 100

# images 폴더의 모든 jpg 파일 처리
image_files = sorted([f for f in os.listdir(images_folder) if f.endswith(".jpg")])

for idx, old_image_name in enumerate(image_files):
    # 기존 이미지 파일 이름
    # 예: Rear_0017_jpg.rf.ac44871ba09bb2563aa42c6a435af15e.jpg
    new_image_name = f"rear_{start_index + idx}.jpg"  # rear_100.jpg, rear_101.jpg, ...

    # 기존 레이블 파일 이름
    # 이미지 파일 이름에서 .jpg를 .txt로 변경
    old_label_name = old_image_name.replace(".jpg", ".txt")
    new_label_name = new_image_name.replace(".jpg", ".txt")

    # 이미지 파일 이름 변경
    old_image_path = os.path.join(images_folder, old_image_name)
    new_image_path = os.path.join(images_folder, new_image_name)
    if os.path.exists(old_image_path):
        os.rename(old_image_path, new_image_path)
        print(f"이미지 파일 이름 변경 완료: {old_image_name} -> {new_image_name}")
    else:
        print(f"이미지 파일 {old_image_name}이 존재하지 않습니다.")

    # 레이블 파일 이름 변경
    old_label_path = os.path.join(labels_folder, old_label_name)
    new_label_path = os.path.join(labels_folder, new_label_name)
    if os.path.exists(old_label_path):
        os.rename(old_label_path, new_label_path)
        print(f"레이블 파일 이름 변경 완료: {old_label_name} -> {new_label_name}")
    else:
        print(f"레이블 파일 {old_label_name}이 존재하지 않습니다.")