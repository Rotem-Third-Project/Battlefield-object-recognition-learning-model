import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, models
from torchvision.models import MobileNet_V3_Small_Weights
import albumentations as A
from albumentations.pytorch import ToTensorV2
import numpy as np
from tqdm import tqdm
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns

# 데이터셋 경로: enemy_front, enemy_side, enemy_rear 폴더가 포함된 디렉토리
data_dir = r"C:\Users\acorn\OneDrive\Desktop\EfficientnetData\real_efficientnet_dataset"

# 하이퍼파라미터 설정
num_classes = 3  # 클래스 수: enemy_front, enemy_side, enemy_rear
batch_size = 64  # 배치 크기: 30,000장 데이터셋에 적합, CPU 환경 고려
initial_epochs = 25  # 초기 학습 에포크: 최대 25번, Early Stopping으로 조기 종료 가능
finetune_epochs = 10  # Fine-tuning 에포크: 10번 추가 학습
initial_lr = 0.001  # 초기 학습률: Classifier 학습에 사용
finetune_lr = 0.0001  # Fine-tuning 학습률: 낮은 학습률로 과적합 방지
patience = 5  # Early Stopping: 검증 손실이 5 에포크 동안 개선되지 않으면 종료
weight_decay = 1e-4  # L2 정규화: 과적합 방지를 위해 가중치 감쇠

# 디바이스 설정: CPU 사용 (오류에서 CPU로 확인됨)
device = torch.device("cpu")
print(f"Using device: {device}")

# 데이터셋 구조 확인 함수: 클래스 폴더와 이미지 수를 점검하여 데이터셋 무결성 확인
def check_dataset_structure(data_dir):
    expected_classes = ['enemy_front', 'enemy_side', 'enemy_rear']  # 예상 클래스 목록
    print("Checking dataset structure...")
    for cls in expected_classes:
        cls_path = os.path.join(data_dir, cls)
        if not os.path.isdir(cls_path):
            raise ValueError(f"Class folder {cls_path} does not exist!")  # 폴더 누락 시 오류
        num_images = len([f for f in os.listdir(cls_path) if f.endswith(('.jpg', '.jpeg', '.png'))])
        print(f"{cls}: {num_images} images")  # 각 클래스별 이미지 수 출력
    print("Dataset structure check completed.")

# 데이터 증강 및 전처리
# - Train: 데이터가 이미 증강된 상태이므로 가벼운 증강(좌우 반전, 회전, 밝기 조정) 적용
# - Validation/Test: 증강 없이 리사이즈와 정규화만 적용하여 데이터 왜곡 방지
train_transforms = A.Compose([
    A.Resize(224, 224),  # MobileNetV3-Small 입력 크기 (224x224)
    A.HorizontalFlip(p=0.5),  # 50% 확률로 좌우 반전 (데이터 다양성 증가)
    A.RandomRotate90(p=0.3),  # 30% 확률로 90도 회전 (방향 다양성)
    A.RandomBrightnessContrast(p=0.3),  # 30% 확률로 밝기/대비 조정 (조명 변화 대응)
    A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),  # ImageNet 정규화
    ToTensorV2()  # PyTorch 텐서로 변환
])

val_test_transforms = A.Compose([
    A.Resize(224, 224),  # 동일한 입력 크기 유지
    A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),  # 동일한 정규화
    ToTensorV2()  # 텐서 변환
])

# 데이터셋 클래스: torchvision의 ImageFolder와 albumentations를 결합하여 커스텀 데이터셋 생성
class CustomImageDataset(torch.utils.data.Dataset):
    def __init__(self, dataset, transform=None):
        self.dataset = dataset  # ImageFolder 데이터셋
        self.transform = transform  # albumentations 변환 파이프라인

    def __len__(self):
        return len(self.dataset)  # 데이터셋 크기 반환

    def __getitem__(self, idx):
        img, label = self.dataset[idx]  # 이미지와 레이블 가져오기
        img = np.array(img)  # PIL 이미지를 numpy 배열로 변환 (albumentations용)
        if self.transform:
            augmented = self.transform(image=img)  # 증강 적용
            img = augmented['image']
        return img, label  # 변환된 이미지와 레이블 반환

