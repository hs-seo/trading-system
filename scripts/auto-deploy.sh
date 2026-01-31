#!/bin/bash
# 시놀로지 자동 배포 스크립트
# GitHub에서 최신 코드를 가져와서 Docker 컨테이너를 재빌드합니다.

PROJECT_DIR="/volume1/docker/trading-system"
LOG_FILE="/volume1/docker/trading-system/deploy.log"

echo "$(date): 배포 시작" >> $LOG_FILE

cd $PROJECT_DIR

# GitHub에서 최신 코드 가져오기
git fetch origin main

# 로컬과 원격 비교
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$(date): 새 커밋 발견, 업데이트 중..." >> $LOG_FILE

    # 최신 코드 적용
    git reset --hard origin/main

    # Docker 컨테이너 재빌드 & 재시작
    docker-compose down
    docker-compose up -d --build

    echo "$(date): 배포 완료 - $REMOTE" >> $LOG_FILE
else
    echo "$(date): 변경사항 없음" >> $LOG_FILE
fi
