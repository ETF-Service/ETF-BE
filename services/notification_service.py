"""
알림 전송 서비스
알림 전송 서비스
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from models.notification import Notification
from models.user import User, InvestmentSettings
from models.etf import InvestmentETFSettings, ETF
from crud.notification import create_notification	

from config.notification_config import (
    get_notification_titles,
    get_notification_types
)
from schemas.notification import NotificationCreate
from services.email_service import email_service

logger = logging.getLogger(__name__)

class NotificationService:
    """알림 전송 서비스"""
    
    def __init__(self):
        self.notification_titles = get_notification_titles()
        self.notification_types = get_notification_types()
    
    async def send_ai_analysis_notification(
        self,
        db: Session,
        user: User,
        etf: ETF,
        analysis_result: Dict,
        should_notify: bool
    ) -> bool:
        """
        AI 분석 결과에 따른 알림 전송
        
        Args:
            db: 데이터베이스 세션
            user: 사용자 정보
            etf: ETF 정보
            analysis_result: AI 분석 결과
            should_notify: 알림 전송 여부
        
        Returns:
            알림 전송 성공 여부
        """
        try:
            if not should_notify:
                logger.info(f"📊 {user.name}님의 {etf.symbol} ETF - 알림 전송 불필요")
                return True
            
            # 알림 내용 구성
            title = self.notification_titles.get('ai_analysis', '🤖 AI 투자 분석 알림')
            content = self._format_ai_analysis_content(user, etf, analysis_result)
            
            # 사용자 알림 설정 확인
            user_settings = user.settings
            if not user_settings or not user_settings.notification_enabled:
                logger.info(f"📊 {user.name}님의 알림이 비활성화되어 있습니다")
                return True
            
            # 이메일 알림 전송 (알림 채널에 email이 포함된 경우)
            email_sent = False
            email_data = {
                'etf_symbol': etf.symbol,
                'analysis_summary': analysis_result.get('summary', ''),
                'recommendation': analysis_result.get('recommendation', ''),
                'confidence_score': analysis_result.get('confidence_score', 0),
                'current_weight': analysis_result.get('current_weight', 0),
                'recommended_weight': analysis_result.get('recommended_weight', 0),
                'adjustment_amount': analysis_result.get('adjustment_amount', 0),
                'detailed_analysis': analysis_result.get('detailed_analysis', '')
            }
            
            email_sent = email_service.send_ai_analysis_notification(
                user.email, user.name, email_data
            )
            
            if email_sent:
                logger.info(f"📧 {user.name}님의 {etf.symbol} ETF 이메일 알림 전송 성공")
            else:
                logger.warning(f"⚠️ {user.name}님의 {etf.symbol} ETF 이메일 알림 전송 실패")
            
            # 데이터베이스에 알림 저장
            sent_via = "email" if email_sent else "app"
            notification_data = NotificationCreate(
                user_id=user.id,
                title=title,
                content=content,
                type=self.notification_types.get('AI_ANALYSIS', 'ai_analysis'),
                sent_via=sent_via
            )
            
            db_notification = create_notification(db, notification_data)
            
            if not db_notification:
                logger.error(f"❌ {user.name}님의 {etf.symbol} ETF 알림 저장 실패")
                return False
            
            logger.info(f"📤 {user.name}님의 {etf.symbol} ETF 알림 생성 완료 (전송: {sent_via})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ {user.name}님의 {etf.symbol} ETF 알림 전송 중 오류: {e}")
            return False
    
    async def send_investment_reminder(
        self,
        db: Session,
        user: User,
        etf_settings: List[InvestmentETFSettings]
    ) -> bool:
        """
        투자일 알림 전송
        
        Args:
            db: 데이터베이스 세션
            user: 사용자 정보
            etf_settings: 투자할 ETF 설정 목록
        
        Returns:
            알림 전송 성공 여부
        """
        try:
            if not etf_settings:
                logger.info(f"📅 {user.name}님 - 오늘 투자할 ETF가 없습니다")
                return True
            
            # 사용자 알림 설정 확인
            user_settings = user.settings
            if not user_settings or not user_settings.notification_enabled:
                logger.info(f"📅 {user.name}님의 알림이 비활성화되어 있습니다")
                return True
            
            # 이메일 알림 전송 (알림 채널에 email이 포함된 경우)
            email_sent = False
            # ETF 목록 및 총 금액 계산
            etf_list = []
            total_amount = 0
            for etf_setting in etf_settings:
                etf_list.append({
                    'name': etf_setting.etf.name if etf_setting.etf else etf_setting.symbol,
                    'amount': etf_setting.amount
                })
                total_amount += etf_setting.amount
            
            email_data = {
                'etf_list': etf_list,
                'total_amount': total_amount
            }
            
            email_sent = email_service.send_investment_reminder(
                user.email, user.name, email_data
            )
            
            if email_sent:
                logger.info(f"📧 {user.name}님의 투자일 이메일 알림 전송 성공")
            else:
                logger.warning(f"⚠️ {user.name}님의 투자일 이메일 알림 전송 실패")
            
            # 알림 내용 구성
            title = self.notification_titles.get('investment_reminder', '📅 투자일 알림')
            content = self._format_investment_reminder_content(user, etf_settings)
            
            # 데이터베이스에 알림 저장
            sent_via = "email" if email_sent else "app"
            notification_data = NotificationCreate(
                user_id=user.id,
                title=title,
                content=content,
                type=self.notification_types.get('INVESTMENT_REMINDER', 'investment_reminder'),
                sent_via=sent_via
            )
            
            db_notification = create_notification(db, notification_data)
            
            if not db_notification:
                logger.error(f"❌ {user.name}님의 투자일 알림 저장 실패")
                return False
            
            logger.info(f"📤 {user.name}님의 투자일 알림 생성 완료 (전송: {sent_via})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ {user.name}님의 투자일 알림 전송 중 오류: {e}")
            return False
    
    async def send_system_notification(
        self,
        db: Session,
        user: User,
        title: str,
        content: str,
        notification_type: str = "system"
    ) -> bool:
        """
        시스템 알림 전송
        
        Args:
            db: 데이터베이스 세션
            user: 사용자 정보
            title: 알림 제목
            content: 알림 내용
            notification_type: 알림 타입
        
        Returns:
            알림 전송 성공 여부
        """
        try:
            # 사용자 알림 설정 확인
            user_settings = user.settings
            if not user_settings or not user_settings.notification_enabled:
                logger.info(f"🔔 {user.name}님의 알림이 비활성화되어 있습니다")
                return True
            
            # 이메일 알림 전송 (알림 채널에 email이 포함된 경우)
            email_sent = False
            email_sent = email_service.send_system_notification(
                user.email, user.name, title, content
            )
            
            if email_sent:
                logger.info(f"📧 {user.name}님의 시스템 이메일 알림 전송 성공")
            else:
                logger.warning(f"⚠️ {user.name}님의 시스템 이메일 알림 전송 실패")
            
            # 데이터베이스에 알림 저장
            sent_via = "email" if email_sent else "app"
            notification_data = NotificationCreate(
                user_id=user.id,
                title=title,
                content=content,
                type=notification_type,
                sent_via=sent_via
            )
            
            db_notification = create_notification(db, notification_data)
            
            if not db_notification:
                logger.error(f"❌ {user.name}님의 시스템 알림 저장 실패")
                return False
            
            logger.info(f"📤 {user.name}님의 시스템 알림 생성 완료 (전송: {sent_via})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ {user.name}님의 시스템 알림 전송 중 오류: {e}")
            return False
    
    def _format_ai_analysis_content(self, user: User, etf: ETF, analysis_result: Dict) -> str:
        """AI 분석 알림 내용 포맷팅"""
        recommendation = analysis_result.get('recommendation', '분석 결과가 없습니다.')
        confidence_score = analysis_result.get('confidence_score', 0.0)
        
        content = f"""
