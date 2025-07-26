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
from services.ai_service import analyze_investment_decision, request_batch_ai_analysis
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
            # 환경변수에서 간격 설정 가져오기
            interval = os.getenv('SCHEDULER_INTERVAL', '*/5')
            
            self.scheduler.add_job(
                self.check_investment_dates,
                CronTrigger(minute=interval),
                id='investment_notification_check',
                name='투자일 알림 체크 (병렬 처리 버전)',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"✅ 병렬 처리 알림 스케줄러 시작됨 (간격: {interval}분, 최대 동시 처리: {self.max_concurrent_users}명)")
    
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
    
    async def process_users_in_parallel(self, db: Session, today_users: List):
        """사용자들을 병렬로 처리 (배치 AI 분석 사용)"""
        logger.info(f"🔄 배치 AI 분석을 통한 병렬 처리 시작: {len(today_users)}개 사용자")
        
        # AI 분석 요청 데이터 준비
        analysis_requests = []
        user_data_map = {}  # 요청과 사용자 데이터 매핑
        
        for user_setting in today_users:
            try:
                # 사용자 정보 조회
                user = get_user_by_id(db, user_setting['user_setting'].user_id)
                if not user:
                    logger.warning(f"⚠️ 사용자 {user_setting['user_setting'].user_id}를 찾을 수 없습니다")
                    continue
                
                # ETF 정보 조회
                etf = get_etf_by_id(db, user_setting['etf_setting'].etf_id)
                if not etf:
                    logger.warning(f"⚠️ ETF {user_setting['etf_setting'].etf_id}를 찾을 수 없습니다")
                    continue
                
                # AI 분석 메시지 생성
                from services.ai_service import create_analysis_messages
                analysis_messages = create_analysis_messages(
                    user, 
                    user_setting['user_setting'], 
                    user_setting['etf_setting'], 
                    etf
                )
                
                # 배치 요청에 추가
                request_id = len(analysis_requests)
                analysis_requests.append({
                    "messages": analysis_messages,
                    "api_key": user_setting['user_setting'].api_key,
                    "model_type": user_setting['user_setting'].model_type
                })
                
                # 사용자 데이터 매핑
                user_data_map[request_id] = {
                    "user": user,
                    "user_setting": user_setting['user_setting'],
                    "etf_setting": user_setting['etf_setting'],
                    "etf": etf
                }
                
            except Exception as e:
                logger.error(f"❌ 사용자 데이터 준비 중 오류: {e}")
                continue
        
        if not analysis_requests:
            logger.warning("⚠️ 처리할 AI 분석 요청이 없습니다")
            return []
        
        # 배치 AI 분석 실행
        analysis_results = await request_batch_ai_analysis(analysis_requests)
        
        # 결과 처리 및 알림 생성
        results = []
        for i, analysis_result in enumerate(analysis_results):
            if i in user_data_map:
                try:
                    user_data = user_data_map[i]
                    result = await self.process_analysis_result(
                        db, user_data, analysis_result
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"❌ 분석 결과 처리 중 오류: {e}")
                    results.append(None)
        
        success_count = sum(1 for result in results if result is not None)
        logger.info(f"✅ 배치 AI 분석 완료: 성공 {success_count}개, 실패 {len(results) - success_count}개")
        
        return results
    
    async def process_analysis_result(self, db: Session, user_data: dict, analysis_result: str):
        """AI 분석 결과 처리 및 알림 생성"""
        try:
            user = user_data["user"]
            user_setting = user_data["user_setting"]
            etf_setting = user_data["etf_setting"]
            etf = user_data["etf"]
            
            if not analysis_result:
                logger.warning(f"⚠️ {user.name}님의 {etf.symbol} ETF 분석 결과가 없습니다")
                return None
            
            # 이전 분석 결과 조회
            from services.ai_service import get_previous_analysis, save_analysis_result
            previous_analysis = get_previous_analysis(user.id, etf.symbol, db)
            
            # 알림 전송 여부 결정
            from services.ai_service import determine_notification_need, extract_recommendation, extract_confidence_score
            should_notify = determine_notification_need(analysis_result, previous_analysis)
            
            # 분석 결과 저장
            save_analysis_result(user.id, etf.symbol, analysis_result, db)
            
            # 추천사항 및 신뢰도 추출
            recommendation = extract_recommendation(analysis_result)
            confidence_score = extract_confidence_score(analysis_result)
            
            # 알림 전송
            if should_notify:
                await self.send_investment_notification(
                    user, user_setting, etf_setting, etf, 
                    analysis_result, recommendation, confidence_score
                )
            
            logger.info(f"✅ {user.name}님의 {etf.symbol} ETF 분석 완료: 알림 {'전송' if should_notify else '불필요'}")
            
            return {
                'user_id': user.id,
                'etf_symbol': etf.symbol,
                'should_notify': should_notify,
                'analysis_result': analysis_result,
                'recommendation': recommendation,
                'confidence_score': confidence_score
            }
            
        except Exception as e:
            logger.error(f"❌ 분석 결과 처리 중 오류: {e}")
            return None
    
    async def send_investment_notification(
        self, user, user_setting, etf_setting, etf, 
        analysis_result, recommendation, confidence_score
    ):
        """투자 알림 전송"""
        try:
            # 알림 메시지 생성
            notification_message = f"""
🤖 {user.name}님의 {etf.symbol} ETF 투자 분석 결과

📊 분석 결과:
{analysis_result}

💡 추천사항:
{recommendation}

🎯 신뢰도: {confidence_score:.1f}%

📅 투자일: {etf_setting.cycle} (매 {etf_setting.day}일)
💰 투자 금액: {etf_setting.amount:,}원
            """.strip()
            
            # 알림 전송
            await notification_service.send_notification(
                user_id=user.id,
                title=f"📈 {etf.symbol} ETF 투자 알림",
                message=notification_message,
                notification_type="investment_analysis"
            )
            
            logger.info(f"📧 {user.name}님에게 {etf.symbol} ETF 투자 알림 전송 완료")
            
        except Exception as e:
            logger.error(f"❌ 알림 전송 중 오류: {e}")
    
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
    
    async def process_user_investment(self, db: Session, investor_data: dict):
        """사용자 투자 처리 (개선된 버전)"""
        user_setting = investor_data['user_setting']
        etf_setting = investor_data['etf_setting']
        
        start_time = time.time()
        
        try:
            # 사용자 정보 조회
            user = get_user_by_id(db, user_setting.user_id)
            if not user:
                logger.warning(f"⚠️ 사용자 {user_setting.user_id}를 찾을 수 없습니다")
                return None
            
            # ETF 정보 조회
            etf = get_etf_by_id(db, etf_setting.etf_id)
            if not etf:
                logger.warning(f"⚠️ ETF {etf_setting.etf_id}를 찾을 수 없습니다")
                return None
            
            logger.info(f"🤖 {user.name}님의 {etf.symbol} ETF AI 분석 시작...")
            
            # AI 분석 수행 (타임아웃 설정)
            try:
                analysis_result = await asyncio.wait_for(
                    analyze_investment_decision(user, user_setting, etf_setting, etf),
                    timeout=30.0  # 30초 타임아웃
                )
            except asyncio.TimeoutError:
                logger.error(f"⏰ {user.name}님의 AI 분석 타임아웃")
                return None
            
            if not analysis_result:
                logger.warning(f"⚠️ {user.name}님의 {etf.symbol} ETF AI 분석 실패")
                return None
            
            # 알림 전송 (병렬로 처리)
            notification_tasks = [
                notification_service.send_ai_analysis_notification(
                    db, user, etf, analysis_result, analysis_result['should_notify']
                ),
                notification_service.send_investment_reminder(
                    db, user, [etf_setting]
                )
            ]
            
            await asyncio.gather(*notification_tasks)
            
            processing_time = time.time() - start_time
            logger.info(f"✅ {user.name}님의 {etf.symbol} ETF 처리 완료 ({processing_time:.2f}초)")
            
            return True
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ {user_setting.user_id} 사용자 투자 처리 중 오류 ({processing_time:.2f}초): {e}")
            return None

# 전역 스케줄러 인스턴스
scheduler = NotificationScheduler()

def start_notification_scheduler():
    """알림 스케줄러 시작"""
    scheduler.start()

def stop_notification_scheduler():
    """알림 스케줄러 중지"""
    scheduler.stop() 