# Early Stopping 클래스: 검증 손실이 개선되지 않으면 학습 조기 종료
class EarlyStopping:
    def __init__(self, patience=5, delta=0, path='checkpoint.pt'):
        self.patience = patience  # 개선되지 않은 에포크 허용 횟수
        self.delta = delta  # 손실 개선 최소 기준
        self.path = path  # 최적 모델 저장 경로
        self.counter = 0  # 개선되지 않은 에포크 카운터
        self.best_score = None  # 최고 성능 스코어
        self.early_stop = False  # 조기 종료 플래그
        self.best_loss = np.Inf  # 최소 손실 기록

    def __call__(self, val_loss, model):
        score = -val_loss  # 손실이 낮을수록 좋은 스코어
        if self.best_score is None:
            self.best_score = score
            self.save_checkpoint(val_loss, model)  # 초기 모델 저장
        elif score < self.best_score + self.delta:
            self.counter += 1
            print(f'EarlyStopping counter: {self.counter} out of {self.patience}')
            if self.counter >= self.patience:
                self.early_stop = True  # patience 초과 시 종료
        else:
            self.best_score = score
            self.save_checkpoint(val_loss, model)  # 개선 시 모델 저장
            self.counter = 0

    def save_checkpoint(self, val_loss, model):
        torch.save(model.state_dict(), self.path)  # 모델 가중치 저장
        self.best_loss = val_loss

# 학습 함수: 초기 학습과 Fine-tuning을 처리
def train_model(model, train_loader, val_loader, criterion, optimizer, scheduler, num_epochs, phase="initial"):
    # Early Stopping 초기화: 초기 학습에서만 사용
    early_stopping = EarlyStopping(patience=patience, path=f'mobilenetv3_small_{phase}.pt')
    
    for epoch in range(num_epochs):
        # Training 모드: 모델을 학습 상태로 전환
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        # Train 데이터로 학습
        for images, labels in tqdm(train_loader, desc=f"{phase.capitalize()} Epoch {epoch+1}/{num_epochs}"):
            images, labels = images.to(device), labels.to(device)  # 데이터를 디바이스로 이동
            optimizer.zero_grad()  # 이전 그래디언트 초기화
            outputs = model(images)  # 모델 예측
            loss = criterion(outputs, labels)  # 손실 계산
            loss.backward()  # 역전파로 그래디언트 계산
            optimizer.step()  # 가중치 업데이트
            
            train_loss += loss.item() * images.size(0)  # 배치 손실 합산
            _, predicted = torch.max(outputs, 1)  # 예측 클래스
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()  # 정확도 계산
        
        train_loss = train_loss / train_total  # 평균 손실
        train_acc = train_correct / train_total  # 평균 정확도
        
        # Validation 모드: 모델을 평가 상태로 전환
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        # Validation 데이터로 평가 (그래디언트 계산 비활성화)
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                
                val_loss += loss.item() * images.size(0)
                _, predicted = torch.max(outputs, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
        
        val_loss = val_loss / val_total  # 평균 손실
        val_acc = val_correct / val_total  # 평균 정확도
        
        # 학습 결과 출력
        print(f"{phase.capitalize()} Epoch {epoch+1}/{num_epochs}:")
        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}")
        print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")
        
        # Learning rate 스케줄링: 검증 손실 기준 학습률 감소
        scheduler.step(val_loss)
        
        # 초기 학습에서만 Early Stopping 적용
        if phase == "initial":
            early_stopping(val_loss, model)
            if early_stopping.early_stop:
                print("Early stopping triggered")
                break
    
    # 초기 학습 종료 후 최적 모델 로드
    if phase == "initial":
        model.load_state_dict(torch.load(f'mobilenetv3_small_{phase}.pt'))
    return model