🤖 {etf.symbol} ETF AI 분석 결과

📊 분석 요약:
{recommendation}

🎯 신뢰도: {confidence_score:.1%}

💡 투자 가중치 조정이 필요할 수 있습니다. 
앱에서 자세한 분석 내용을 확인해보세요.
        """.strip()
        
        return content
    
    def _format_investment_reminder_content(self, user: User, etf_settings: List[InvestmentETFSettings]) -> str:
        """투자일 알림 내용 포맷팅"""
        etf_list = []
        total_amount = 0
        
        for setting in etf_settings:
            etf_list.append(f"• {setting.etf.symbol}: {setting.amount:,}원")
            total_amount += setting.amount
        
        content = f"""
📅 오늘은 투자일입니다!

💰 투자할 ETF 목록:
{chr(10).join(etf_list)}

💵 총 투자 금액: {total_amount:,}원

⏰ 투자 시간을 잊지 마세요!
        """.strip()
        
        return content
    
    async def send_integrated_investment_notification(
        self,
        db: Session,
        user: User,
        user_setting,
        etf_data_list: List[Dict],
        analysis_result: str,
        recommendation: str,
        confidence_score: float
    ) -> bool:
        """
        통합 투자 알림 전송 (포트폴리오 분석 결과)
        
        Args:
            db: 데이터베이스 세션
            user: 사용자 정보
            user_setting: 사용자 설정
            etf_data_list: ETF 데이터 목록
            analysis_result: AI 분석 결과
            recommendation: 추천사항
            confidence_score: 신뢰도 점수
        
        Returns:
            알림 전송 성공 여부
        """
        try:
            # ETF 목록 생성
            etf_list = []
            total_amount = 0
            for etf_data in etf_data_list:
                etf_setting = etf_data['etf_setting']
                etf = etf_data['etf']
                etf_list.append(f"• {etf.symbol} ({etf.name}): {etf_setting.amount:,}원")
                total_amount += etf_setting.amount
            
            # 포트폴리오 분석 결과를 이메일로 전송
            if etf_data_list:
                # 사용자 알림 설정 확인
                user_settings = user.settings
                if not user_settings or not user_settings.notification_enabled:
                    logger.info(f"📊 {user.name}님의 알림이 비활성화되어 있습니다")
                    return True
                
                # 이메일 알림 전송 (알림 채널에 email이 포함된 경우)
                email_sent = False
                email_data = {
                    'etf_list': etf_list,
                    'total_amount': total_amount,
                    'etf_count': len(etf_data_list),
                    'analysis_result': analysis_result,
                    'recommendation': recommendation,
                    'confidence_score': confidence_score
                }
                
                email_sent = email_service.send_portfolio_analysis_notification(
                    user.email, user.name, email_data
                )
                
                if email_sent:
                    logger.info(f"📧 {user.name}님의 포트폴리오 분석 이메일 알림 전송 성공")
                else:
                    logger.warning(f"⚠️ {user.name}님의 포트폴리오 분석 이메일 알림 전송 실패")
                
                # 데이터베이스에 알림 저장
                title = f"📊 ETF 포트폴리오 투자 분석 알림 ({len(etf_data_list)}개 종목)"
                content = f"""
