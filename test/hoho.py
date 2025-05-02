from ultralytics import YOLO

def main():
    model = YOLO("yolov8n.pt")  # or your custom pretrained model

    data_yaml = r"C:\project\Battlefield-object-recognition-learning-model\data1.yaml"

    model.train(
        data=data_yaml,            # your data.yaml 경로
        epochs=60,                 # 충분히 학습하되 조기종료로 불필요 학습 방지
        batch=16,                  # GPU 메모리 허용 한도 내 최대 배치
        imgsz=640,                 # 입력 해상도

        device='0',                # 첫 번째 GPU
        name='train_enemy_best_plus',

        # — 러닝 레이트 & 스케줄링 —
        lr0=2e-3,                  # 큰 배치(16) → lr도 2배
        lrf=0.2,                   # Cosine 스케줄링

        # — 데이터 증강 (강력하게) —
        augment=True,              # Flip/Rotate/Scale/Shear/Perspective 기본 적용
        mosaic=1.0,                # 모자이크 100%
        mixup=0.5,                 # MixUp 50%
        hsv_h=0.015, hsv_s=0.7, hsv_v=0.4,

        # — 정규화 & 구조적 일반화 —
        weight_decay=5e-4,         # L2 정규화
        dropout=0.1,               # Head에 드롭아웃 10%

        # — 조기 종료 —
        patience=15,               # 15 에포크 동안 검증 향상 없으면 중단

        save_period=10,            # 10 에포크마다 체크포인트 저장
        workers=4                  # 데이터 로딩 스레드
    )

if __name__ == "__main__":
    main()
