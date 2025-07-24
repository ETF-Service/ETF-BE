"""
AI 분석 서비스
ETF_AI 모듈과 연동하여 투자 결정을 분석하고 알림 여부를 결정
"""

import httpx
import logging
from typing import Dict, Optional
from datetime import datetime
import json

from config.notification_config import get_ai_analysis_threshold
from models.user import InvestmentSettings, User
from models.etf import InvestmentETFSettings, ETF

logger = logging.getLogger(__name__)

import os

# ETF_AI 서비스 URL (환경 변수에서 가져오거나 기본값 사용)
AI_SERVICE_URL = os.getenv("ETF_AI_SERVICE_URL", "http://localhost:8001")
MAX_RETRIES = int(os.getenv("AI_SERVICE_MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("AI_SERVICE_RETRY_DELAY", "5"))

async def analyze_investment_decision(
    user: User,
    user_setting: InvestmentSettings,
    etf_setting: InvestmentETFSettings,
    etf: ETF,
    previous_analysis: str = None
) -> Optional[Dict]:
    """
    AI 분석을 통한 투자 결정 분석
    
    Args:
        user: 사용자 정보
        user_setting: 사용자 투자 설정
        etf_setting: ETF 투자 설정
        etf: ETF 정보
        previous_analysis: 이전 분석 결과 (선택사항)
    
    Returns:
        분석 결과 딕셔너리 또는 None
    """
    try:
        logger.info(f"🤖 {user.name}님의 {etf.symbol} ETF AI 분석 시작...")
        
        # AI 분석 요청 메시지 구성
        analysis_messages = create_analysis_messages(
            user, user_setting, etf_setting, etf
        )
        
        # ETF_AI 서비스에 분석 요청
        analysis_result = await request_ai_analysis(
            analysis_messages, 
            user_setting.api_key, 
            user_setting.model_type
        )
        
        if not analysis_result:
            logger.warning(f"⚠️ AI 분석 결과가 없습니다: {etf.symbol}")
            return None
        
        logger.info(f"📊 {user.name}님의 {etf.symbol} ETF AI 분석 완료")
        
        # 분석 결과에서 투자 변경 필요성 판단 (이전 분석과 비교)
        should_notify = determine_notification_need(analysis_result, previous_analysis)
        
        # 추천사항 및 신뢰도 추출
        recommendation = extract_recommendation(analysis_result)
        confidence_score = extract_confidence_score(analysis_result)
        
        result = {
            'should_notify': should_notify,
            'analysis_result': analysis_result,
            'recommendation': recommendation,
            'confidence_score': confidence_score,
            'analyzed_at': datetime.now().isoformat(),
            'etf_symbol': etf.symbol,
            'user_id': user.id
        }
        
        logger.info(f"✅ {user.name}님의 {etf.symbol} ETF 분석 결과: 알림 전송 {'예정' if should_notify else '불필요'}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ {user.name}님의 {etf.symbol} ETF AI 분석 중 오류 발생: {e}")
        return None

def create_analysis_messages(
    user: User,
    user_setting: InvestmentSettings,
    etf_setting: InvestmentETFSettings,
    etf: ETF
) -> list:
    """AI 분석 요청 메시지 생성 - analyze_instructions 함수 사용"""
    
    # 사용자 정보
    user_name = user.name
    invest_type = user_setting.risk_level
    interest = user_setting.persona or "ETF 투자"
    invest_price = etf_setting.amount
    invest_infos = f"{etf.symbol}: {etf.name}"
    
    # 오늘 날짜 정보
    today = datetime.now().strftime("%Y-%m-%d")
    today_ETF = etf.symbol
    today_ETF_invest_price = etf_setting.amount
    
    # analyze_instructions 스타일로 developer 메시지 생성
    today_date = f"{datetime.now().year}년 {datetime.now().month}월 {datetime.now().day}일"
    
    developer_content = f"너의 이름은 금융 Agent야. 사용자를 '{user_name} 고객님'이라고 불러야 해.\
    너가 해야하는 업무는 사용자의 성향과 최근 뉴스 및 한국 은행에서 제공하는 해외 동향분석, 현지정보 자료를 기반으로 상품마다 투자하기 전에 '{user_name} 고객님, OOO상품을 곧 투자할 예정인데 이 상품의 앞으로의 전망이 이러니 투자 비중을 기존보다 10% 인상하는게 좋겠다.'라고 말해줘야해.\
    오늘 날짜는 {today_date}야.\
    사용자의 투자 성향은 0(보수적) ~ 10(공격적)이라고 할 때, {invest_type}이야.\
    사용자가 현재 투자하고 있는 ETF 및 그에 대한 정보는 {invest_infos}야."
    
    messages = [
        {
            "role": "developer",
            "content": developer_content
        },
        {
            "role": "user",
            "content": f"네이버 글로벌 경제 뉴스, 네이버 한국 경제 뉴스, 한국은행에서 제공하는 정보 3가지를 모두 분석해줘.\
                        오늘 나는 {today_ETF} ETF에 각각 {today_ETF_invest_price}만원씩 투자하는 날이야. 이중에서 투자 비율을 조정해야 하는 것이 있어?\
                        요약만 간결하게 해서 상품에 투자 비중을 정해서 최종 금액을 도출해줘."
        }
    ]
    
    return messages

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
                        logger.info(f"✅ AI 분석 성공 (시도 {attempt + 1})")
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

def determine_notification_need(analysis_result: str, previous_analysis: str = None) -> bool:
    """
    AI 분석 결과를 바탕으로 알림 전송 여부 결정
    코사인 유사도 기반으로 이전 분석과 비교하여 변화 감지
    
    Args:
        analysis_result: AI 분석 결과 텍스트
        previous_analysis: 이전 분석 결과 텍스트 (선택사항)
    
    Returns:
        알림 전송 여부 (True/False)
    """
    try:
        # 이전 분석이 있는 경우 코사인 유사도 기반 판단
        if previous_analysis:
            similarity = calculate_cosine_similarity(previous_analysis, analysis_result)
            similarity_threshold = 0.45  # ETF_AI와 동일한 임계값
            
            should_notify = similarity < similarity_threshold
            
            logger.info(f"📊 코사인 유사도: {similarity:.3f}, 임계값: {similarity_threshold}, 알림 전송: {should_notify}")
            
            return should_notify
        
        # 이전 분석이 없는 경우 키워드 기반 판단 (기존 방식)
        threshold = get_ai_analysis_threshold()
        
        # 분석 결과에서 투자 변경 필요성 키워드 확인
        change_keywords = [
            "조정", "변경", "수정", "조정해야", "변경해야", "수정해야",
            "비중 조정", "투자 비율 조정", "금액 조정",
            "추가 투자", "투자 금액 증가", "투자 금액 감소",
            "권장", "추천", "제안"
        ]
        
        # 분석 결과에서 변경 필요성 점수 계산
        change_score = 0.0
        
        for keyword in change_keywords:
            if keyword in analysis_result:
                change_score += 0.1  # 각 키워드당 0.1점
        
        # 금액 변경이 언급된 경우 추가 점수
        if any(word in analysis_result for word in ["원", "금액", "투자액"]):
            change_score += 0.2
        
        # 비중 조정이 언급된 경우 추가 점수
        if any(word in analysis_result for word in ["비중", "비율", "%"]):
            change_score += 0.3
        
        # 임계값과 비교
        should_notify = change_score >= threshold
        
        logger.info(f"📊 키워드 기반 점수: {change_score:.2f}, 임계값: {threshold}, 알림 전송: {should_notify}")
        
        return should_notify
        
    except Exception as e:
        logger.error(f"❌ 알림 필요성 판단 중 오류: {e}")
        return False  # 오류 시 알림 전송하지 않음

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
        from crud.notification import get_user_notifications_by_type
        from config.notification_config import NOTIFICATION_TYPES
        
        # 최근 AI 분석 알림 조회
        notifications = get_user_notifications_by_type(
            db, user_id, NOTIFICATION_TYPES['AI_ANALYSIS'], limit=1
        )
        
        if notifications:
            # 알림 내용에서 분석 결과 추출
            content = notifications[0].content
            # "추천사항:" 이후 부분이 분석 결과일 가능성이 높음
            if "추천사항:" in content:
                return content.split("추천사항:")[0].strip()
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