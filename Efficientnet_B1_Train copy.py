import os
import tensorflow as tf

# — GPU 설정: 메모리 growth 허용
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f"GPU detected: {[g.name for g in gpus]}")
    except RuntimeError as e:
        print(e)

from tensorflow.keras.applications import EfficientNetB1
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.utils import class_weight
import matplotlib.pyplot as plt
import numpy as np

# 설정
data_dir       = r"C:\Users\user\Desktop\crop"
img_size       = (240, 240)      # B1용 해상도
batch_size     = 32
num_classes    = 3
epochs         = 25
learning_rate  = 1e-4

# 클래스별 분포 출력
print("Class distribution:")
class_counts = {}
for cls in os.listdir(data_dir):
    cnt = len(os.listdir(os.path.join(data_dir, cls)))
    class_counts[cls] = cnt
    print(f"  {cls}: {cnt}")

# 데이터 증강 + train/val split
datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    shear_range=0.2,
    zoom_range=0.2,
    horizontal_flip=True,
    fill_mode="nearest",
    validation_split=0.2
)
train_gen = datagen.flow_from_directory(
    data_dir, target_size=img_size, batch_size=batch_size,
    class_mode="categorical", subset="training", shuffle=True
)
val_gen = datagen.flow_from_directory(
    data_dir, target_size=img_size, batch_size=batch_size,
    class_mode="categorical", subset="validation", shuffle=False
)
print(f"Found {train_gen.samples} train, {val_gen.samples} val images")

# steps 계산
steps_per_epoch = (train_gen.samples + batch_size - 1) // batch_size
validation_steps = (val_gen.samples + batch_size - 1) // batch_size

# 클래스 가중치
cw = class_weight.compute_class_weight(
    class_weight="balanced",
    classes=np.unique(train_gen.classes),
    y=train_gen.classes
)
class_weight_dict = dict(enumerate(cw))
print("Class weights:", class_weight_dict)

# EfficientNetB1 모델
base = EfficientNetB1(weights="imagenet", include_top=False, input_shape=img_size+(3,))
base.trainable = False

x = GlobalAveragePooling2D()(base.output)
x = Dense(512, activation="relu")(x)
x = Dropout(0.5)(x)
out = Dense(num_classes, activation="softmax")(x)

model = Model(inputs=base.input, outputs=out)
model.compile(
    optimizer=Adam(learning_rate=learning_rate),
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

# 콜백
callbacks = [
    EarlyStopping(patience=5, restore_best_weights=True),
    ReduceLROnPlateau(factor=0.5, patience=3, min_lr=1e-6)
]

# 학습
history = model.fit(
    train_gen,
    epochs=epochs,
    validation_data=val_gen,
    steps_per_epoch=steps_per_epoch,
    validation_steps=validation_steps,
    class_weight=class_weight_dict,
    callbacks=callbacks,
    verbose=1
)

# Fine-tuning: base_model 일부 layer만 trainable
base.trainable = True
for layer in base.layers[:100]:
    layer.trainable = False

model.compile(
    optimizer=Adam(learning_rate=learning_rate/10),
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

history_fine = model.fit(
    train_gen,
    epochs=epochs + 10,
    initial_epoch=history.epoch[-1] + 1,
    validation_data=val_gen,
    steps_per_epoch=steps_per_epoch,
    validation_steps=validation_steps,
    class_weight=class_weight_dict,
    callbacks=callbacks,
    verbose=1
)

# 모델 저장
save_path = r"C:\Users\user\Desktop\efficient\efficientnetb1_model.h5"

model.save(save_path)
print(f"Model saved to {save_path}")

# 학습곡선 그리기
acc      = history.history["accuracy"] + history_fine.history["accuracy"]
val_acc  = history.history["val_accuracy"] + history_fine.history["val_accuracy"]
loss     = history.history["loss"] + history_fine.history["loss"]
val_loss = history.history["val_loss"] + history_fine.history["val_loss"]

plt.figure(figsize=(12,4))
plt.subplot(1,2,1)
plt.plot(acc, label="Train Acc");    plt.plot(val_acc, label="Val Acc")
plt.title("Accuracy"); plt.legend()

plt.subplot(1,2,2)
plt.plot(loss, label="Train Loss"); plt.plot(val_loss, label="Val Loss")
plt.title("Loss"); plt.legend()

plt.savefig(r"C:\Users\user\Desktop\efficient\training_plot_b1.png")
plt.show()
