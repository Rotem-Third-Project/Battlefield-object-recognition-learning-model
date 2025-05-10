async function fetchAndRankObjects() {
  try {
    console.log("📡 priority.js: 객체 가져오는 중...");
    const response = await fetch("/get_detected_objects");
    if (!response.ok) {
      console.error(`Fetch error: ${response.status} ${response.statusText}`);
      return;
    }

    const data = await response.json();
    console.log("📥 priority.js: 받은 데이터:", data);

    const objects = data.objects || [];
    if (!Array.isArray(objects)) {
      console.warn("받은 데이터가 배열이 아님:", objects);
      return;
    }

    if (objects.length === 0) {
      console.warn("객체 배열이 비어 있음");
      if (typeof window.onRankedObjectsReady === "function") {
        window.onRankedObjectsReady([]);
      }
      return;
    }

    // ✅ 서버에서 받은 rank를 사용, threat이 Normal인 객체도 포함
    const ranked = objects
      .filter((obj) => typeof obj.rank === "number") // rank가 숫자인 객체만
      .sort((a, b) => a.rank - b.rank);

    console.log("📊 priority.js: 우선순위 정렬 완료", ranked);

    // ✅ 콜백 호출 (hud.js에서 정의함)
    if (typeof window.onRankedObjectsReady === "function") {
      window.onRankedObjectsReady(ranked);
    } else {
      console.warn("window.onRankedObjectsReady 함수가 정의되지 않음");
    }
  } catch (error) {
    console.error("priority.js fetch 실패:", error);
  }
}

// 주기적으로 호출 (예: 1초마다)
setInterval(fetchAndRankObjects, 1000);