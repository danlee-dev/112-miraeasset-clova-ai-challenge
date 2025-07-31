#!/bin/bash
# AWS EC2 배포 스크립트

echo "🚀 MiraeAsset AI Challenge AWS 배포 시작..."

# 1. 시스템 업데이트
sudo yum update -y

# 2. Docker 설치
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# 3. Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 4. Git 설치 및 프로젝트 클론
sudo yum install -y git
git clone https://github.com/danlee-dev/112-miraeasset-clova-ai-challenge.git
cd 112-miraeasset-clova-ai-challenge

# 5. 환경변수 설정
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo "REACT_APP_API_URL=http://${PUBLIC_IP}:8000" > Frontend/.env

# 6. AWS용 Docker Compose로 실행
sudo docker-compose -f docker-compose.aws.yml up -d --build

echo "✅ 배포 완료!"
echo "🌐 Frontend: http://${PUBLIC_IP}:3000"
echo "🔧 Backend API: http://${PUBLIC_IP}:8000"
echo "📖 API Docs: http://${PUBLIC_IP}:8000/docs"
