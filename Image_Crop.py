{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 1,
   "id": "05440c36",
   "metadata": {},
   "outputs": [
    {
     "ename": "KeyboardInterrupt",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31m---------------------------------------------------------------------------\u001b[0m",
      "\u001b[1;31mKeyboardInterrupt\u001b[0m                         Traceback (most recent call last)",
      "Cell \u001b[1;32mIn[1], line 20\u001b[0m\n\u001b[0;32m     17\u001b[0m     \u001b[38;5;28;01mcontinue\u001b[39;00m\n\u001b[0;32m     19\u001b[0m img_path \u001b[38;5;241m=\u001b[39m os\u001b[38;5;241m.\u001b[39mpath\u001b[38;5;241m.\u001b[39mjoin(img_dir, img_file)\n\u001b[1;32m---> 20\u001b[0m img \u001b[38;5;241m=\u001b[39m cv2\u001b[38;5;241m.\u001b[39mimread(img_path)\n\u001b[0;32m     21\u001b[0m \u001b[38;5;28;01mif\u001b[39;00m img \u001b[38;5;129;01mis\u001b[39;00m \u001b[38;5;28;01mNone\u001b[39;00m:\n\u001b[0;32m     22\u001b[0m     \u001b[38;5;28;01mcontinue\u001b[39;00m\n",
      "\u001b[1;31mKeyboardInterrupt\u001b[0m: "
     ]
    }
   ],
   "source": [
    "import os\n",
    "import cv2\n",
    "\n",
    "dataset_dir = r\"C:\\Users\\acorn\\OneDrive\\Desktop\\Object-recognition.v18i.yolov8\\train\"\n",
    "output_dir = r\"C:\\Users\\acorn\\OneDrive\\Desktop\\efficientnet_dataset\"\n",
    "class_names = [\"Enemy_Front\", \"Enemy_Rear\", \"Enemy_Side\"]  # Unlabeled 제외\n",
    "img_size = (224, 224)\n",
    "\n",
    "for class_name in class_names:\n",
    "    os.makedirs(os.path.join(output_dir, class_name), exist_ok=True)\n",
    "\n",
    "img_dir = os.path.join(dataset_dir, \"images\")\n",
    "label_dir = os.path.join(dataset_dir, \"labels\")\n",
    "\n",
    "for img_file in os.listdir(img_dir):\n",
    "    if not img_file.lower().endswith((\".jpg\", \".png\")):\n",
    "        continue\n",
    "\n",
    "    img_path = os.path.join(img_dir, img_file)\n",
    "    img = cv2.imread(img_path)\n",
    "    if img is None:\n",
    "        continue\n",
    "    img_height, img_width = img.shape[:2]\n",
    "\n",
    "    label_file = os.path.splitext(img_file)[0] + \".txt\"\n",
    "    label_path = os.path.join(label_dir, label_file)\n",
    "    if not os.path.exists(label_path):\n",
    "        continue\n",
    "\n",
    "    with open(label_path, \"r\", encoding=\"utf-8\") as f:\n",
    "        lines = f.readlines()\n",
    "\n",
    "    if not lines or all(not line.strip() for line in lines):  # Unlabeled 제외\n",
    "        continue\n",
    "\n",
    "    for idx, line in enumerate(lines):\n",
    "        line = line.strip()\n",
    "        if not line:\n",
    "            continue\n",
    "        parts = line.split()\n",
    "        if len(parts) < 5:\n",
    "            print(f\"Invalid label format in {label_path}: {line}\")\n",
    "            continue\n",
    "\n",
    "        class_id = int(parts[0])\n",
    "        x_center, y_center, width, height = map(float, parts[1:])\n",
    "\n",
    "        x_center *= img_width\n",
    "        y_center *= img_height\n",
    "        width *= img_width\n",
    "        height *= img_height\n",
    "\n",
    "        x1 = int(x_center - width / 2)\n",
    "        y1 = int(y_center - height / 2)\n",
    "        x2 = int(x_center + width / 2)\n",
    "        y2 = int(y_center + height / 2)\n",
    "\n",
    "        cropped_img = img[max(y1, 0):min(y2, img_height), max(x1, 0):min(x2, img_width)]\n",
    "        if cropped_img.size == 0:\n",
    "            print(f\"Empty crop in {img_file}, box {idx}\")\n",
    "            continue\n",
    "\n",
    "        cropped_img = cv2.resize(cropped_img, img_size)\n",
    "        class_name = class_names[class_id]\n",
    "        output_path = os.path.join(output_dir, class_name, f\"train_{img_file}_{idx}.jpg\")\n",
    "        cv2.imwrite(output_path, cropped_img)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "95c348fa",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "f8b2cc1a",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "02add2be",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "a0c8b14b",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "531ad3fa",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "aa406c5f",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "dcba5f1f",
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "base",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.12.7"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
