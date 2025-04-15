import os
from PIL import Image
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TimeRemainingColumn,
    TextColumn,
)

console = Console()

# 설정
DATA_DIR = "data"
SAVE_FORMAT = "jpg"
SAVE_PADDING = 5
VALID_EXTS = (".png", ".jpeg", ".jpg", ".bmp", ".webp")

# 하위 폴더만 순회
subfolders = [
    os.path.join(DATA_DIR, name)
    for name in os.listdir(DATA_DIR)
    if os.path.isdir(os.path.join(DATA_DIR, name))
]

with Progress(
    SpinnerColumn(style="bold magenta"),
    TextColumn("[progress.description]{task.description}", justify="right"),
    BarColumn(bar_width=40),
    "[progress.percentage]{task.percentage:>3.0f}%",
    TimeRemainingColumn(),
    console=console,
) as progress:

    for folder in subfolders:
        # 해당 폴더 내 이미지 수집
        image_files = sorted([
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(VALID_EXTS)
        ])

        if not image_files:
            console.log(f"[yellow]⚠️ 이미지 없음: {folder}")
            continue

        task = progress.add_task(f"[green]{os.path.basename(folder)} 변환 중...", total=len(image_files))

        for idx, image_path in enumerate(image_files):
            try:
                img = Image.open(image_path).convert("RGB")
                new_name = str(idx + 1).zfill(SAVE_PADDING) + f".{SAVE_FORMAT}"
                new_path = os.path.join(folder, new_name)

                # 이미지 저장 시 정확한 포맷 지정
                save_format_correct = 'JPEG' if SAVE_FORMAT.lower() in ['jpg', 'jpeg'] else SAVE_FORMAT.upper()
                img.save(new_path, format=save_format_correct)

                # 기존 파일과 새 파일 경로가 다를 때만 기존 파일 삭제
                if os.path.abspath(image_path) != os.path.abspath(new_path):
                    os.remove(image_path)

            except Exception as e:
                console.log(f"[red]❌ {image_path} 변환 실패: {e}")

            finally:
                progress.update(task, advance=1)

console.print("\n✅ [bold green]폴더별 이미지 변환 완료![/bold green]")