# Railway 배포용 백엔드 Dockerfile
FROM python:3.10-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 백엔드 의존성 파일 복사 및 설치
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 설치 (백그라운드 크롤링용)
RUN playwright install chromium
RUN playwright install-deps chromium

# 백엔드 코드 복사
COPY backend/ .

# 데이터 디렉토리 생성
RUN mkdir -p /app/data

# 포트 노출
EXPOSE $PORT

# 환경변수 설정
ENV PYTHONPATH=/app
ENV PORT=8001

# 애플리케이션 실행
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
