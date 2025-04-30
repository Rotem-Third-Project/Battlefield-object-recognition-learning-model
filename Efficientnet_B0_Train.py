import os
import tensorflow as tf
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import matplotlib.pyplot as plt
from sklearn.utils import class_weight
import numpy as np

# 설정
data_dir = r"C:\Users\acorn\OneDrive\Desktop\real_efficientnet_dataset"
img_size = (224, 224)
batch_size = 32
num_classes = 3
epochs = 25
learning_rate = 1e-3  # 학습률 증가

# 클래스별 이미지 수 확인
print("Class distribution:")
class_counts = {}
for cls in os.listdir(data_dir):
    count = len(os.listdir(os.path.join(data_dir, cls)))
    class_counts[cls] = count
    print(f"{cls}: {count} images")

# 데이터 증강 및 로드
train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=10,  # 증강 완화
    width_shift_range=0.1,
    height_shift_range=0.1,
    shear_range=0.1,
    zoom_range=0.1,
    horizontal_flip=True,
    fill_mode="nearest",
    validation_split=0.2
)

val_datagen = ImageDataGenerator(
    rescale=1./255,
    validation_split=0.2
)

train_generator = train_datagen.flow_from_directory(
    data_dir,
    target_size=img_size,
    batch_size=batch_size,
    class_mode="categorical",
    subset="training",
    shuffle=True
)

validation_generator = val_datagen.flow_from_directory(
    data_dir,
    target_size=img_size,
    batch_size=batch_size,
    class_mode="categorical",
    subset="validation",
    shuffle=False
)

print(f"Found {train_generator.samples} training images and {validation_generator.samples} validation images")

# 데이터 확인
print("Class indices:", train_generator.class_indices)
batch = next(train_generator)
images, labels = batch
print("Image value range:", images.min(), images.max())
for i in range(5):
    plt.imshow(images[i])
    plt.title(f"Label: {labels[i]}")
    plt.show()

# steps_per_epoch 및 validation_steps 조정
steps_per_epoch = train_generator.samples // batch_size
if train_generator.samples % batch_size != 0:
    steps_per_epoch += 1
validation_steps = validation_generator.samples // batch_size
if validation_generator.samples % batch_size != 0:
    validation_steps += 1

# 클래스 가중치 계산
class_weights = class_weight.compute_class_weight(
    class_weight="balanced",
    classes=np.unique(train_generator.classes),
    y=train_generator.classes
)
class_weight_dict = dict(enumerate(class_weights))
print(f"Class weights: {class_weight_dict}")

# EfficientNetB0 모델 빌드
base_model = EfficientNetB0(weights="imagenet", include_top=False, input_shape=img_size + (3,))
base_model.trainable = True
for layer in base_model.layers[:100]:
    layer.trainable = False

x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(512, activation="relu")(x)
x = Dropout(0.3)(x)  # Dropout 비율 감소
outputs = Dense(num_classes, activation="softmax")(x)

model = Model(inputs=base_model.input, outputs=outputs)

# 모델 컴파일
model.compile(optimizer=Adam(learning_rate=learning_rate),
              loss="categorical_crossentropy",
              metrics=["accuracy"])

# 콜백 설정
callbacks = [
    EarlyStopping(patience=5, restore_best_weights=True),
    ReduceLROnPlateau(factor=0.5, patience=3, min_lr=1e-6)
]

# 학습
train_generator.reset()
validation_generator.reset()
history = model.fit(
    train_generator,
    epochs=epochs,
    validation_data=validation_generator,
    steps_per_epoch=steps_per_epoch,
    validation_steps=validation_steps,
    callbacks=callbacks,
    class_weight=class_weight_dict,
    verbose=1
)

# Fine-tuning
base_model.trainable = True
for layer in base_model.layers[:50]:  # 더 적은 레이어 고정
    layer.trainable = False

model.compile(optimizer=Adam(learning_rate=learning_rate / 10),
              loss="categorical_crossentropy",
              metrics=["accuracy"])

fine_tune_epochs = 10
train_generator.reset()
validation_generator.reset()
history_fine = model.fit(
    train_generator,
    epochs=epochs + fine_tune_epochs,
    initial_epoch=history.epoch[-1] + 1,
    validation_data=validation_generator,
    steps_per_epoch=steps_per_epoch,
    validation_steps=validation_steps,
    callbacks=callbacks,
    class_weight=class_weight_dict,
    verbose=1
)

# 모델 저장
model.save(r"C:\Users\acorn\OneDrive\Desktop\real_efficientnetb0_model.h5")
print("Model saved to real_efficientnetb0_model.h5")

# 학습 결과 시각화
acc = history.history["accuracy"] + history_fine.history["accuracy"]
val_acc = history.history["val_accuracy"] + history_fine.history["val_accuracy"]
loss = history.history["loss"] + history_fine.history["loss"]
val_loss = history.history["val_loss"] + history_fine.history["val_loss"]

plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1)
plt.plot(acc, label="Training Accuracy")
plt.plot(val_acc, label="Validation Accuracy")
plt.title("Training and Validation Accuracy")
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(loss, label="Training Loss")
plt.plot(val_loss, label="Validation Loss")
plt.title("Training and Validation Loss")
plt.legend()

plt.savefig(r"C:\Users\acorn\OneDrive\Desktop\real_training_plot.png")
plt.show()