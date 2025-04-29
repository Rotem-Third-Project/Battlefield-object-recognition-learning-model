import os

# 이미지가 있는 폴더 경로
folder_path = "C:\\Users\\acorn\\Desktop\\image\\you"

# 확장자 설정
extension = ".jpg"

# 파일 가져오기
files = sorted([f for f in os.listdir(folder_path) if f.endswith(extension)])

# 파일 이름 바꾸기
for index, filename in enumerate(files, start=48951):
    new_name = f"{index}{extension}"  # 숫자만!
    old_path = os.path.join(folder_path, filename)
    new_path = os.path.join(folder_path, new_name)
    os.rename(old_path, new_path)

print("이름 변경 완료!")