🤖 {user.name}님의 ETF 포트폴리오 투자 분석 결과

📊 오늘 투자일인 ETF:
{chr(10).join(etf_list)}

💰 총 투자 금액: {total_amount:,}원

📈 분석 결과:
{analysis_result}

💡 종합 추천사항:
{recommendation}

🎯 신뢰도: {confidence_score:.1f}%
                """.strip()
                
                sent_via = "email" if email_sent else "app"
                notification_data = NotificationCreate(
                    user_id=user.id,
                    title=title,
                    content=content,
                    type=self.notification_types.get('PORTFOLIO_ANALYSIS', 'portfolio_analysis'),
                    sent_via=sent_via
                )
                
                db_notification = create_notification(db, notification_data)
                
                if not db_notification:
                    logger.error(f"❌ {user.name}님의 포트폴리오 분석 알림 저장 실패")
                    return False
                
                logger.info(f"📧 {user.name}님에게 {len(etf_data_list)}개 ETF 통합 투자 알림 전송 완료")
                return True
            
            return False

        except Exception as e:
            logger.error(f"❌ 통합 알림 전송 중 오류: {e}")
            return False
    
    async def send_bulk_notifications(
        self,
        db: Session,
        notifications: List[Dict]
    ) -> Dict[str, int]:
        """
        대량 알림 전송
        
        Args:
            db: 데이터베이스 세션
            notifications: 알림 데이터 목록
        
        Returns:
            전송 결과 통계
        """
        success_count = 0
        failure_count = 0
        
        for notification_data in notifications:
            try:
                user_id = notification_data.get('user_id')
                user = db.query(User).filter(User.id == user_id).first()
                
                if not user:
                    failure_count += 1
                    continue
                
                # 알림 타입에 따른 전송
                if notification_data.get('type') == 'ai_analysis':
                    success = await self.send_ai_analysis_notification(
                        db, user, notification_data['etf'], 
                        notification_data['analysis_result'], 
                        notification_data['should_notify']
                    )
                elif notification_data.get('type') == 'investment_reminder':
                    success = await self.send_investment_reminder(
                        db, user, notification_data['etf_settings']
                    )
                elif notification_data.get('type') == 'integrated_investment':
                    success = await self.send_integrated_investment_notification(
                        db, user, notification_data['user_setting'],
                        notification_data['etf_data_list'],
                        notification_data['analysis_result'],
                        notification_data['recommendation'],
                        notification_data['confidence_score']
                    )
                else:
                    success = await self.send_system_notification(
                        db, user,
                        notification_data['title'],
                        notification_data['content'],
                        notification_data.get('type', 'system')
                    )
                
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                    
            except Exception as e:
                logger.error(f"❌ 대량 알림 전송 중 오류: {e}")
                failure_count += 1
        
        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "total_count": len(notifications)
        }

# 전역 알림 서비스 인스턴스
notification_service = NotificationService() 