# 평가 함수: 손실, 정확도, 정밀도, 재현율, F1-Score, Confusion Matrix 계산
def evaluate_model(model, loader, criterion, dataset_name="Test"):
    model.eval()  # 평가 모드
    loss = 0.0
    correct = 0
    total = 0
    all_preds = []
    all_labels = []
    
    # 그래디언트 계산 없이 평가
    with torch.no_grad():
        for images, labels in tqdm(loader, desc=f"Evaluating on {dataset_name} Set"):
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss += criterion(outputs, labels).item() * images.size(0)  # 손실 합산
            
            _, predicted = torch.max(outputs, 1)  # 예측 클래스
            total += labels.size(0)
            correct += (predicted == labels).sum().item()  # 정확도 계산
            
            all_preds.extend(predicted.cpu().numpy())  # 예측 레이블 저장
            all_labels.extend(labels.cpu().numpy())  # 실제 레이블 저장
    
    loss = loss / total  # 평균 손실
    acc = correct / total  # 평균 정확도
    
    # 클래스별 정밀도, 재현율, F1-Score 계산
    precision, recall, f1, _ = precision_recall_fscore_support(all_labels, all_preds, average=None)
    class_names = ['enemy_front', 'enemy_side', 'enemy_rear']  # 클래스 이름 정의
    report = classification_report(all_labels, all_preds, target_names=class_names)  # 분류 보고서
    cm = confusion_matrix(all_labels, all_preds)  # Confusion Matrix
    
    return loss, acc, precision, recall, f1, report, cm, class_names

# Confusion Matrix 시각화 및 저장
def save_confusion_matrix(cm, class_names, filename='confusion_matrix.png'):
    plt.figure(figsize=(8, 6))  # 이미지 크기 설정
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=class_names, yticklabels=class_names)
    plt.xlabel('Predicted')  # X축 레이블
    plt.ylabel('True')  # Y축 레이블
    plt.title('Confusion Matrix')  # 제목
    plt.savefig(filename)  # 파일 저장
    plt.close()  # 메모리 정리

# 평가 결과 저장: 손실, 정확도, 클래스별 메트릭, 분류 보고서
def save_evaluation_results(train_results, val_results, test_results):
    with open('evaluation_results.txt', 'w') as f:
        f.write("=== Quantitative Evaluation Results ===\n\n")
        
        # Train 결과
        f.write("Train Set:\n")
        f.write(f"Loss: {train_results[0]:.4f}, Accuracy: {train_results[1]:.4f}\n")
        f.write("Class-wise Metrics:\n")
        for i, class_name in enumerate(train_results[7]):
            f.write(f"{class_name}:\n")
            f.write(f"  Precision: {train_results[2][i]:.4f}\n")
            f.write(f"  Recall: {train_results[3][i]:.4f}\n")
            f.write(f"  F1-Score: {train_results[4][i]:.4f}\n")
        f.write("\nClassification Report:\n")
        f.write(train_results[5])
        f.write("\n")
        
        # Validation 결과
        f.write("Validation Set:\n")
        f.write(f"Loss: {val_results[0]:.4f}, Accuracy: {val_results[1]:.4f}\n")
        f.write("Class-wise Metrics:\n")
        for i, class_name in enumerate(val_results[7]):
            f.write(f"{class_name}:\n")
            f.write(f"  Precision: {val_results[2][i]:.4f}\n")
            f.write(f"  Recall: {val_results[3][i]:.4f}\n")
            f.write(f"  F1-Score: {val_results[4][i]:.4f}\n")
        f.write("\nClassification Report:\n")
        f.write(val_results[5])
        f.write("\n")
        
        # Test 결과
        f.write("Test Set:\n")
        f.write(f"Loss: {test_results[0]:.4f}, Accuracy: {test_results[1]:.4f}\n")
        f.write("Class-wise Metrics:\n")
        for i, class_name in enumerate(test_results[7]):
            f.write(f"{class_name}:\n")
            f.write(f"  Precision: {test_results[2][i]:.4f}\n")
            f.write(f"  Recall: {test_results[3][i]:.4f}\n")
            f.write(f"  F1-Score: {test_results[4][i]:.4f}\n")
        f.write("\nClassification Report:\n")
        f.write(test_results[5])

