"""
알림 스케줄러 서비스
매일 1시간마다 실행되어 투자일인 사용자에게 AI 분석 기반 알림을 생성
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
from typing import List
import asyncio

from database import SessionLocal
from crud.notification import create_notification, get_users_with_notifications_enabled
from crud.etf import get_investment_etf_settings_by_user_id, get_etf_by_id
from crud.user import get_user_by_id
from schemas.notification import NotificationCreate
from config.notification_config import (
    get_scheduler_interval,
    get_notification_time,
    NOTIFICATION_TYPES,
    NOTIFICATION_TITLES,
    NOTIFICATION_CONTENT_TEMPLATES
)
from services.ai_service import analyze_investment_decision

logger = logging.getLogger(__name__)

class NotificationScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    def start(self):
        """스케줄러 시작"""
        if not self.is_running:
            # 매일 1시간마다 실행 (매시 정각)
            self.scheduler.add_job(
                self.check_investment_dates,
                CronTrigger(hour='*', minute=0),  # 매시 정각
                id='investment_notification_check',
                name='투자일 알림 체크',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info("✅ 알림 스케줄러 시작됨")
    
    def stop(self):
        """스케줄러 중지"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("⏹️ 알림 스케줄러 중지됨")
    
    async def check_investment_dates(self):
        """투자일 체크 및 알림 생성"""
        logger.info("🔍 투자일 체크 시작...")
        
        db = SessionLocal()
        try:
            # 오늘 투자일인 사용자 조회
            today_users = self.get_users_with_investment_today(db)
            
            if not today_users:
                logger.info("ℹ️ 오늘 투자일인 사용자가 없습니다")
                return
            
            logger.info(f"📅 오늘 투자일인 사용자: {len(today_users)}명")
            
            # 각 사용자별로 AI 분석 및 알림 생성
            for user_setting in today_users:
                await self.process_user_investment(db, user_setting)
                
        except Exception as e:
            logger.error(f"❌ 투자일 체크 중 오류 발생: {e}")
        finally:
            db.close()
    
    def get_users_with_investment_today(self, db: Session) -> List:
        """오늘 투자일인 사용자 조회"""
        today = datetime.now()
        today_weekday = today.weekday()  # 0=월요일, 6=일요일 (Python datetime.weekday() 기준)
        today_day = today.day  # 1-31
        
        # 투자 설정이 있고 알림이 활성화된 사용자 조회
        enabled_users = get_users_with_notifications_enabled(db)
        
        today_investors = []
        
        for user_setting in enabled_users:
            # 해당 사용자의 ETF 투자 설정 조회
            etf_settings = get_investment_etf_settings_by_user_id(db, user_setting.user_id)
            
            for etf_setting in etf_settings:
                if self.is_investment_day(etf_setting, today_weekday, today_day):
                    today_investors.append({
                        'user_setting': user_setting,
                        'etf_setting': etf_setting
                    })
        
        return today_investors
    
    def is_investment_day(self, etf_setting, today_weekday: int, today_day: int) -> bool:
        """오늘이 투자일인지 확인"""
        cycle = etf_setting.cycle
        day = etf_setting.day
        
        if cycle == 'daily':
            return True
        elif cycle == 'weekly':
            return today_weekday == day  # 0=월요일, 6=일요일 (Python datetime.weekday() 기준)
        elif cycle == 'monthly':
            return today_day == day  # 1-31
        else:
            return False
    
    async def process_user_investment(self, db: Session, investor_data: dict):
        """사용자별 투자 처리 및 알림 생성"""
        user_setting = investor_data['user_setting']
        etf_setting = investor_data['etf_setting']
        
        try:
            # 사용자 정보 조회
            user = get_user_by_id(db, user_setting.user_id)
            if not user:
                logger.warning(f"⚠️ 사용자를 찾을 수 없음: {user_setting.user_id}")
                return
            
            # ETF 정보 조회
            etf = get_etf_by_id(db, etf_setting.etf_id)
            if not etf:
                logger.warning(f"⚠️ ETF를 찾을 수 없음: {etf_setting.etf_id}")
                return
            
            logger.info(f"🤖 {user.name}님의 {etf.symbol} ETF AI 분석 시작...")
            
            # AI 분석 요청
            analysis_result = await analyze_investment_decision(
                user, user_setting, 
                etf_setting, 
                etf
            )
            
            if analysis_result and analysis_result.get('should_notify', False):
                # 알림 생성
                await self.create_investment_notification(
                    db, user, etf, etf_setting, analysis_result
                )
            else:
                logger.info(f"ℹ️ {user.name}님의 {etf.symbol} ETF - 알림 불필요")
                
        except Exception as e:
            logger.error(f"❌ 사용자 {user_setting.user_id} 처리 중 오류: {e}")
    
    async def create_investment_notification(
        self, 
        db: Session, 
        user, 
        etf, 
        etf_setting, 
        analysis_result: dict
    ):
        """투자 알림 생성"""
        try:
            # 알림 제목 및 내용 생성
            title = NOTIFICATION_TITLES[NOTIFICATION_TYPES['AI_ANALYSIS']]
            
            content = NOTIFICATION_CONTENT_TEMPLATES['ai_analysis']
            if analysis_result.get('recommendation'):
                content += f"\n\n추천사항: {analysis_result['recommendation']}"
            
            # 알림 생성
            notification_data = NotificationCreate(
                user_id=user.id,
                title=title,
                content=content,
                type=NOTIFICATION_TYPES['AI_ANALYSIS'],
                sent_via='app'  # 기본적으로 앱 내 알림
            )
            
            notification = create_notification(db, notification_data)
            logger.info(f"✅ {user.name}님에게 {etf.symbol} ETF 알림 생성 완료")
            
            return notification
            
        except Exception as e:
            logger.error(f"❌ 알림 생성 중 오류: {e}")
            return None

# 전역 스케줄러 인스턴스
notification_scheduler = NotificationScheduler()

def start_notification_scheduler():
    """알림 스케줄러 시작"""
    notification_scheduler.start()

def stop_notification_scheduler():
    """알림 스케줄러 중지"""
    notification_scheduler.stop() 