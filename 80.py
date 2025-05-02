import os

label_dir = r"C:\project\Battlefield-object-recognition-learning-model\train3\filtered_labels"

# 모든 .txt 파일 순회
for filename in os.listdir(label_dir):
    if filename.endswith(".txt"):
        file_path = os.path.join(label_dir, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 클래스 ID 80을 0으로 바꿈
        new_lines = []
        for line in lines:
            parts = line.strip().split()
            if parts and parts[0] == '80':
                parts[0] = '0'
            new_lines.append(' '.join(parts) + '\n')

        # 덮어쓰기
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

print("✅ 모든 라벨 파일에서 클래스 ID 80 → 0 으로 변환 완료!")
