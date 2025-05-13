# 베이스 이미지
FROM python:3.11-slim

# 필수 패키지 설치 (ffmpeg 포함)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean

# 작업 디렉토리 설정
WORKDIR /app

# 의존 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 파일 복사
COPY . .

# 포맷된 실행 명령
CMD ["python", "code.py"]
