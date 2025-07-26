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
    market_news: str = None
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
        # 3. 시장 뉴스
        news_info = f"[시장 뉴스]\n{market_news}" if market_news else "[시장 뉴스]\n(최신 뉴스 데이터 없음)"
        # 4. 분석 기준/목표
        analysis_criteria = (
            "[분석 기준]\n"
            "- 시장 변동성이 20% 이상이거나, 사용자 위험 성향이 8 이상일 때만 비중 조정 권고\n"
            "- ETF별로 조정 사유와 권장 비중을 명확히 제시\n"
            "- 투자 금액, 주기, 시장 상황, 사용자 성향을 모두 고려\n"
            "- 불필요한 조정은 피하고, 반드시 조정이 필요한 경우만 권고\n"
        )
        # 5. 예시 답변 포맷
        example_format = (
            "[분석 결과 예시]\n"
            "- SPY: 비중 유지 (시장 안정, 추가 매수 불필요)\n"
            "- QQQ: 비중 10% 증가 권고 (기술주 강세, 성장 기대)\n"
            "- 종합 의견: 전체 포트폴리오의 위험도는 적정 수준, 추가 리밸런싱 필요 없음\n"
        )
        # 6. 오늘 날짜
        today_date = f"[분석 기준일] {datetime.now().year}년 {datetime.now().month}월 {datetime.now().day}일"
        # 7. 최종 developer 메시지 조립
        developer_content = (
            f"""
{user_info}\n\n{etf_info}\n\n{news_info}\n\n{analysis_criteria}\n{example_format}\n{today_date}\n\n위 정보를 바탕으로 오늘의 투자 조언을 위 예시 포맷에 맞춰 작성해줘.\nETF별로 조정이 필요한 경우 그 이유를 반드시 명확히 설명하고, 종합 의견도 꼭 포함해줘.\n답변은 반드시 [분석 결과 예시] 포맷을 따라줘.
"""
        )
        # 8. user 메시지(명령)
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

def determine_notification_need(analysis_result: str, previous_analysis: str = None) -> bool:
    """
    다차원 분석과 ML 분류기를 통합한 알림 필요성 판단
    
    Args:
        analysis_result: 현재 AI 분석 결과
        previous_analysis: 이전 AI 분석 결과
    
    Returns:
        알림 전송 여부
    """
    try:
        # 1. 기본 텍스트 유사도 분석
        text_similarity = calculate_cosine_similarity(analysis_result, previous_analysis) if previous_analysis else 0.0
        
        # 2. 투자 권장사항 변화 분석
        recommendation_change = analyze_recommendation_change(analysis_result, previous_analysis)
        
        # 3. 위험도 변화 분석
        risk_change = analyze_risk_change(analysis_result, previous_analysis)
        
        # 4. 투자 금액 변화 분석
        amount_change = analyze_investment_amount_change(analysis_result, previous_analysis)
        
        # 5. 시장 상황 변화 분석
        market_change = analyze_market_situation_change(analysis_result, previous_analysis)
        
        # 6. 감정 변화 분석 (선택적)
        sentiment_change = analyze_sentiment_change(analysis_result, previous_analysis)
        
        # 7. 긴급성 수준 분석
        urgency_level = analyze_urgency_level(analysis_result)
        
        # 8. ML 분류기 분석 (선택적)
        ml_score = analyze_with_ml_classifier(analysis_result, previous_analysis)
        
        # 9. 종합 점수 계산 (개선된 가중치)
        notification_score = calculate_enhanced_notification_score(
            text_similarity=text_similarity,
            recommendation_change=recommendation_change,
            risk_change=risk_change,
            amount_change=amount_change,
            market_change=market_change,
            sentiment_change=sentiment_change,
            urgency_level=urgency_level,
            ml_score=ml_score
        )
        
        # 10. 동적 임계값 적용
        dynamic_threshold = get_enhanced_dynamic_threshold(
            analysis_result, 
            urgency_level, 
            market_change
        )
        
        should_notify = notification_score > dynamic_threshold
        
        # 상세 로깅
        logger.info(f"📊 개선된 알림 판단 결과:")
        logger.info(f"   - 텍스트 유사도: {text_similarity:.3f}")
        logger.info(f"   - 권장사항 변화: {recommendation_change:.3f}")
        logger.info(f"   - 위험도 변화: {risk_change:.3f}")
        logger.info(f"   - 투자금액 변화: {amount_change:.3f}")
        logger.info(f"   - 시장상황 변화: {market_change:.3f}")
        logger.info(f"   - 감정 변화: {sentiment_change:.3f}")
        logger.info(f"   - 긴급성 수준: {urgency_level:.3f}")
        logger.info(f"   - ML 분류기 점수: {ml_score:.3f}")
        logger.info(f"   - 종합 점수: {notification_score:.3f}")
        logger.info(f"   - 동적 임계값: {dynamic_threshold:.3f}")
        logger.info(f"   - 알림 전송: {'예' if should_notify else '아니오'}")
        
        return should_notify
        
    except Exception as e:
        logger.error(f"❌ 개선된 알림 판단 중 오류: {e}")
        return True  # 오류 시 안전하게 알림 전송

