# AWS EC2 배포 가이드

## 사전 준비사항
- AWS 계정 (무료 계정 가능)
- 신용카드 (무료 티어 내에서는 과금 없음)

## 배포 과정

### 1단계: EC2 인스턴스 생성
1. AWS 콘솔 로그인 → EC2 서비스 이동
2. **인스턴스 시작** 클릭
3. **설정:**
   - **AMI**: Amazon Linux 2023 AMI (무료 티어 지원)
   - **인스턴스 타입**: t2.micro (무료 티어)
   - **키 페어**: 새로 생성 또는 기존 사용
   - **보안 그룹**: 
     - SSH (22) - 내 IP만
     - HTTP (80) - 모든 곳
     - Custom TCP (3000) - 모든 곳 (Frontend)
     - Custom TCP (8000) - 모든 곳 (Backend API)

### 2단계: 인스턴스 접속
```bash
# Mac/Linux
ssh -i "your-key.pem" ec2-user@YOUR-EC2-PUBLIC-IP

# Windows (PuTTY 사용)
```

### 3단계: 자동 배포 스크립트 실행
```bash
# 배포 스크립트 다운로드 및 실행
curl -O https://raw.githubusercontent.com/danlee-dev/112-miraeasset-clova-ai-challenge/main/aws-deploy.sh
chmod +x aws-deploy.sh
./aws-deploy.sh
```

## 접속 주소
- **Frontend**: http://YOUR-EC2-PUBLIC-IP:3000
- **Backend API**: http://YOUR-EC2-PUBLIC-IP:8000
- **API 문서**: http://YOUR-EC2-PUBLIC-IP:8000/docs

## 💰 비용 정보
- **t2.micro**: 월 750시간 무료 (24시간 x 31일)
- **스토리지**: 30GB EBS 무료
- **데이터 전송**: 월 15GB 무료
- **12개월 무료 사용 가능**

## 🔧 관리 명령어
```bash
# 로그 확인
sudo docker-compose logs

# 서비스 재시작
sudo docker-compose restart

# 서비스 중지
sudo docker-compose down

# 업데이트 후 재배포
git pull
sudo docker-compose up -d --build
```

## ⚠️ 주의사항
- 인스턴스 중지하면 Public IP 변경됨
- Elastic IP 사용시 고정 IP 가능 (무료 티어 1개)
- 12개월 후에는 과금됨 (t2.micro: ~$8.5/월)
