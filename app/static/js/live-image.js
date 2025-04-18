let lastMtime = 0;

function refreshImage() {
  const img = document.getElementById("live-image");
  const timestamp = new Date().getTime();
  img.src = `/tmp/temp_image.jpg?time=${timestamp}`; // 캐시 방지
}

function pollForNewImage() {
  fetch(`/check_new_frame?last_mtime=${lastMtime}`)
    .then((res) => res.json())
    .then((data) => {
      if (data.updated) {
        refreshImage();
        lastMtime = data.mtime;
      }
      pollForNewImage(); // 계속 반복
    })
    .catch(() => {
      setTimeout(pollForNewImage, 2000); // 에러 시 재시도
    });
}

pollForNewImage(); // 시작
