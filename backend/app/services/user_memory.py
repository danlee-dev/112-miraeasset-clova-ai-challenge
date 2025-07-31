import sqlite3
import json
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class UserMemoryService:
    def __init__(self, db_path: str = "data/user_memory.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """사용자 메모리 데이터베이스 초기화"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 기존 테이블 삭제 (스키마 변경을 위해)
                cursor.execute('DROP TABLE IF EXISTS user_conversations')
                cursor.execute('DROP TABLE IF EXISTS user_preferences')
                cursor.execute('DROP TABLE IF EXISTS user_profiles')
                
                # 사용자 기본 정보 테이블
                cursor.execute('''
                    CREATE TABLE user_profiles (
                        user_id TEXT PRIMARY KEY,
                        user_name TEXT NOT NULL,
                        investment_experience TEXT,
                        risk_tolerance TEXT,
                        preferred_sectors TEXT,
                        portfolio_count INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 사용자 대화 기록 테이블
                cursor.execute('''
                    CREATE TABLE user_conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        message TEXT,
                        response TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                    )
                ''')
                
                # 사용자 선호도 학습 테이블
                cursor.execute('''
                    CREATE TABLE user_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        preference_type TEXT,
                        preference_value TEXT,
                        confidence_score REAL DEFAULT 0.5,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                    )
                ''')
                
                conn.commit()
                logger.info("사용자 메모리 데이터베이스 초기화 완료")
                
        except Exception as e:
            logger.error(f"데이터베이스 초기화 오류: {e}")
    
    def save_user_profile(self, user_id: str, user_name: str, user_context: Dict[str, Any]):
        """사용자 프로필 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 기존 사용자 확인
                cursor.execute("SELECT user_id FROM user_profiles WHERE user_id = ?", (user_id,))
                existing_user = cursor.fetchone()
                
                preferred_sectors_json = json.dumps(user_context.get('preferred_sectors', []))
                
                if existing_user:
                    # 기존 사용자 업데이트
                    cursor.execute('''
                        UPDATE user_profiles 
                        SET user_name = ?, investment_experience = ?, risk_tolerance = ?, 
                            preferred_sectors = ?, portfolio_count = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    ''', (
                        user_name,
                        user_context.get('investment_experience'),
                        user_context.get('risk_tolerance'),
                        preferred_sectors_json,
                        user_context.get('portfolio_count', 0),
                        user_id
                    ))
                    logger.info(f"사용자 프로필 업데이트: {user_name}")
                else:
                    # 새 사용자 생성
                    cursor.execute('''
                        INSERT INTO user_profiles 
                        (user_id, user_name, investment_experience, risk_tolerance, preferred_sectors, portfolio_count)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        user_name,
                        user_context.get('investment_experience'),
                        user_context.get('risk_tolerance'),
                        preferred_sectors_json,
                        user_context.get('portfolio_count', 0)
                    ))
                    logger.info(f"새 사용자 프로필 생성: {user_name}")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"사용자 프로필 저장 오류: {e}")
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 프로필 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, user_name, investment_experience, risk_tolerance, 
                           preferred_sectors, portfolio_count, created_at, updated_at
                    FROM user_profiles WHERE user_id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'user_id': row[0],
                        'user_name': row[1],
                        'investment_experience': row[2],
                        'risk_tolerance': row[3],
                        'preferred_sectors': json.loads(row[4]) if row[4] else [],
                        'portfolio_count': row[5],
                        'created_at': row[6],
                        'updated_at': row[7]
                    }
                return None
                
        except Exception as e:
            logger.error(f"사용자 프로필 조회 오류: {e}")
            return None
    
    def save_conversation(self, user_id: str, message: str, response: str):
        """대화 기록 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_conversations (user_id, message, response)
                    VALUES (?, ?, ?)
                ''', (user_id, message, response))
                conn.commit()
                
        except Exception as e:
            logger.error(f"대화 기록 저장 오류: {e}")
    
    def get_recent_conversations(self, user_id: str, limit: int = 5) -> list:
        """최근 대화 기록 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT message, response, timestamp 
                    FROM user_conversations 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (user_id, limit))
                
                rows = cursor.fetchall()
                return [{'message': row[0], 'response': row[1], 'timestamp': row[2]} for row in rows]
                
        except Exception as e:
            logger.error(f"대화 기록 조회 오류: {e}")
            return []
    
    def update_user_preference(self, user_id: str, preference_type: str, preference_value: str, confidence: float = 0.7):
        """사용자 선호도 업데이트"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 기존 선호도 확인
                cursor.execute('''
                    SELECT id, confidence_score FROM user_preferences 
                    WHERE user_id = ? AND preference_type = ? AND preference_value = ?
                ''', (user_id, preference_type, preference_value))
                
                existing = cursor.fetchone()
                
                if existing:
                    # 기존 선호도 업데이트 (신뢰도 증가)
                    new_confidence = min(1.0, existing[1] + confidence * 0.1)
                    cursor.execute('''
                        UPDATE user_preferences 
                        SET confidence_score = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (new_confidence, existing[0]))
                else:
                    # 새 선호도 추가
                    cursor.execute('''
                        INSERT INTO user_preferences (user_id, preference_type, preference_value, confidence_score)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, preference_type, preference_value, confidence))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"사용자 선호도 업데이트 오류: {e}")
    
    def get_user_context_for_chat(self, user_id: str) -> str:
        """채팅용 사용자 컨텍스트 생성"""
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return "사용자 정보가 없습니다."
            
            context = f"""
사용자 정보:
- 이름: {profile['user_name']}
- 투자 경험: {profile['investment_experience']}
- 위험 성향: {profile['risk_tolerance']}
- 선호 섹터: {', '.join(profile['preferred_sectors'])}
- 포트폴리오 수: {profile['portfolio_count']}개
"""
            
            # 최근 대화 기록 추가
            recent_conversations = self.get_recent_conversations(user_id, 3)
            if recent_conversations:
                context += "\n최근 대화 내용:\n"
                for conv in reversed(recent_conversations):  # 시간순 정렬
                    context += f"- 질문: {conv['message'][:100]}...\n"
            
            return context
            
        except Exception as e:
            logger.error(f"사용자 컨텍스트 생성 오류: {e}")
            return "사용자 정보 로드 중 오류가 발생했습니다."

# 전역 인스턴스
user_memory_service = UserMemoryService()
