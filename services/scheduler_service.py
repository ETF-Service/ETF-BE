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
from crud.notification import get_users_with_notifications_enabled
from crud.etf import get_investment_etf_settings_by_user_id, get_etf_by_id
from crud.user import get_user_by_id
from services.ai_service import analyze_investment_decision
from services.notification_service import notification_service

logger = logging.getLogger(__name__)

class NotificationScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    def start(self):
        """스케줄러 시작"""
        if not self.is_running:
            # 테스트용: 5분마다 실행
            self.scheduler.add_job(
                self.check_investment_dates,
                CronTrigger(minute='*/5'),  # 5분마다
                id='investment_notification_check',
                name='투자일 알림 체크 (테스트용)',
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
                    break  # 한 사용자당 하나의 투자일만 처리
        
        return today_investors
    
    def is_investment_day(self, etf_setting, today_weekday: int, today_day: int) -> bool:
        """투자일 여부 확인"""
        if etf_setting.cycle == 'daily':
            return True
        elif etf_setting.cycle == 'weekly':
            # 요일 체크 (0=월요일, 6=일요일)
            return today_weekday == etf_setting.day
        elif etf_setting.cycle == 'monthly':
            # 월 투자일 체크
            return today_day == etf_setting.day
        return False
    
    async def process_user_investment(self, db: Session, investor_data: dict):
        """사용자 투자 처리"""
        user_setting = investor_data['user_setting']
        etf_setting = investor_data['etf_setting']
        
        try:
            # 사용자 정보 조회
            user = get_user_by_id(db, user_setting.user_id)
            if not user:
                logger.warning(f"⚠️ 사용자 {user_setting.user_id}를 찾을 수 없습니다")
                return
            
            # ETF 정보 조회
            etf = get_etf_by_id(db, etf_setting.etf_id)
            if not etf:
                logger.warning(f"⚠️ ETF {etf_setting.etf_id}를 찾을 수 없습니다")
                return
            
            logger.info(f"🤖 {user.name}님의 {etf.symbol} ETF AI 분석 시작...")
            
            # AI 분석 수행
            analysis_result = await analyze_investment_decision(
                user, user_setting, etf_setting, etf
            )
            
            if not analysis_result:
                logger.warning(f"⚠️ {user.name}님의 {etf.symbol} ETF AI 분석 실패")
                return
            
            # 알림 전송 (새로운 알림 서비스 사용)
            await notification_service.send_ai_analysis_notification(
                db, user, etf, analysis_result, analysis_result['should_notify']
            )
            
            # 투자일 알림도 함께 전송
            etf_settings = [etf_setting]  # 단일 ETF 설정을 리스트로 변환
            await notification_service.send_investment_reminder(
                db, user, etf_settings
            )
            
            logger.info(f"✅ {user.name}님의 {etf.symbol} ETF 처리 완료")
            
        except Exception as e:
            logger.error(f"❌ {user_setting.user_id} 사용자 투자 처리 중 오류: {e}")

# 전역 스케줄러 인스턴스
scheduler = NotificationScheduler()

def start_notification_scheduler():
    """알림 스케줄러 시작"""
    scheduler.start()

def stop_notification_scheduler():
    """알림 스케줄러 중지"""
    scheduler.stop() 