def analyze_recommendation_change(current: str, previous: str = None) -> float:
    """투자 권장사항 변화 분석"""
    try:
        if not previous:
            return 1.0  # 이전 데이터가 없으면 최대 변화로 간주
        
        # 권장사항 키워드 추출
        current_recommendation = extract_recommendation(current)
        previous_recommendation = extract_recommendation(previous)
        
        # 권장사항 변화 패턴 분석
        change_patterns = {
            '매수': ['매수', '증가', '상향', '추천'],
            '매도': ['매도', '감소', '하향', '회수'],
            '유지': ['유지', '보유', '현상유지', '관망'],
            '중립': ['중립', '보수', '신중']
        }
        
        current_action = classify_recommendation_action(current_recommendation, change_patterns)
        previous_action = classify_recommendation_action(previous_recommendation, change_patterns)
        
        # 액션 변화에 따른 점수 계산
        if current_action != previous_action:
            return 1.0  # 액션이 바뀌면 최대 변화
        elif current_action in ['매수', '매도']:
            return 0.8  # 적극적 액션은 높은 변화도
        else:
            return 0.3  # 보수적 액션은 낮은 변화도
            
    except Exception as e:
        logger.error(f"❌ 권장사항 변화 분석 중 오류: {e}")
        return 0.5

def analyze_risk_change(current: str, previous: str = None) -> float:
    """위험도 변화 분석"""
    try:
        if not previous:
            return 0.5
        
        # 위험도 관련 키워드 추출
        risk_keywords = {
            'high_risk': ['높은 위험', '위험도 증가', '불안정', '변동성 증가'],
            'low_risk': ['낮은 위험', '안정적', '보수적', '안전'],
            'medium_risk': ['보통 위험', '중간', '적당한']
        }
        
        current_risk = extract_risk_level(current, risk_keywords)
        previous_risk = extract_risk_level(previous, risk_keywords)
        
        # 위험도 변화 계산
        risk_change = abs(current_risk - previous_risk)
        
        # 위험도 변화가 클수록 높은 점수
        return min(risk_change * 2, 1.0)
        
    except Exception as e:
        logger.error(f"❌ 위험도 변화 분석 중 오류: {e}")
        return 0.5

def analyze_investment_amount_change(current: str, previous: str = None) -> float:
    """투자 금액 변화 분석"""
    try:
        if not previous:
            return 0.5
        
        # 금액 관련 정보 추출
        current_amounts = extract_investment_amounts(current)
        previous_amounts = extract_investment_amounts(previous)
        
        if not current_amounts or not previous_amounts:
            return 0.5
        
        # 평균 금액 변화율 계산
        current_avg = sum(current_amounts) / len(current_amounts)
        previous_avg = sum(previous_amounts) / len(previous_amounts)
        
        if previous_avg == 0:
            return 0.5
        
        change_ratio = abs(current_avg - previous_avg) / previous_avg
        
        # 변화율에 따른 점수 (20% 이상 변화 시 높은 점수)
        if change_ratio > 0.2:
            return 1.0
        elif change_ratio > 0.1:
            return 0.7
        else:
            return 0.3
            
    except Exception as e:
        logger.error(f"❌ 투자 금액 변화 분석 중 오류: {e}")
        return 0.5

