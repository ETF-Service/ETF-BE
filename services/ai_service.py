"""
AI 분석 서비스
ETF_AI 모듈과 연동하여 투자 결정을 분석하고 알림 여부를 결정
"""

import httpx
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import json

from config.notification_config import get_ai_analysis_threshold, NOTIFICATION_TYPES
from models import User, InvestmentSettings
from crud.notification import get_notifications_by_user_id_and_type

logger = logging.getLogger(__name__)

import os

# ETF_AI 서비스 URL (환경 변수에서 가져오거나 기본값 사용)
AI_SERVICE_URL = os.getenv("ETF_AI_SERVICE_URL", "http://localhost:8001")
MAX_RETRIES = int(os.getenv("AI_SERVICE_MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("AI_SERVICE_RETRY_DELAY", "5"))

def create_integrated_analysis_messages(
    user: User,
    user_setting: InvestmentSettings,
    etf_data_list: list,
) -> list:
    """
    사용자의 모든 ETF를 포함한 통합 분석 메시지 생성 (구조적/구체적 프롬프트)
    market_news: 외부 시장 뉴스 요약(선택)
    """
    try:
        # 1. 사용자 정보
        user_info = f"""[사용자 정보]\n- 이름: {user.name}\n- 위험 성향(0~10): {user_setting.risk_level}\n- 투자 목표/페르소나: {user_setting.persona or '미입력'}"""
        # 2. ETF 정보
        etf_info = "[ETF 목록]\n" + "\n".join([
            f"- {etf_data['etf'].symbol}: {etf_data['etf_setting'].amount:,}만원, 주기: {etf_data['etf_setting'].cycle}, 이름: {etf_data['etf'].name}"
            for etf_data in etf_data_list
        ])
        # 3. 분석 기준/목표
        analysis_criteria = (
            "[분석 기준]\n"
            "- 시장 변동성이 20% 이상이거나, 사용자 위험 성향이 8 이상일 때만 비중 조정 권고\n"
            "- ETF별로 조정 사유와 권장 비중을 명확히 제시\n"
            "- 투자 금액, 주기, 시장 상황, 사용자 성향을 모두 고려\n"
            "- 불필요한 조정은 피하고, 반드시 조정이 필요한 경우만 권고\n"
        )
        # 4. 예시 답변 포맷
        example_format = (
            "[분석 결과 예시]\n"
            "- SPY: 비중 유지 (시장 안정, 추가 매수 불필요)\n"
            "- QQQ: 비중 10% 증가 권고 (기술주 강세, 성장 기대)\n"
            "- 종합 의견: 전체 포트폴리오의 위험도는 적정 수준, 추가 리밸런싱 필요 없음\n"
        )
        # 5. 오늘 날짜
        today_date = f"[분석 기준일] {datetime.now().year}년 {datetime.now().month}월 {datetime.now().day}일"
        # 6. 최종 developer 메시지 조립
        developer_content = (
            f"""
{user_info}\n\n{etf_info}\n\n{analysis_criteria}\n{example_format}\n{today_date}\n\n위 정보를 바탕으로 오늘의 투자 조언을 위 예시 포맷에 맞춰 작성해줘.\nETF별로 조정이 필요한 경우 그 이유를 반드시 명확히 설명하고, 종합 의견도 꼭 포함해줘.\n답변은 반드시 [분석 결과 예시] 포맷을 따라줘.
"""
        )
        # 7. user 메시지(명령)
        user_content = (
            "아래 정보를 참고해서 오늘 투자할 ETF 포트폴리오의 각 상품별 투자 비중을 조정해야 하는지 판단해줘. "
            "시장 뉴스, 투자 금액, 주기, 사용자 성향을 모두 고려해서, 조정이 필요한 경우만 구체적으로 권고해줘. "
            "ETF별로 조정 사유와 권장 비중을 명확히 제시하고, 종합 의견도 꼭 포함해줘."
        )
        messages = [
            {"role": "developer", "content": developer_content},
            {"role": "user", "content": user_content}
        ]
        return messages
    except Exception as e:
        logger.error(f"❌ 통합 분석 메시지 생성 중 오류: {e}")
        return []

async def request_ai_analysis(
    messages: list, 
    api_key: str, 
    model_type: str
) -> Optional[str]:
    """ETF_AI 서비스에 분석 요청 - analyze_sentiment 함수 사용 (재시도 로직 포함)"""
    
    import asyncio
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"🔄 AI 서비스 요청 시도 {attempt + 1}/{MAX_RETRIES}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{AI_SERVICE_URL}/analyze",
                    json={
                        "messages": messages,
                        "api_key": api_key,
                        "model_type": model_type
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success", False):
                        processing_time = result.get("processing_time", 0)
                        logger.info(f"✅ AI 분석 성공 (시도 {attempt + 1}, 처리시간: {processing_time:.2f}초)")
                        return result.get("answer", "")
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        logger.error(f"❌ AI 분석 실패: {error_msg}")
                        return None
                else:
                    logger.error(f"❌ AI 서비스 HTTP 오류: {response.status_code}")
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    return None
                    
        except httpx.TimeoutException:
            logger.warning(f"⏰ AI 서비스 타임아웃 (시도 {attempt + 1})")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
                continue
            return None
            
        except httpx.ConnectError:
            logger.error(f"🔌 AI 서비스 연결 오류 (시도 {attempt + 1}): {AI_SERVICE_URL}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
                continue
            return None
            
        except Exception as e:
            logger.error(f"❌ AI 서비스 요청 중 예상치 못한 오류 (시도 {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
                continue
            return None
    
    logger.error(f"❌ AI 서비스 요청 최대 재시도 횟수 초과 ({MAX_RETRIES}회)")
    return None

async def request_batch_ai_analysis(
    analysis_requests: list
) -> list:
    """ETF_AI 서비스에 배치 분석 요청 - 병렬 처리 지원"""
    
    import asyncio
    
    try:
        logger.info(f"🔄 배치 AI 분석 요청 시작: {len(analysis_requests)}개")
        
        async with httpx.AsyncClient(timeout=120.0) as client:  # 배치 처리이므로 더 긴 타임아웃
            response = await client.post(
                f"{AI_SERVICE_URL}/analyze/batch",
                json={
                    "requests": [
                        {
                            "messages": req["messages"],
                            "api_key": req["api_key"],
                            "model_type": req["model_type"]
                        }
                        for req in analysis_requests
                    ]
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    summary = result.get("summary", {})
                    logger.info(f"✅ 배치 AI 분석 성공: {summary.get('successful_count', 0)}개 성공, {summary.get('failed_count', 0)}개 실패, 총 시간: {summary.get('total_processing_time', 0):.2f}초")
                    
                    # 성공한 결과들만 반환
                    successful_results = result.get("results", {}).get("successful", [])
                    return [res.get("answer", "") for res in successful_results]
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"❌ 배치 AI 분석 실패: {error_msg}")
                    return []
            else:
                logger.error(f"❌ 배치 AI 서비스 HTTP 오류: {response.status_code}")
                return []
                
    except httpx.TimeoutException:
        logger.warning(f"⏰ 배치 AI 서비스 타임아웃")
        return []
        
    except httpx.ConnectError:
        logger.error(f"🔌 배치 AI 서비스 연결 오류: {AI_SERVICE_URL}")
        return []
        
    except Exception as e:
        logger.error(f"❌ 배치 AI 서비스 요청 중 예상치 못한 오류: {e}")
        return []

def determine_notification_need(analysis_result: str) -> bool:
    """
    현재 AI 분석 결과만을 기반으로 알림 필요성 판단 (ML 모델 제거)
    
    Args:
        analysis_result: 현재 AI 분석 결과
    
    Returns:
        알림 전송 여부
    """
    try:
        logger.debug(f"🚀 알림 필요성 판단 시작...")
        logger.debug(f"입력된 분석 결과: {analysis_result[:200]}...")

        # 1. 긴급성 수준 분석 (가장 중요)
        urgency_level = analyze_urgency_level(analysis_result)
        
        # 2. 권장사항 중요도 분석
        recommendation_importance = analyze_recommendation_importance(analysis_result)
        
        # 3. 위험도 수준 분석
        risk_level = analyze_risk_level(analysis_result)
        
        # 4. 시장 상황 중요도 분석
        market_importance = analyze_market_importance(analysis_result)
        
        # 5. 투자 금액 변화 중요도 분석
        amount_importance = analyze_amount_importance(analysis_result)
        
        # 6. 종합 점수 계산 (ML 제거)
        notification_score = calculate_simplified_notification_score(
            urgency_level=urgency_level,
            recommendation_importance=recommendation_importance,
            risk_level=risk_level,
            market_importance=market_importance,
            amount_importance=amount_importance
        )
        
        # 7. 동적 임계값 적용
        dynamic_threshold = get_simplified_dynamic_threshold(
            analysis_result, 
            urgency_level
        )
        
        should_notify = notification_score > dynamic_threshold
        
        # 상세 로깅
        logger.debug(f"📊 알림 판단 최종 결과:")
        logger.debug(f"   - 긴급성 수준: {urgency_level:.3f}")
        logger.debug(f"   - 권장사항 중요도: {recommendation_importance:.3f}")
        logger.debug(f"   - 위험도 수준: {risk_level:.3f}")
        logger.debug(f"   - 시장 상황 중요도: {market_importance:.3f}")
        logger.debug(f"   - 투자 금액 중요도: {amount_importance:.3f}")
        logger.debug(f"   - 종합 점수: {notification_score:.3f}")
        logger.debug(f"   - 동적 임계값: {dynamic_threshold:.3f}")
        logger.debug(f"   - 최종 알림 결정: {'✅ 전송' if should_notify else '❌ 미전송'}")
        
        return should_notify
        
    except Exception as e:
        logger.error(f"❌ 단순화된 알림 판단 중 오류: {e}")
        return True  # 오류 시 안전하게 알림 전송

def analyze_recommendation_importance(analysis_result: str) -> float:
    """투자 권장사항의 중요도 분석 (가중치 기반으로 변경)"""
    try:
        # 가중치 기반 키워드
        keyword_weights = {
            # 직접적인 행동 지시 (3점)
            '매수': 3, '매도': 3, '증가': 3, '감소': 3, '상향': 3, '하향': 3, '변경': 3, '조정': 3, '회수': 3,
            # 긴급성/경고 (2점)
            '즉시': 2, '당장': 2, '긴급': 2, '주의': 2, '경고': 2,
            # 추천/제안 (1점)
            '추천': 1, '권고': 1, '제안': 1,
            # 중립/관망 (0점)
            '유지': 0, '보유': 0, '현상유지': 0, '관망': 0, '신중': 0, '보수': 0
        }
        
        text_lower = analysis_result.lower()
        
        score = 0
        matched_keywords = []
        for keyword, weight in keyword_weights.items():
            if keyword in text_lower:
                score += weight
                matched_keywords.append(f"{keyword}({weight})")
        
        logger.debug(f"권장사항 중요도 분석: 매칭된 키워드: {', '.join(matched_keywords) if matched_keywords else '없음'}. 총점: {score}")

        # 점수 구간에 따라 최종 점수 반환
        # 5점 이상이면 매우 중요(1.0), 3점 이상이면 중요(0.8), 1점 이상이면 보통(0.5), 그 외에는 낮음(0.2)
        if score >= 5:
            final_score = 1.0
        elif score >= 3:
            final_score = 0.8
        elif score >= 1:
            final_score = 0.5
        else:
            final_score = 0.2
            
        logger.debug(f"권장사항 중요도 분석: 최종 점수: {final_score}")
        return final_score
            
    except Exception as e:
        logger.error(f"❌ 권장사항 중요도 분석 중 오류: {e}")
        return 0.5

def analyze_risk_level(analysis_result: str) -> float:
    """위험도 수준 분석 (0.0 ~ 1.0, 가중치 기반으로 변경)"""
    try:
        # 가중치 기반 키워드
        keyword_weights = {
            # 매우 높음 (3점)
            '불안정': 3, '변동성 증가': 3, '위험도 증가': 3,
            # 높음 (2점)
            '위험': 2, '주의': 2, '높은 위험': 2,
            # 보통 (1점)
            '보통 위험': 1, '중간': 1, '적당한': 1, '보통': 1,
            # 낮음 (0점)
            '낮은 위험': 0, '안정적': 0, '보수적': 0, '안전': 0, '평온': 0
        }
        
        text_lower = analysis_result.lower()
        
        score = 0
        matched_keywords = []
        for keyword, weight in keyword_weights.items():
            if keyword in text_lower:
                score += weight
                matched_keywords.append(f"{keyword}({weight})")

        logger.debug(f"위험도 분석: 매칭된 키워드: {', '.join(matched_keywords) if matched_keywords else '없음'}. 총점: {score}")

        # 점수 구간에 따라 최종 점수 반환
        if score >= 4:
            final_score = 1.0
        elif score >= 2:
            final_score = 0.8
        elif score >= 1:
            final_score = 0.5
        else:
            final_score = 0.2
            
        logger.debug(f"위험도 분석: 최종 점수: {final_score}")
        return final_score
        
    except Exception as e:
        logger.error(f"❌ 위험도 분석 중 오류: {e}")
        return 0.5

def analyze_market_importance(analysis_result: str) -> float:
    """시장 상황의 중요도 분석 (가중치 기반으로 변경)"""
    try:
        # 가중치 기반 키워드
        keyword_weights = {
            # 매우 중요 (3점)
            '급변': 3, '긴급': 3, '침체': 3, '위험': 3,
            # 중요 (2점)
            '하락장': 2, '변동성': 2, '불안정': 2, '부정적': 2,
            # 보통 (1점)
            '상승장': 1, '호황': 1, '기회': 1, '긍정적': 1,
            # 안정 (0점)
            '안정': 0, '평온': 0, '예측가능': 0, '일정': 0, '관망': 0
        }
        
        text_lower = analysis_result.lower()
        
        score = 0
        matched_keywords = []
        for keyword, weight in keyword_weights.items():
            if keyword in text_lower:
                score += weight
                matched_keywords.append(f"{keyword}({weight})")
        
        logger.debug(f"시장 상황 중요도 분석: 매칭된 키워드: {', '.join(matched_keywords) if matched_keywords else '없음'}. 총점: {score}")

        # 점수 구간에 따라 최종 점수 반환
        if score >= 4:
            final_score = 1.0
        elif score >= 2:
            final_score = 0.8
        elif score >= 1:
            final_score = 0.5
        else:
            final_score = 0.2
            
        logger.debug(f"시장 상황 중요도 분석: 최종 점수: {final_score}")
        return final_score
            
    except Exception as e:
        logger.error(f"❌ 시장 상황 중요도 분석 중 오류: {e}")
        return 0.5

def analyze_amount_importance(analysis_result: str) -> float:
    """투자 금액 변화의 중요도 분석"""
    try:
        # 금액 관련 정보 추출
        amounts = extract_investment_amounts(analysis_result)
        
        if not amounts:
            logger.debug("투자 금액 중요도 분석: 금액 정보 없음. 점수: 0.3")
            return 0.3  # 금액 정보가 없으면 낮은 중요도
        
        # 평균 금액 계산
        avg_amount = sum(amounts) / len(amounts)
        logger.debug(f"투자 금액 중요도 분석: 평균 금액 {avg_amount}만원")
        
        # 금액 크기에 따른 중요도 (큰 금액일수록 중요)
        if avg_amount > 100:  # 100만원 이상
            logger.debug("투자 금액 중요도 분석: 100만원 초과. 점수: 0.9")
            return 0.9
        elif avg_amount > 50:  # 50만원 이상
            logger.debug("투자 금액 중요도 분석: 50만원 초과. 점수: 0.7")
            return 0.7
        elif avg_amount > 20:  # 20만원 이상
            logger.debug("투자 금액 중요도 분석: 20만원 초과. 점수: 0.5")
            return 0.5
        else:
            logger.debug("투자 금액 중요도 분석: 20만원 이하. 점수: 0.3")
            return 0.3
            
    except Exception as e:
        logger.error(f"❌ 투자 금액 중요도 분석 중 오류: {e}")
        return 0.5

def calculate_simplified_notification_score(
    urgency_level: float,
    recommendation_importance: float,
    risk_level: float,
    market_importance: float,
    amount_importance: float
) -> float:
    """ML 제거된 단순화된 종합 알림 점수 계산"""
    try:
        # 가중치 재조정 (ML 점수 제거)
        weights = {
            'urgency_level': 0.35,           # 30% → 35%
            'recommendation_importance': 0.30, # 25% → 30%
            'risk_level': 0.15,              # 유지
            'market_importance': 0.15,       # 유지
            'amount_importance': 0.05        # 10% → 5%
        }
        
        logger.debug(f"종합 점수 계산 입력값: 긴급성={urgency_level}, 권장사항={recommendation_importance}, 위험도={risk_level}, 시장={market_importance}, 금액={amount_importance}")
        
        # 가중 평균 계산
        weighted_score = (
            urgency_level * weights['urgency_level'] +
            recommendation_importance * weights['recommendation_importance'] +
            risk_level * weights['risk_level'] +
            market_importance * weights['market_importance'] +
            amount_importance * weights['amount_importance']
        )
        
        final_score = min(weighted_score, 1.0)
        logger.debug(f"계산된 종합 점수: {final_score:.3f}")
        return final_score
        
    except Exception as e:
        logger.error(f"❌ 단순화된 알림 점수 계산 중 오류: {e}")
        return 0.5

def get_simplified_dynamic_threshold(analysis_result: str, urgency_level: float) -> float:
    """단순화된 동적 임계값 계산"""
    try:
        base_threshold = 0.7
        logger.debug(f"동적 임계값 계산 시작. 기본값: {base_threshold}")
        
        # 긴급성에 따른 임계값 조정
        if urgency_level > 0.8:
            base_threshold -= 0.3  # 긴급 상황은 매우 낮은 임계값
            logger.debug(f"  - 긴급성(>0.8) 조정: -0.3. 현재 임계값: {base_threshold:.3f}")
        elif urgency_level > 0.6:
            base_threshold -= 0.2  # 높은 긴급성
            logger.debug(f"  - 긴급성(>0.6) 조정: -0.2. 현재 임계값: {base_threshold:.3f}")
        elif urgency_level > 0.4:
            base_threshold -= 0.1  # 중간 긴급성
            logger.debug(f"  - 긴급성(>0.4) 조정: -0.1. 현재 임계값: {base_threshold:.3f}")
        
        # 시장 상황에 따른 조정
        if '불안정' in analysis_result or '변동성' in analysis_result:
            base_threshold -= 0.1
            logger.debug(f"  - 시장상황(불안정/변동성) 조정: -0.1. 현재 임계값: {base_threshold:.3f}")
        
        # 시간대에 따른 조정
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 15:  # 시장 개장 시간
            base_threshold -= 0.1
            logger.debug(f"  - 시간대(장중) 조정: -0.1. 현재 임계값: {base_threshold:.3f}")
        elif 15 < current_hour <= 18:  # 시장 마감 후
            base_threshold += 0.05
            logger.debug(f"  - 시간대(장마감) 조정: +0.05. 현재 임계값: {base_threshold:.3f}")
        
        # 요일에 따른 조정
        current_weekday = datetime.now().weekday()
        if current_weekday in [5, 6]:  # 주말
            base_threshold += 0.1
            logger.debug(f"  - 요일(주말) 조정: +0.1. 현재 임계값: {base_threshold:.3f}")
        
        
        # 최소/최대 임계값 보장
        final_threshold = max(0.3, min(0.9, base_threshold))
        logger.debug(f"최종 동적 임계값: {final_threshold:.3f}")
        return final_threshold
        
    except Exception as e:
        logger.error(f"❌ 단순화된 동적 임계값 계산 중 오류: {e}")
        return 0.7

def analyze_urgency_level(analysis_result: str) -> float:
    """
    긴급성 수준 분석 (가중치 기반)
    
    Args:
        analysis_result: 분석 결과
    
    Returns:
        긴급성 점수 (0.0 ~ 1.0)
    """
    try:
        urgency_keyword_weights = {
            # 높음 (3점) - 이 단어가 하나라도 있으면 높은 긴급성
            '긴급': 3, '즉시': 3, '당장': 3, '경고': 3,
            # 중간 (1점) - 상황을 주시해야 함
            '위험': 1, '주의': 1, '신중': 1, '변동성': 1, '급변': 1,
            # 낮음 (-1점) - 긴급성이 낮아짐
            '안정': -1, '유지': -1, '관망': -1, '평온': -1, '보유': -1
        }
        
        text_lower = analysis_result.lower()
        
        score = 0
        matched_keywords = []
        for keyword, weight in urgency_keyword_weights.items():
            if keyword in text_lower:
                score += weight
                matched_keywords.append(f"{keyword}({weight})")
        
        logger.debug(f"긴급성 분석: 매칭된 키워드: {', '.join(matched_keywords) if matched_keywords else '없음'}. 총점: {score}")

        # 점수 구간에 따라 최종 점수 반환
        if score >= 3:
            logger.debug("긴급성 최종 점수: 1.0 (높음)")
            return 1.0
        elif score >= 1:
            logger.debug("긴급성 최종 점수: 0.6 (중간)")
            return 0.6
        elif score < 0:
            logger.debug("긴급성 최종 점수: 0.2 (낮음)")
            return 0.2
        else: # score == 0
            logger.debug("긴급성 최종 점수: 0.5 (기본)")
            return 0.5
            
    except Exception as e:
        logger.error(f"❌ 긴급성 분석 중 오류: {e}")
        return 0.5

def get_user_customized_threshold(user_id: int, db) -> float:
    """
    사용자별 맞춤형 알림 임계값 계산
    
    Args:
        user_id: 사용자 ID
        db: 데이터베이스 세션
    
    Returns:
        사용자별 임계값
    """
    try:
        from crud.user import get_user_by_id
        from crud.notification import get_user_notification_history
        
        user = get_user_by_id(db, user_id)
        if not user or not user.settings:
            return 0.7  # 기본값
        
        # 사용자 위험도에 따른 기본 임계값 조정
        risk_level = user.settings.risk_level
        base_threshold = 0.7
        
        if risk_level <= 3:  # 보수적 투자자
            base_threshold += 0.1  # 더 높은 임계값 (적은 알림)
        elif risk_level >= 7:  # 공격적 투자자
            base_threshold -= 0.1  # 더 낮은 임계값 (많은 알림)
        
        # 사용자 알림 이력 분석
        notification_history = get_user_notification_history(db, user_id, limit=10)
        
        if notification_history:
            # 최근 알림 빈도 분석
            recent_notifications = len([n for n in notification_history if n.created_at > datetime.now() - timedelta(days=7)])
            
            if recent_notifications > 5:  # 일주일 내 5개 이상 알림
                base_threshold += 0.1  # 알림 빈도가 높으면 임계값 증가
            elif recent_notifications < 2:  # 일주일 내 2개 미만 알림
                base_threshold -= 0.05  # 알림 빈도가 낮으면 임계값 감소
        
        # 사용자 투자 패턴 분석
        investment_pattern = analyze_user_investment_pattern(user_id, db)
        
        if investment_pattern == 'frequent':
            base_threshold -= 0.05  # 자주 투자하는 사용자는 더 민감하게
        elif investment_pattern == 'conservative':
            base_threshold += 0.05  # 보수적 투자자는 덜 민감하게
        
        return max(0.3, min(0.9, base_threshold))
        
    except Exception as e:
        logger.error(f"❌ 사용자 맞춤형 임계값 계산 중 오류: {e}")
        return 0.7

def analyze_user_investment_pattern(user_id: int, db) -> str:
    """
    사용자 투자 패턴 분석
    
    Args:
        user_id: 사용자 ID
        db: 데이터베이스 세션
    
    Returns:
        투자 패턴 ('frequent', 'moderate', 'conservative')
    """
    try:
        from crud.etf import get_investment_etf_settings_by_user_id
        
        etf_settings = get_investment_etf_settings_by_user_id(db, user_id)
        
        if not etf_settings:
            return 'moderate'
        
        # 투자 주기 분석
        daily_count = sum(1 for setting in etf_settings if setting.cycle == 'daily')
        weekly_count = sum(1 for setting in etf_settings if setting.cycle == 'weekly')
        monthly_count = sum(1 for setting in etf_settings if setting.cycle == 'monthly')
        
        # 총 투자 금액 분석
        total_amount = sum(setting.amount for setting in etf_settings)
        
        # 패턴 분류
        if daily_count > 0 or (weekly_count > 2 and total_amount > 100):
            return 'frequent'  # 자주 투자하는 패턴
        elif monthly_count > 0 and total_amount < 50:
            return 'conservative'  # 보수적 투자 패턴
        else:
            return 'moderate'  # 보통 투자 패턴
            
    except Exception as e:
        logger.error(f"❌ 사용자 투자 패턴 분석 중 오류: {e}")
        return 'moderate'

def get_context_aware_threshold(
    analysis_result: str,
    user_id: int,
    etf_symbol: str,
    db
) -> float:
    """
    상황 인식 임계값 계산
    
    Args:
        analysis_result: 분석 결과
        user_id: 사용자 ID
        etf_symbol: ETF 심볼
        db: 데이터베이스 세션
    
    Returns:
        상황 인식 임계값
    """
    try:
        # 기본 사용자 맞춤형 임계값
        user_threshold = get_user_customized_threshold(user_id, db)
        
        # ETF별 특성에 따른 조정
        etf_adjustment = get_etf_specific_adjustment(etf_symbol)
        
        # 시장 상황에 따른 조정
        market_adjustment = get_market_situation_adjustment(analysis_result)
        
        # 시간대별 조정
        time_adjustment = get_time_based_adjustment()
        
        # 최종 임계값 계산
        final_threshold = user_threshold + etf_adjustment + market_adjustment + time_adjustment
        
        return max(0.3, min(0.9, final_threshold))
        
    except Exception as e:
        logger.error(f"❌ 상황 인식 임계값 계산 중 오류: {e}")
        return 0.7

def get_etf_specific_adjustment(etf_symbol: str) -> float:
    """ETF별 특성에 따른 임계값 조정"""
    try:
        # 변동성이 높은 ETF는 더 민감하게
        high_volatility_etfs = ['QQQ', 'TQQQ', 'SQQQ', 'VXX']
        low_volatility_etfs = ['BND', 'TLT', 'GLD', 'VNQ']
        
        if etf_symbol in high_volatility_etfs:
            return -0.1  # 낮은 임계값 (더 민감하게)
        elif etf_symbol in low_volatility_etfs:
            return 0.05  # 높은 임계값 (덜 민감하게)
        
        return 0.0
        
    except Exception as e:
        logger.error(f"❌ ETF별 조정 계산 중 오류: {e}")
        return 0.0

def get_market_situation_adjustment(analysis_result: str) -> float:
    """시장 상황에 따른 임계값 조정"""
    try:
        adjustment = 0.0
        
        # 긴급 상황 키워드
        urgent_keywords = ['긴급', '위험', '주의', '경고', '즉시']
        if any(keyword in analysis_result for keyword in urgent_keywords):
            adjustment -= 0.2
        
        # 안정적 상황 키워드
        stable_keywords = ['안정', '평온', '관망', '보수']
        if any(keyword in analysis_result for keyword in stable_keywords):
            adjustment += 0.1
        
        return adjustment
        
    except Exception as e:
        logger.error(f"❌ 시장 상황 조정 계산 중 오류: {e}")
        return 0.0

def get_time_based_adjustment() -> float:
    """시간대별 임계값 조정"""
    try:
        current_time = datetime.now()
        current_hour = current_time.hour
        current_weekday = current_time.weekday()
        
        adjustment = 0.0
        
        # 시장 개장 시간 (9-15시)
        if 9 <= current_hour <= 15:
            adjustment -= 0.1  # 시장 시간에는 더 민감하게
        
        # 시장 마감 후 (15-18시)
        elif 15 < current_hour <= 18:
            adjustment += 0.05  # 마감 후에는 덜 민감하게
        
        # 야간 시간 (18-9시)
        elif current_hour > 18 or current_hour < 9:
            adjustment += 0.1  # 야간에는 덜 민감하게
        
        # 주말
        if current_weekday in [5, 6]:  # 토, 일
            adjustment += 0.15  # 주말에는 훨씬 덜 민감하게
        
        return adjustment
        
    except Exception as e:
        logger.error(f"❌ 시간대별 조정 계산 중 오류: {e}")
        return 0.0

def extract_investment_amounts(text: str) -> list:
    """투자 금액 추출"""
    try:
        import re
        
        # 금액 패턴 매칭 (예: 100만원, 1,000,000원 등)
        amount_patterns = [
            r'(\d+(?:,\d{3})*)\s*만원',
            r'(\d+(?:,\d{3})*)\s*원',
            r'(\d+(?:,\d{3})*)\s*천원'
        ]
        
        amounts = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 쉼표 제거 후 숫자로 변환
                amount_str = match.replace(',', '')
                try:
                    amount = float(amount_str)
                    amounts.append(amount)
                except ValueError:
                    continue
        
        return amounts
        
    except Exception as e:
        logger.error(f"❌ 투자 금액 추출 중 오류: {e}")
        return []

def extract_recommendation(analysis_result: str) -> str:
    """AI 분석 결과에서 추천사항 추출"""
    try:
        # 간단한 추천사항 추출 로직
        lines = analysis_result.split('\n')
        for line in lines:
            if any(word in line for word in ["추천", "권장", "제안", "조정", "변경", "매수", "매도"]):
                return line.strip()
        
        # 추천 키워드가 없으면 전체 결과 반환 (길이 제한)
        if len(analysis_result) > 200:
            return analysis_result[:200] + "..."
        return analysis_result
        
    except Exception as e:
        logger.error(f"❌ 추천사항 추출 중 오류: {e}")
        return "AI 분석 결과를 확인해주세요."

def extract_confidence_score(analysis_result: str) -> float:
    """AI 분석 결과에서 신뢰도 점수 추출 (0.0 ~ 1.0)"""
    try:
        # 간단한 신뢰도 계산 로직
        confidence_score = 0.5  # 기본값
        
        # 분석 결과의 길이와 내용을 바탕으로 신뢰도 조정
        if len(analysis_result) > 100:
            confidence_score += 0.2
        
        if any(word in analysis_result for word in ["분석", "데이터", "정보"]):
            confidence_score += 0.1
        
        if any(word in analysis_result for word in ["확실", "명확", "분명"]):
            confidence_score += 0.1
        
        return min(confidence_score, 1.0)
        
    except Exception as e:
        logger.error(f"❌ 신뢰도 점수 추출 중 오류: {e}")
        return 0.5  # 기본값 반환

def save_analysis_result(user_id: int, etf_symbol: str, analysis_result: str, db) -> bool:
    """
    분석 결과를 임시 저장 (선택사항)
    
    Args:
        user_id: 사용자 ID
        etf_symbol: ETF 심볼 또는 포트폴리오 키
        analysis_result: 분석 결과
        db: 데이터베이스 세션
    
    Returns:
        저장 성공 여부
    """
    try:
        # 여기서는 로그만 남기고, 필요시 별도의 분석 결과 테이블을 만들 수 있음
        logger.info(f"💾 {user_id} 사용자의 {etf_symbol} 분석 결과 저장됨")
        return True
        
    except Exception as e:
        logger.error(f"❌ 분석 결과 저장 중 오류: {e}")
        return False