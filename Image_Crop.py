import os
import cv2

dataset_dir = r"C:\Users\acorn\OneDrive\Desktop\Object-recognition.v18i.yolov8\train"
output_dir = r"C:\Users\acorn\OneDrive\Desktop\efficientnet_dataset"
class_names = ["Enemy_Front", "Enemy_Rear", "Enemy_Side"]  # Unlabeled 제외
img_size = (224, 224)

for class_name in class_names:
    os.makedirs(os.path.join(output_dir, class_name), exist_ok=True)

img_dir = os.path.join(dataset_dir, "images")
label_dir = os.path.join(dataset_dir, "labels")

for img_file in os.listdir(img_dir):
    if not img_file.lower().endswith((".jpg", ".png")):
        continue

    img_path = os.path.join(img_dir, img_file)
    img = cv2.imread(img_path)
    if img is None:
        continue
    img_height, img_width = img.shape[:2]

    label_file = os.path.splitext(img_file)[0] + ".txt"
    label_path = os.path.join(label_dir, label_file)
    if not os.path.exists(label_path):
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
        x_center, y_center, width, height = map(float, parts[1:])

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
        output_path = os.path.join(output_dir, class_name, f"train_{img_file}_{idx}.jpg")
        cv2.imwrite(output_path, cropped_img)