def analyze_market_situation_change(current: str, previous: str = None) -> float:
    """시장 상황 변화 분석"""
    try:
        if not previous:
            return 0.5
        
        # 시장 상황 키워드 추출
        market_keywords = {
            'bull_market': ['상승장', '호황', '긍정적', '기회'],
            'bear_market': ['하락장', '침체', '부정적', '위험'],
            'volatile': ['변동성', '불안정', '급변', '예측불가'],
            'stable': ['안정', '평온', '예측가능', '일정']
        }
        
        current_market = classify_market_situation(current, market_keywords)
        previous_market = classify_market_situation(previous, market_keywords)
        
        # 시장 상황 변화에 따른 점수
        if current_market != previous_market:
            return 1.0  # 시장 상황이 바뀌면 최대 변화
        elif current_market in ['volatile', 'bear_market']:
            return 0.8  # 불안정한 시장은 높은 변화도
        else:
            return 0.4  # 안정적인 시장은 낮은 변화도
            
    except Exception as e:
        logger.error(f"❌ 시장 상황 변화 분석 중 오류: {e}")
        return 0.5

def calculate_notification_score(
    text_similarity: float,
    recommendation_change: float,
    risk_change: float,
    amount_change: float,
    market_change: float
) -> float:
    """종합 알림 점수 계산"""
    try:
        # 가중치 설정 (중요도에 따라 조정 가능)
        weights = {
            'text_similarity': 0.2,      # 텍스트 유사도
            'recommendation_change': 0.3, # 권장사항 변화 (가장 중요)
            'risk_change': 0.2,          # 위험도 변화
            'amount_change': 0.15,       # 투자 금액 변화
            'market_change': 0.15        # 시장 상황 변화
        }
        
        # 가중 평균 계산
        weighted_score = (
            (1 - text_similarity) * weights['text_similarity'] +
            recommendation_change * weights['recommendation_change'] +
            risk_change * weights['risk_change'] +
            amount_change * weights['amount_change'] +
            market_change * weights['market_change']
        )
        
        return min(weighted_score, 1.0)
        
    except Exception as e:
        logger.error(f"❌ 알림 점수 계산 중 오류: {e}")
        return 0.5

def get_dynamic_threshold(analysis_result: str) -> float:
    """동적 임계값 계산"""
    try:
        base_threshold = 0.7
        
        # 시장 상황에 따른 임계값 조정
        if '긴급' in analysis_result or '위험' in analysis_result:
            return base_threshold - 0.2  # 긴급 상황은 낮은 임계값
        elif '안정' in analysis_result or '관망' in analysis_result:
            return base_threshold + 0.1  # 안정적 상황은 높은 임계값
        
        # 시간대에 따른 조정 (시장 개장 시간 등)
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 15:  # 시장 개장 시간
            return base_threshold - 0.1  # 시장 시간에는 더 민감하게
        
        return base_threshold
        
    except Exception as e:
        logger.error(f"❌ 동적 임계값 계산 중 오류: {e}")
        return 0.7

def classify_recommendation_action(recommendation: str, patterns: dict) -> str:
    """권장사항을 액션으로 분류"""
    try:
        recommendation_lower = recommendation.lower()
        
        for action, keywords in patterns.items():
            if any(keyword in recommendation_lower for keyword in keywords):
                return action
        
        return '중립'  # 기본값
        
    except Exception as e:
        logger.error(f"❌ 권장사항 분류 중 오류: {e}")
        return '중립'

def extract_risk_level(text: str, risk_keywords: dict) -> float:
    """위험도 수준 추출 (0.0 ~ 1.0)"""
    try:
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in risk_keywords['high_risk']):
            return 0.8
        elif any(keyword in text_lower for keyword in risk_keywords['low_risk']):
            return 0.2
        elif any(keyword in text_lower for keyword in risk_keywords['medium_risk']):
            return 0.5
        
        return 0.5  # 기본값
        
    except Exception as e:
        logger.error(f"❌ 위험도 추출 중 오류: {e}")
        return 0.5

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

