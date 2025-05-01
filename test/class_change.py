import os
import shutil

# 원본 데이터 디렉토리 경로
orig_label_dir = r"C:\Users\acorn\OneDrive\Desktop\EfficientnetData/train/labels"
orig_image_dir = r"C:\Users\acorn\OneDrive\Desktop\EfficientnetData/train/images"

# 새로운 데이터 디렉토리 경로
new_train_dir = r"C:\Users\acorn\OneDrive\Desktop\EfficientnetData/new_train"
new_label_dir = os.path.join(new_train_dir, "labels")
new_image_dir = os.path.join(new_train_dir, "images")

# 지원하는 이미지 확장자
image_extensions = (".jpg", ".jpeg", ".png")

# 새로운 디렉토리 생성
os.makedirs(new_label_dir, exist_ok=True)
os.makedirs(new_image_dir, exist_ok=True)

# 디렉토리 내 모든 .txt 파일 순회
for label_file in os.listdir(orig_label_dir):
    if label_file.endswith(".txt"):
        orig_label_path = os.path.join(orig_label_dir, label_file)
        new_label_path = os.path.join(new_label_dir, label_file)
        
        # 라벨 파일 읽기
        with open(orig_label_path, "r") as f:
            lines = f.readlines()
        
        # 유효한 라벨이 있는지 확인 (비어 있거나 공백만 있는 경우 제외)
        has_valid_label = False
        new_lines = []
        for line in lines:
            parts = line.strip().split()
            if parts:  # 비어 있지 않은 라인만 처리
                parts[0] = "0"  # 클래스 ID를 0으로 변경
                new_lines.append(" ".join(parts))
                has_valid_label = True
        
        if has_valid_label:
            # 수정된 라벨 파일 저장
            with open(new_label_path, "w") as f:
                for line in new_lines:
                    f.write(line + "\n")
            
            # 쌍을 이루는 이미지 파일 복사
            base_name = os.path.splitext(label_file)[0]
            for ext in image_extensions:
                orig_image_path = os.path.join(orig_image_dir, base_name + ext)
                new_image_path = os.path.join(new_image_dir, base_name + ext)
                if os.path.exists(orig_image_path):
                    shutil.copy2(orig_image_path, new_image_path)
                    print(f"Copied image file: {new_image_path}")
                    break
        else:
            # 라벨이 없는 경우, 복사하지 않고 로그 출력
            print(f"Skipped empty label file: {orig_label_path}")