def main():
    # 데이터셋 구조 확인
    check_dataset_structure(data_dir)

    # 데이터셋 로드: ImageFolder로 폴더 구조 기반 데이터셋 로드
    full_dataset = datasets.ImageFolder(os.path.join(data_dir), transform=None)
    print("Classes:", full_dataset.classes)  # 클래스 이름 출력
    print("Total images:", len(full_dataset))  # 총 이미지 수 출력

    # 데이터셋 분할: 80% Train (24,000장), 10% Validation (3,000장), 10% Test (3,000장)
    train_size = int(0.8 * len(full_dataset))
    val_size = int(0.1 * len(full_dataset))
    test_size = len(full_dataset) - train_size - val_size
    train_dataset, val_dataset, test_dataset = torch.utils.data.random_split(
        full_dataset, [train_size, val_size, test_size]
    )

    # 커스텀 데이터셋 적용: Train은 증강, Val/Test는 정규화만
    train_dataset = CustomImageDataset(train_dataset, transform=train_transforms)
    val_dataset = CustomImageDataset(val_dataset, transform=val_test_transforms)
    test_dataset = CustomImageDataset(test_dataset, transform=val_test_transforms)

    # DataLoader: 데이터를 배치 단위로 로드
    # - Train: 셔플링으로 데이터 순서 무작위화
    # - Val/Test: 순차적 로드
    # - num_workers=0: CPU 환경에서 멀티프로세싱 비활성화
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    # MobileNetV3-Small 모델 로드: ImageNet 사전 학습 가중치 사용
    model = models.mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)

    # Classifier 레이어 수정: 3개 클래스(enemy_front, enemy_side, enemy_rear)에 맞게 출력 크기 조정
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)

    # Dropout 추가: 과적합 방지를 위해 Classifier에 추가 Dropout 레이어 삽입
    model.classifier = nn.Sequential(
        model.classifier[0],  # Linear 레이어
        model.classifier[1],  # Hardswish 활성화 함수
        nn.Dropout(0.4),      # 추가 Dropout (40% 확률로 뉴런 비활성화)
        model.classifier[2],  # 기존 Dropout
        model.classifier[3]   # 출력 Linear 레이어
    )

    # 모델을 CPU로 이동
    model = model.to(device)

    # 손실 함수: CrossEntropyLoss (다중 클래스 분류에 적합)
    criterion = nn.CrossEntropyLoss()

    # 초기 학습: Classifier만 학습
    print("Starting Initial Training...")
    for param in model.features.parameters():
        param.requires_grad = False  # Backbone(Feature Extractor) 고정
    optimizer = optim.Adam(model.classifier.parameters(), lr=initial_lr, weight_decay=weight_decay)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.1, patience=3)
    model = train_model(model, train_loader, val_loader, criterion, optimizer, scheduler, initial_epochs, phase="initial")

    # Fine-tuning: 전체 모델 학습
    print("Starting Fine-tuning...")
    for param in model.features.parameters():
        param.requires_grad = True  # Backbone 해제
    optimizer = optim.Adam(model.parameters(), lr=finetune_lr, weight_decay=weight_decay)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.1, patience=3)
    model = train_model(model, train_loader, val_loader, criterion, optimizer, scheduler, finetune_epochs, phase="finetune")

    # 최종 모델 저장
    torch.save(model.state_dict(), 'mobilenetv3_small_final.pt')
    print("Training completed and model saved.")

    # 정량적 평가: Train, Validation, Test 데이터셋
    print("Evaluating on Train Dataset...")
    train_results = evaluate_model(model, train_loader, criterion, dataset_name="Train")

    print("Evaluating on Validation Dataset...")
    val_results = evaluate_model(model, val_loader, criterion, dataset_name="Validation")

    print("Evaluating on Test Dataset...")
    test_results = evaluate_model(model, test_loader, criterion, dataset_name="Test")

    # 평가 결과 저장: 텍스트 파일과 Confusion Matrix 이미지
    save_evaluation_results(train_results, val_results, test_results)
    save_confusion_matrix(test_results[6], test_results[7], filename='confusion_matrix.png')
    print("Evaluation results saved to 'evaluation_results.txt' and 'confusion_matrix.png'")

if __name__ == '__main__':
    main()  # 메인 함수 실행 (Windows 멀티프로세싱 오류 방지)