def classify_market_situation(text: str, market_keywords: dict) -> str:
    """시장 상황 분류"""
    try:
        text_lower = text.lower()
        
        for situation, keywords in market_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return situation
        
        return 'stable'  # 기본값
        
    except Exception as e:
        logger.error(f"❌ 시장 상황 분류 중 오류: {e}")
        return 'stable'

def calculate_cosine_similarity(text1: str, text2: str) -> float:
    """
    두 텍스트 간의 코사인 유사도 계산
    ETF_AI와 동일한 SentenceTransformer 모델 사용
    """
    try:
        # SentenceTransformer 모델 사용 (ETF_AI와 동일)
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        
        # 모델 로드 (캐싱을 위해 전역 변수로 관리)
        if not hasattr(calculate_cosine_similarity, 'model'):
            logger.info("🤖 SentenceTransformer 모델 로딩 중...")
            calculate_cosine_similarity.model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
            logger.info("✅ SentenceTransformer 모델 로딩 완료")
        
        model = calculate_cosine_similarity.model
        
        # 각 문장 인코딩
        sent1_encode = model.encode([text1])
        sent2_encode = model.encode([text2])
        
        # 코사인 유사도 계산
        similarity = cosine_similarity(sent1_encode, sent2_encode)
        
        result = similarity[0][0]
        logger.debug(f"📊 코사인 유사도: {result:.3f}")
        
        return result
        
    except ImportError:
        logger.error("❌ SentenceTransformer가 설치되지 않음. 코사인 유사도 계산 불가")
        return 0.0
        
    except Exception as e:
        logger.error(f"❌ 코사인 유사도 계산 중 오류: {e}")
        return 0.0  # 오류 시 0 반환

def extract_recommendation(analysis_result: str) -> str:
    """AI 분석 결과에서 추천사항 추출"""
    try:
        # 간단한 추천사항 추출 로직
        lines = analysis_result.split('\n')
        for line in lines:
            if any(word in line for word in ["추천", "권장", "제안", "조정", "변경"]):
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

def get_previous_analysis(user_id: int, etf_symbol: str, db) -> Optional[str]:
    """
    사용자의 이전 분석 결과 조회
    
    Args:
        user_id: 사용자 ID
        etf_symbol: ETF 심볼
        db: 데이터베이스 세션
    
    Returns:
        이전 분석 결과 또는 None
    """
    try:
        # 최근 AI 분석 알림 조회
        notifications = get_notifications_by_user_id_and_type(
            db, user_id, NOTIFICATION_TYPES['AI_ANALYSIS'], limit=1
        )
        
        if notifications:
            # 알림 내용에서 분석 결과 추출
            content = notifications[0].content
            return content
        
        return None
        
    except Exception as e:
        logger.error(f"❌ 이전 분석 결과 조회 중 오류: {e}")
        return None

def save_analysis_result(user_id: int, etf_symbol: str, analysis_result: str, db) -> bool:
    """
    분석 결과를 임시 저장 (선택사항)
    
    Args:
        user_id: 사용자 ID
        etf_symbol: ETF 심볼
        analysis_result: 분석 결과
        db: 데이터베이스 세션
    
    Returns:
        저장 성공 여부
    """
    try:
        # 여기서는 알림 테이블에 저장하지만, 
        # 필요시 별도의 분석 결과 테이블을 만들 수 있음
        logger.info(f"💾 {user_id} 사용자의 {etf_symbol} 분석 결과 저장됨")
        return True
        
    except Exception as e:
        logger.error(f"❌ 분석 결과 저장 중 오류: {e}")
        return False

