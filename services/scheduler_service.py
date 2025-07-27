"""
알림 스케줄러 서비스 (병렬 처리 버전)
매일 1시간마다 실행되어 투자일인 사용자에게 AI 분석 기반 알림을 생성
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
from typing import List
import asyncio
import os
import time

from database import SessionLocal
from crud.notification import get_users_with_notifications_enabled
from crud.etf import get_investment_etf_settings_by_user_id, get_etf_by_id
from crud.user import get_user_by_id
from services.ai_service import (
    request_batch_ai_analysis, 
    create_integrated_analysis_messages, 
    determine_notification_need)
from services.notification_service import notification_service

logger = logging.getLogger(__name__)

class NotificationScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        # 병렬 처리를 위한 설정
        self.max_concurrent_users = int(os.getenv('MAX_CONCURRENT_USERS', '10'))
    
    def start(self):
        """스케줄러 시작"""
        if not self.is_running:
            self.scheduler.add_job(
                self.check_investment_dates,
                # CronTrigger(hour='8-17/3', minute='0'),
				CronTrigger(minute='*/5'),
                id='investment_notification_check',
                name='투자일 알림 체크 (병렬 처리 버전)',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"✅ 병렬 처리 알림 스케줄러 시작됨 (매일 8시-17시, 3시간 간격, 최대 동시 처리: {self.max_concurrent_users}명)")
    
    def stop(self):
        """스케줄러 중지"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("⏹️ 알림 스케줄러 중지됨")
    
    async def check_investment_dates(self):
        """투자일 체크 및 알림 생성 (병렬 처리)"""
        start_time = time.time()
        logger.info("🔍 투자일 체크 시작 (병렬 처리)...")
        
        db = SessionLocal()
        try:
            # 오늘 투자일인 사용자 조회
            today_users = self.get_users_with_investment_today(db)
            
            if not today_users:
                logger.info("ℹ️ 오늘 투자일인 사용자가 없습니다")
                return
            
            logger.info(f"📅 오늘 투자일인 사용자: {len(today_users)}명")
            
            # 병렬 처리로 개선
            await self.process_users_in_parallel(db, today_users)
            
            # 성능 메트릭 기록
            processing_time = time.time() - start_time
            await self.record_metrics(len(today_users), processing_time)
            
        except Exception as e:
            logger.error(f"❌ 투자일 체크 중 오류 발생: {e}")
        finally:
            db.close()
    
    def get_users_with_investment_today(self, db: Session) -> List:
        """오늘 투자일인 사용자 조회 (한 사용자의 모든 투자일 ETF 포함)"""
        today = datetime.now()
        today_weekday = today.weekday()  # 0=월요일, 6=일요일 (Python datetime.weekday() 기준)
        today_day = today.day  # 1-31
        
        # 투자 설정이 있고 알림이 활성화된 사용자 조회
        enabled_users = get_users_with_notifications_enabled(db)
        
        today_investors = []
        
        for user_setting in enabled_users:
            # 해당 사용자의 ETF 투자 설정 조회
            etf_settings = get_investment_etf_settings_by_user_id(db, user_setting.user_id)
            
            # 오늘 투자일인 모든 ETF 설정 수집
            today_etf_settings = []
            for etf_setting in etf_settings:
                if self.is_investment_day(etf_setting, today_weekday, today_day):
                    today_etf_settings.append(etf_setting)
            
            # 오늘 투자일인 ETF가 있는 경우에만 추가
            if today_etf_settings:
                today_investors.append({
                    'user_setting': user_setting,
                    'etf_settings': today_etf_settings  # 모든 ETF 설정을 포함
                })
        
        return today_investors
    
    async def process_users_in_parallel(self, db: Session, today_users: List):
        """사용자들을 병렬로 처리하고, 결과를 취합하여 대량 알림을 전송"""
        logger.info(f"🔄 사용자별 통합 AI 분석 시작: {len(today_users)}개 사용자")
        
        # 사용자별 통합 분석 요청 데이터 준비
        analysis_requests = []
        user_data_map = {}  # 요청과 사용자 데이터 매핑
        
        for user_data in today_users:
            try:
                # 사용자 정보 조회
                user = get_user_by_id(db, user_data['user_setting'].user_id)
                if not user:
                    logger.warning(f"⚠️ 사용자 {user_data['user_setting'].user_id}를 찾을 수 없습니다")
                    continue
                
                # 해당 사용자의 모든 ETF 정보 조회
                etf_data_list = []
                for etf_setting in user_data['etf_settings']:
                    etf = get_etf_by_id(db, etf_setting.etf_id)
                    if not etf:
                        logger.warning(f"⚠️ ETF {etf_setting.etf_id}를 찾을 수 없습니다")
                        continue
                    etf_data_list.append({
                        'etf_setting': etf_setting,
                        'etf': etf
                    })
                
                if not etf_data_list:
                    logger.warning(f"⚠️ {user.name}님의 유효한 ETF가 없습니다")
                    continue
                
                # 사용자의 모든 ETF를 포함한 통합 분석 메시지 생성
                analysis_messages = create_integrated_analysis_messages(
                    user, user_data['user_setting'], etf_data_list
                )
                
                # 배치 요청에 추가
                request_id = len(analysis_requests)
                analysis_requests.append({
                    "messages": analysis_messages,
                    "api_key": user_data['user_setting'].api_key,
                    "model_type": user_data['user_setting'].model_type
                })
                
                # 사용자 데이터 매핑
                user_data_map[request_id] = {
                    "user": user,
                    "user_setting": user_data['user_setting'],
                    "etf_data_list": etf_data_list
                }
                
                logger.info(f"📊 {user.name}님의 {len(etf_data_list)}개 ETF 통합 분석 준비 완료")
                
            except Exception as e:
                logger.error(f"❌ 사용자 데이터 준비 중 오류: {e}")
                continue
        
        if not analysis_requests:
            logger.warning("⚠️ 처리할 AI 분석 요청이 없습니다")
            return
        
        # 배치 AI 분석 실행
        analysis_results = await request_batch_ai_analysis(analysis_requests)
        
        # 알림 전송을 위한 데이터 수집
        notifications_to_send = []
        for i, analysis_result in enumerate(analysis_results):
            if i in user_data_map and analysis_result:
                try:
                    user_data = user_data_map[i]
                    user = user_data["user"]
                    
                    # 분석 결과 저장
                    portfolio_key = f"portfolio_{user.id}"
                    
                    # 알림 필요성 판단 및 파싱된 데이터 수신
                    should_notify, parsed_analysis = determine_notification_need(db, user, analysis_result)
                    logger.info(f"✅ {user.name}님의 {len(user_data['etf_data_list'])}개 ETF 통합 분석 완료: 알림 {'전송 필요' if should_notify else '불필요'}")

                    if should_notify:
                        notifications_to_send.append({
                            'type': 'integrated_investment',
                            'user_id': user.id,
                            'user_setting': user_data["user_setting"],
                            'etf_data_list': user_data["etf_data_list"],
                            'parsed_analysis': parsed_analysis # 파싱된 데이터를 전달
                        })
                except Exception as e:
                    logger.error(f"❌ 통합 분석 결과 처리 중 오류: {e}")

        # 수집된 알림들을 대량으로 전송
        if notifications_to_send:
            logger.info(f"📤 통합 투자 알림 대량 전송 시작: {len(notifications_to_send)}개")
            result_summary = await notification_service.send_bulk_notifications(notifications_to_send)
            logger.info(f"✅ 통합 투자 알림 대량 전송 완료: {result_summary}")
        else:
            logger.info("ℹ️ 전송할 통합 투자 알림이 없습니다.")
    
    async def record_metrics(self, user_count: int, processing_time: float):
        """성능 메트릭 기록"""
        avg_time_per_user = processing_time / user_count if user_count > 0 else 0
        
        logger.info(f"📊 성능 메트릭:")
        logger.info(f"   - 총 처리 시간: {processing_time:.2f}초")
        logger.info(f"   - 처리된 사용자: {user_count}명")
        logger.info(f"   - 사용자당 평균 시간: {avg_time_per_user:.2f}초")
        logger.info(f"   - 처리 속도: {user_count/processing_time:.2f}명/초")
    
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
    


# 전역 스케줄러 인스턴스
scheduler = NotificationScheduler()

def start_notification_scheduler():
    """알림 스케줄러 시작"""
    scheduler.start()

def stop_notification_scheduler():
    """알림 스케줄러 중지"""
    scheduler.stop() 