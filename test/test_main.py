import cv2

# ✅ 예시 이미지 불러오기
img = cv2.imread("input.jpg")

# ✅ 바운딩 박스 좌표 리스트 (x, y, w, h)
boxes = [
    (100, 150, 200, 100),  # x, y, width, height
    (300, 200, 120, 180),
]

# ✅ 바운딩 박스 그리기
for (x, y, w, h) in boxes:
    cv2.rectangle(img, (x, y), (x + w, y + h), color=(0, 255, 0), thickness=2)

# ✅ 이미지 출력
cv2.imshow("Bounding Boxes", img)
cv2.waitKey(0)
cv2.destroyAllWindows()