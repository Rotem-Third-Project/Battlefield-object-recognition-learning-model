import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.metrics import confusion_matrix, classification_report, roc_curve, auc, precision_recall_curve
import matplotlib.pyplot as plt
import seaborn as sns
import time
import os
from pathlib import Path

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = Path(r"C:\Users\acorn\OneDrive\Desktop\MyWork\Battlefield-object-recognition-learning-model\app\models\Efficientnet_weights\30000Efficient_weight.h5")
DATA_DIR = r"C:\Users\acorn\OneDrive\Desktop\real_efficientnet_dataset"  
IMG_SIZE = (224, 224)
BATCH_SIZE = 32

# 모델 로드
model = tf.keras.models.load_model(MODEL_PATH)
print("EfficientNetB0 model loaded successfully")

# 검증 데이터 로드
val_datagen = ImageDataGenerator(
    rescale=1./255,
    validation_split=0.3
)

validation_generator = val_datagen.flow_from_directory(
    DATA_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="validation",
    shuffle=False
)

print(f"Found {validation_generator.samples} validation images")

# 클래스 이름 및 인덱스 매핑
class_names = ["Enemy_Front", "Enemy_Rear", "Enemy_Side"]
class_indices = validation_generator.class_indices
print(f"Class indices: {class_indices}")

# 모델 평가 (정확도 및 손실)
val_steps = validation_generator.samples // BATCH_SIZE
if validation_generator.samples % BATCH_SIZE != 0:
    val_steps += 1

validation_generator.reset()
loss, accuracy = model.evaluate(validation_generator, steps=val_steps, verbose=1)
print(f"Validation Loss: {loss:.4f}")
print(f"Validation Accuracy: {accuracy:.4f}")

# 예측 수행
validation_generator.reset()
start_time = time.time()
y_pred = model.predict(validation_generator, steps=val_steps, verbose=1)
y_pred_classes = np.argmax(y_pred, axis=1)
y_true = validation_generator.classes
inference_time = time.time() - start_time
print(f"Inference Time: {inference_time:.2f} seconds for {validation_generator.samples} images")
print(f"Average Inference Time per Image: {inference_time / validation_generator.samples:.4f} seconds")

# 혼동 행렬
cm = confusion_matrix(y_true, y_pred_classes)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=class_names, yticklabels=class_names)
plt.title("Confusion Matrix")
plt.xlabel("Predicted")
plt.ylabel("True")
plt.savefig(BASE_DIR / "confusion_matrix.png")
plt.show()

# 분류 보고서 (정밀도, 재현율, F1 점수)
print("\nClassification Report:")
print(classification_report(y_true, y_pred_classes, target_names=class_names))

# ROC-AUC (One-vs-Rest 방식)
plt.figure(figsize=(10, 8))
for i, class_name in enumerate(class_names):
    fpr, tpr, _ = roc_curve(y_true == i, y_pred[:, i])
    roc_auc = auc(fpr, tpr)
    plt.plot(fpr, tpr, label=f"{class_name} (AUC = {roc_auc:.2f})")
plt.plot([0, 1], [0, 1], 'k--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve (One-vs-Rest)")
plt.legend(loc="lower right")
plt.savefig(BASE_DIR / "roc_curve.png")
plt.show()

# Precision-Recall Curve (One-vs-Rest 방식)
plt.figure(figsize=(10, 8))
for i, class_name in enumerate(class_names):
    precision, recall, _ = precision_recall_curve(y_true == i, y_pred[:, i])
    pr_auc = auc(recall, precision)
    plt.plot(recall, precision, label=f"{class_name} (PR-AUC = {pr_auc:.2f})")
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel("Recall")
plt.ylabel("Precision")
plt.title("Precision-Recall Curve (One-vs-Rest)")
plt.legend(loc="lower left")
plt.savefig(BASE_DIR / "pr_curve.png")
plt.show()