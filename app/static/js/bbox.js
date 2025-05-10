// bbox.js

function renderBoundingBoxes(objects, roiWidth, roiHeight, videoElement) {
  const videoWidth = videoElement.clientWidth;
  const videoHeight = videoElement.clientHeight;

  const container = videoElement.parentElement;

  // 기존 bbox 삭제
  document.querySelectorAll(".bbox").forEach((e) => e.remove());

  if (!objects || objects.length === 0) return;

  const scaleX = videoWidth / roiWidth;
  const scaleY = videoHeight / roiHeight;

  objects.forEach((obj) => {
    const [x1, y1, x2, y2] = obj.bbox;
    const className = obj.className;
    const threat = obj.threat;

    // 스케일 변환
    const scaledX1 = x1 * scaleX;
    const scaledY1 = y1 * scaleY;
    const scaledWidth = (x2 - x1) * scaleX;
    const scaledHeight = (y2 - y1) * scaleY;

    // 위협 수준별 색상
    const box = document.createElement("div");
    box.classList.add("bbox");
    box.style.left = `${scaledX1}px`;
    box.style.top = `${scaledY1}px`;
    box.style.width = `${scaledWidth}px`;
    box.style.height = `${scaledHeight}px`;

    const classMap = {
      "LEVEL 3": "threat-level-3",
      "LEVEL 2": "threat-level-2",
      "LEVEL 1": "threat-level-1",
      None: "threat-none",
    };
    box.classList.add(classMap[threat] || "threat-none");

    // 라벨 텍스트
    box.innerText = `${className}`;

    // bbox 추가
    container.appendChild(box);
  });
}

fetch("/get_detected_objects")
  .then((res) => res.json())
  .then((data) => {
    const roiWidth = data.roi.width;
    const roiHeight = data.roi.height;
    const videoElement = document.getElementById("live-image");

    renderBoundingBoxes(data.objects, roiWidth, roiHeight, videoElement);
  });