def analyze_with_ml_classifier(analysis_result: str, previous_analysis: str = None) -> float:
    """
    머신러닝 기반 분류기를 사용한 알림 필요성 분석
    
    Args:
        analysis_result: 현재 분석 결과
        previous_analysis: 이전 분석 결과
    
    Returns:
        ML 분류기 점수 (0.0 ~ 1.0)
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.ensemble import RandomForestClassifier
        import pickle
        import os
        
        # ML 모델 파일 경로
        model_path = "models/notification_classifier.pkl"
        vectorizer_path = "models/notification_vectorizer.pkl"
        
        # 모델이 존재하는지 확인
        if not os.path.exists(model_path) or not os.path.exists(vectorizer_path):
            logger.warning("ML 모델이 없습니다. 기본 분석을 사용합니다.")
            return 0.5
        
        # 모델 로드
        with open(model_path, 'rb') as f:
            classifier = pickle.load(f)
        
        with open(vectorizer_path, 'rb') as f:
            vectorizer = pickle.load(f)
        
        # 텍스트 전처리
        combined_text = analysis_result
        if previous_analysis:
            combined_text += " " + previous_analysis
        
        # 특성 추출
        features = vectorizer.transform([combined_text])
        
        # 예측
        prediction = classifier.predict_proba(features)[0]
        
        # 알림 필요성 확률 반환 (클래스 1의 확률)
        return prediction[1] if len(prediction) > 1 else prediction[0]
        
    except Exception as e:
        logger.error(f"❌ ML 분류기 분석 중 오류: {e}")
        return 0.5

def train_notification_classifier(training_data: list):
    """
    알림 필요성 분류기 훈련
    
    Args:
        training_data: [(text, label), ...] 형태의 훈련 데이터
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report
        import pickle
        import os
        
        # 데이터 분리
        texts = [item[0] for item in training_data]
        labels = [item[1] for item in training_data]
        
        # 특성 추출
        vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            stop_words=None,
            min_df=2
        )
        
        X = vectorizer.fit_transform(texts)
        
        # 훈련/테스트 분리
        X_train, X_test, y_train, y_test = train_test_split(
            X, labels, test_size=0.2, random_state=42
        )
        
        # 모델 훈련
        classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        classifier.fit(X_train, y_train)
        
        # 성능 평가
        y_pred = classifier.predict(X_test)
        report = classification_report(y_test, y_pred)
        logger.info(f"ML 분류기 성능:\n{report}")
        
        # 모델 저장
        os.makedirs("models", exist_ok=True)
        
        with open("models/notification_classifier.pkl", 'wb') as f:
            pickle.dump(classifier, f)
        
        with open("models/notification_vectorizer.pkl", 'wb') as f:
            pickle.dump(vectorizer, f)
        
        logger.info("✅ ML 분류기 훈련 및 저장 완료")
        
    except Exception as e:
        logger.error(f"❌ ML 분류기 훈련 중 오류: {e}")

def analyze_sentiment_change(current: str, previous: str = None) -> float:
    """
    감정 분석을 통한 변화 감지
    
    Args:
        current: 현재 분석 결과
        previous: 이전 분석 결과
    
    Returns:
        감정 변화 점수 (0.0 ~ 1.0)
    """
    try:
        from textblob import TextBlob
        
        # 감정 점수 계산
        current_sentiment = TextBlob(current).sentiment.polarity
        previous_sentiment = TextBlob(previous).sentiment.polarity if previous else 0.0
        
        # 감정 변화의 절댓값
        sentiment_change = abs(current_sentiment - previous_sentiment)
        
        # 감정 변화가 클수록 높은 점수 (0.5 이상 변화 시 높은 점수)
        if sentiment_change > 0.5:
            return 1.0
        elif sentiment_change > 0.3:
            return 0.7
        elif sentiment_change > 0.1:
            return 0.4
        else:
            return 0.2
            
    except ImportError:
        logger.warning("TextBlob이 설치되지 않았습니다. 감정 분석을 건너뜁니다.")
        return 0.5
    except Exception as e:
        logger.error(f"❌ 감정 분석 중 오류: {e}")
        return 0.5

