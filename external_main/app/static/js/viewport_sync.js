function sendWindowSizeToServer() {
  const width = window.innerWidth;
  const height = window.innerHeight;

  fetch("/set_roi", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      width: width,
      height: height,
    }),
  });
}

// 페이지 로드시 전송
sendWindowSizeToServer();

// 창 크기 바뀔 때마다 전송
window.addEventListener("resize", sendWindowSizeToServer);
