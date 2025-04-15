from PIL import Image
import numpy as np
import os

def change_lux_pil(image, lux_diff):
    """
    이미지의 밝기를 lux_diff만큼 조정 (기준 LUX = 30000)
    """
    alpha = 1.2 + (lux_diff / 100000)
    alpha = max(0.1, min(alpha, 3.0))  # 너무 밝거나 어두운 값 제한
    beta = int(lux_diff / 1000)

    np_img = np.array(image).astype(np.float32)
    np_img = np.clip(alpha * np_img + beta, 0, 255).astype(np.uint8)
    return Image.fromarray(np_img)

def convert_images(input_folder, output_folder, current_lux=30000):
    """
    입력 폴더에 있는 .png 이미지를 밝기 보정 후 .jpg로 저장
    """
    base_lux = 30000
    lux_diff = current_lux - base_lux

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file_name in os.listdir(input_folder):
        if file_name.lower().endswith('.png'):
            img_path = os.path.join(input_folder, file_name)

            try:
                image = Image.open(img_path).convert("RGB")
            except Exception as e:
                print(f"❌ 이미지 로딩 실패: {file_name} → {e}")
                continue

            adjusted = change_lux_pil(image, lux_diff)

            new_name = os.path.splitext(file_name)[0] + '.jpg'
            save_path = os.path.join(output_folder, new_name)
            adjusted.save(save_path, format='JPEG')

            print(f"✅ 변환 완료: {file_name} → {save_path}")

convert_images(
    input_folder=r"C:\Users\acorn\OneDrive\문서\Tank Challenge\capture_images",
    output_folder=r"C:\pycode\Battlefield-object-recognition-learning-model\data\train",
    current_lux=5000  # 기준보다 낮으므로 어둡게 조정
)