def analyze_urgency_level(analysis_result: str) -> float:
    """
    긴급성 수준 분석
    
    Args:
        analysis_result: 분석 결과
    
    Returns:
        긴급성 점수 (0.0 ~ 1.0)
    """
    try:
        urgency_keywords = {
            'high': ['긴급', '즉시', '당장', '위험', '주의', '경고'],
            'medium': ['신중', '관망', '보수', '점진적'],
            'low': ['안정', '평온', '일정', '예측가능']
        }
        
        text_lower = analysis_result.lower()
        
        # 긴급성 키워드 매칭
        urgency_scores = {
            'high': sum(1 for keyword in urgency_keywords['high'] if keyword in text_lower),
            'medium': sum(1 for keyword in urgency_keywords['medium'] if keyword in text_lower),
            'low': sum(1 for keyword in urgency_keywords['low'] if keyword in text_lower)
        }
        
        # 긴급성 점수 계산
        if urgency_scores['high'] > 0:
            return 1.0
        elif urgency_scores['medium'] > 0:
            return 0.6
        elif urgency_scores['low'] > 0:
            return 0.2
        else:
            return 0.5
            
    except Exception as e:
        logger.error(f"❌ 긴급성 분석 중 오류: {e}")
        return 0.5

def calculate_enhanced_notification_score(
    text_similarity: float,
    recommendation_change: float,
    risk_change: float,
    amount_change: float,
    market_change: float,
    sentiment_change: float,
    urgency_level: float,
    ml_score: float
) -> float:
    """개선된 종합 알림 점수 계산"""
    try:
        # 가중치 설정 (중요도와 신뢰도에 따라 조정)
        weights = {
            'text_similarity': 0.15,     # 텍스트 유사도
            'recommendation_change': 0.25, # 권장사항 변화 (가장 중요)
            'risk_change': 0.15,         # 위험도 변화
            'amount_change': 0.10,       # 투자 금액 변화
            'market_change': 0.10,       # 시장 상황 변화
            'sentiment_change': 0.05,    # 감정 변화
            'urgency_level': 0.10,       # 긴급성 수준
            'ml_score': 0.10            # ML 분류기 점수
        }
        
        # 가중 평균 계산
        weighted_score = (
            (1 - text_similarity) * weights['text_similarity'] +
            recommendation_change * weights['recommendation_change'] +
            risk_change * weights['risk_change'] +
            amount_change * weights['amount_change'] +
            market_change * weights['market_change'] +
            sentiment_change * weights['sentiment_change'] +
            urgency_level * weights['urgency_level'] +
            ml_score * weights['ml_score']
        )
        
        return min(weighted_score, 1.0)
        
    except Exception as e:
        logger.error(f"❌ 개선된 알림 점수 계산 중 오류: {e}")
        return 0.5

def get_enhanced_dynamic_threshold(
    analysis_result: str, 
    urgency_level: float, 
    market_change: float
) -> float:
    """개선된 동적 임계값 계산"""
    try:
        base_threshold = 0.7
        
        # 긴급성에 따른 임계값 조정
        if urgency_level > 0.8:
            base_threshold -= 0.3  # 긴급 상황은 매우 낮은 임계값
        elif urgency_level > 0.6:
            base_threshold -= 0.2  # 높은 긴급성
        elif urgency_level > 0.4:
            base_threshold -= 0.1  # 중간 긴급성
        
        # 시장 상황에 따른 조정
        if market_change > 0.8:
            base_threshold -= 0.2  # 시장 급변 시 낮은 임계값
        elif '불안정' in analysis_result or '변동성' in analysis_result:
            base_threshold -= 0.1
        
        # 시간대에 따른 조정
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 15:  # 시장 개장 시간
            base_threshold -= 0.1
        elif 15 < current_hour <= 18:  # 시장 마감 후
            base_threshold += 0.05
        
        # 요일에 따른 조정
        current_weekday = datetime.now().weekday()
        if current_weekday in [5, 6]:  # 주말
            base_threshold += 0.1  # 주말에는 훨씬 덜 민감하게
        
        # 최소/최대 임계값 보장
        return max(0.3, min(0.9, base_threshold))
        
    except Exception as e:
        logger.error(f"❌ 개선된 동적 임계값 계산 중 오류: {e}")
        return 0.7

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