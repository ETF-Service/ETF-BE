"""
알림 전송 서비스
알림 전송 서비스
"""

import logging
from typing import Dict, List

from models.user import User
from crud.notification import create_notification

from config.notification_config import get_notification_titles, get_notification_types
from schemas.notification import NotificationCreate
from services.email_service import email_service
from database import SessionLocal

logger = logging.getLogger(__name__)

class NotificationService:
    """알림 전송 서비스"""

    def __init__(self):
        self.notification_titles = get_notification_titles()
        self.notification_types = get_notification_types()

    async def send_bulk_notifications(self, notifications: List[Dict]) -> Dict[str, int]:
        """
        대량 알림 전송 (통합 포트폴리오 분석 전용으로 단순화)
        
        Args:
            notifications: 알림 데이터 목록
        
        Returns:
            전송 결과 통계
        """
        success_count = 0
        failure_count = 0

        for notification_data in notifications:
            db = SessionLocal()  # 각 알림마다 새로운 DB 세션을 생성
            try:
                user_id = notification_data.get('user_id')
                user = db.query(User).filter(User.id == user_id).first()

                if not user or not user.settings or not user.settings.notification_enabled:
                    logger.warning(f"⚠️ 사용자 {user_id}를 찾을 수 없거나 알림이 비활성화되어 있습니다.")
                    failure_count += 1
                    continue

                # 이메일 전송 로직
                etf_data_list = notification_data['etf_data_list']
                etf_list_for_email = [f"• {d['etf'].symbol} ({d['etf'].name}): {d['etf_setting'].amount:,g}만 원" for d in etf_data_list]
                total_amount = sum(d['etf_setting'].amount for d in etf_data_list)
                
                email_data = {
                    'etf_list': etf_list_for_email,
                    'total_amount': total_amount,
                    'etf_count': len(etf_data_list),
                    'parsed_analysis': notification_data['parsed_analysis']
                }

                email_sent = email_service.send_portfolio_analysis_notification(
                    user.email, user.name, email_data
                )
                
                if email_sent:
                    logger.info(f"📧 {user.name}님의 포트폴리오 분석 이메일 알림 전송 성공")
                else:
                    logger.warning(f"⚠️ {user.name}님의 포트폴리오 분석 이메일 알림 전송 실패")

                # 데이터베이스에 알림 저장 로직
                title = f"📊 ETF 포트폴리오 투자 분석 알림 ({len(etf_data_list)}개 종목)"
                content = notification_data['parsed_analysis'].get('summary', '분석 결과를 확인해주세요.')
                sent_via = "email" if email_sent else "app"

                db_notification_data = NotificationCreate(
                    user_id=user.id,
                    title=title,
                    content=content,
                    type=self.notification_types.get('PORTFOLIO_ANALYSIS', 'portfolio_analysis'),
                    sent_via=sent_via
                )
                create_notification(db, db_notification_data)

                success_count += 1

            except Exception as e:
                logger.error(f"❌ 대량 알림 전송 중 오류: {e}")
                failure_count += 1
            finally:
                db.close()  # 작업이 끝나면 반드시 세션을 닫아줌

        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "total_count": len(notifications)
        }

# 전역 알림 서비스 인스턴스
notification_service = NotificationService() 