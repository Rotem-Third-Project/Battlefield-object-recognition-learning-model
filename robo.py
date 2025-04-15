import os
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"  # ✅ OpenCV 경고 안 보이게

from roboflow import Roboflow
from alive_progress import alive_bar

# ✅ Roboflow 설정
rf = Roboflow(api_key="OA3RekQNjJanlw2Lgqos")
workspace_id = "ai-hxvps"
project_id = "object-recognition-64nqg"
project = rf.workspace(workspace_id).project(project_id)

# ✅ 업로드 대상 디렉토리
upload_dir = r"C:\새 폴더 (2)"
valid_exts = [".jpg", ".jpeg", ".png"]

# ✅ 이미지 경로 수집 (하위 폴더 포함)
image_paths = []
for root, _, files in os.walk(upload_dir):
    for file in files:
        if any(file.lower().endswith(ext) for ext in valid_exts):
            image_paths.append(os.path.join(root, file))

# ✅ 업로드 및 프로그레스바 진행
success_list = []
fail_list = []

with alive_bar(len(image_paths), title="📤 전체 이미지 업로드 진행 중") as bar:
    for path in image_paths:
        try:
            project.upload(path)
            success_list.append(path)
        except Exception as e:
            fail_list.append((path, str(e)))
            bar.text(f"❌ 실패: {os.path.basename(path)}")  # 실패만 출력
        bar()

# ✅ 결과 요약
print("\n📦 업로드 완료 요약")
print(f"  ✅ 성공: {len(success_list)}장")
print(f"  ❌ 실패: {len(fail_list)}장")

if fail_list:
    print("\n🔴 실패한 파일 목록:")
    for f, err in fail_list:
        print(f"- {f} ({err})")
