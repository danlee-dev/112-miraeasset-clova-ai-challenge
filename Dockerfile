# Railway 배포용 백엔드 Dockerfile (Pro Plan용)
FROM python:3.10-slim

WORKDIR /app

# Playwright용 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libnss3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 백엔드 의존성 파일 복사 및 설치
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 브라우저 설치
RUN playwright install chromium
RUN playwright install-deps chromium

# 백엔드 코드 복사
COPY backend/ .

# 데이터 디렉토리 생성
RUN mkdir -p /app/data

# 환경변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# 포트 노출
EXPOSE 8000

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000
