"""
AI 분석 서비스
ETF_AI 모듈과 연동하여 투자 결정을 분석하고 알림 여부를 결정
"""

import httpx
import logging
from typing import Dict, Optional
from datetime import datetime
import json
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from config.notification_config import NOTIFICATION_TYPES
from models import User, InvestmentSettings
from crud.notification import get_notifications_by_user_id_and_type
from crud.user import update_user_investment_settings # crud 추가

logger = logging.getLogger(__name__)

import os

# ETF_AI 서비스 URL (환경 변수에서 가져오거나 기본값 사용)
AI_SERVICE_URL = os.getenv("ETF_AI_SERVICE_URL", "http://localhost:8001")
MAX_RETRIES = int(os.getenv("AI_SERVICE_MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("AI_SERVICE_RETRY_DELAY", "5"))

# 문장 임베딩 모델 로드
try:
    embedding_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
    logger.info("✅ Sentence Transformer 모델 로드 성공")
except Exception as e:
    embedding_model = None
    logger.error(f"❌ Sentence Transformer 모델 로드 실패: {e}")

def create_integrated_analysis_messages(
    user: User,
    user_setting: InvestmentSettings,
    etf_data_list: list,
) -> list:
    """
    사용자의 모든 ETF를 포함한 통합 분석 메시지 생성 (구조적/구체적 프롬프트)
    """
    try:
        # 1. 사용자 정보
        user_info = f"""[사용자 정보]\n- 이름: {user.name}\n- 위험 성향(0~10): {user_setting.risk_level}\n- 투자 목표/페르소나: {user_setting.persona or '미입력'}"""
        
        # 2. ETF 정보
        etf_info = "[보유 ETF 목록]\n" + "\n".join([
            f"- {etf_data['etf'].symbol}: {etf_data['etf_setting'].amount:,}만원, 주기: {etf_data['etf_setting'].cycle}, 이름: {etf_data['etf'].name}"
            for etf_data in etf_data_list
        ])
        
        # 3. 새로운 출력 포맷 및 규칙
        output_format_and_rules = (
            "[출력 포맷]\n"
            "### ETF 분석 결과\n\n"
            "#### SPY (미국 S&P500)\n"
            "- **권고 사항**: 비중 유지 (시장 안정, 추가 매수 불필요)\n"
            "- **이유**: ECB의 주요 정책금리 동결로 인한 글로벌 금융시장의 안정세가 유지되고 있습니다.\n\n"
            "#### QQQ (미국 나스닥)\n"
            "- **권고 사항**: 비중 10% 증가 권고 (기술주 강세, 성장 기대)\n"
            "- **이유**: 기술주 중심의 나스닥 시장은 최근 긍정적인 경제 신호들로 강세를 보입니다.\n\n"
            "### 종합 의견:\n"
            "이번 주는 전반적으로 안정된 시장 모습을 보였습니다. 현 상황에서는 점진적이고 안정적인 접근이 필요합니다.\n"
            "\n"
            "[규칙]\n"
            "1. 응답은 반드시 제공한 모든 ETF 목록을 분석한 후에, 위의 [출력 포맷]을 정확하게 따라야 합니다.\n"
            "2. 각 ETF는 `#### <심볼> (<이름>)` 형식의 제목으로 시작해야 합니다.\n"
            "3. 각 ETF 정보는 `- **권고 사항**: ...`과 `- **이유**: ...` 항목을 반드시 포함해야 합니다.\n"
            "4. `### 종합 의견:` 항목을 반드시 포함해야 합니다.\n"
            "5. 포맷 외에 불필요한 인사말, 서론, 결론 등 부연 설명을 절대 추가하지 마십시오."
        )

        # 4. 오늘 날짜
        today_date = f"[분석 기준일] {datetime.now().year}년 {datetime.now().month}월 {datetime.now().day}일"
        
        # 5. 최종 developer 메시지 조립
        developer_content = (
            f"당신은 유능한 금융 분석가입니다. 아래 정보를 바탕으로 포트폴리오 조정에 대한 조언을 생성해야 합니다. 반드시 [규칙]을 엄격히 준수하십시오.\n\n"
            f"{user_info}\n\n"
            f"{etf_info}\n\n"
            f"{today_date}\n\n"
            f"{output_format_and_rules}"
        )
        
        # 6. user 메시지(명령) 단순화
        user_content = "오늘의 투자 포트폴리오 조정 조언을 생성해줘."

        messages = [
            {"role": "system", "content": developer_content}, # 역할을 system으로 변경하여 더 강력한 지시
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

def parse_structured_ai_response(analysis_text: str) -> dict:
    """
    구조화된 AI 분석 응답 텍스트(마크다운 형식)를 파싱하여 딕셔셔너리로 변환합니다.
    """
    import re
    parsed_data = {"etfs": [], "summary": ""}
    try:
        # '### 종합 의견:'을 기준으로 종합 의견 추출
        summary_match = re.search(r'### 종합 의견:\s*(.*)', analysis_text, re.DOTALL | re.IGNORECASE)
        if summary_match:
            parsed_data["summary"] = summary_match.group(1).strip()
            etf_section = analysis_text[:summary_match.start()]
        else:
            etf_section = analysis_text

        # '####'로 시작하는 각 ETF 블록을 찾아서 처리
        etf_blocks = re.split(r'(?=####\s+)', etf_section)

        for block in etf_blocks:
            block = block.strip()
            if not block.startswith('####'):
                continue
            
            # 심볼과 이름 추출
            title_match = re.search(r'####\s+([A-Z0-9]+)\s*\((.*?)\)', block, re.IGNORECASE)
            if not title_match:
                continue
            
            symbol, name = title_match.groups()

            # 권고 사항 추출
            recommendation_match = re.search(r'-\s*\*\*권고 사항\*\*:\s*(.*)', block, re.IGNORECASE)
            recommendation = recommendation_match.group(1).strip() if recommendation_match else ""

            # 이유 추출
            reason_match = re.search(r'-\s*\*\*이유\*\*:\s*(.*)', block, re.IGNORECASE | re.DOTALL)
            reason = reason_match.group(1).strip() if reason_match else ""

            parsed_data["etfs"].append({
                "symbol": symbol.strip(),
                "name": name.strip(),
                "recommendation": recommendation,
                "reason": reason
            })

    except Exception as e:
        logger.error(f"❌ AI 응답 파싱 중 오류 발생: {e}")
        # 파싱 실패 시, 전체 텍스트를 summary에 넣어 기존 로직이 어느정도 동작하도록 함
        return {"etfs": [], "summary": analysis_text}
    
    logger.debug(f"파싱된 데이터: {parsed_data}")
    return parsed_data

def determine_notification_need(
    db,
    user: User,
    analysis_result: str
) -> tuple[bool, dict]:
    """
    이전 분석 결과와의 코사인 유사도를 기반으로 알림 필요성 판단
    - 오늘의 첫 분석은 항상 알림 전송
    """
    if not embedding_model:
        logger.error(" embedding 모델이 로드되지 않아 알림 판단을 스킵합니다.")
        return True, {"etfs": [], "summary": analysis_result}

    try:
        logger.debug(f"🚀 코사인 유사도 기반 알림 필요성 판단 시작 (사용자: {user.id})")
        
        # 1. 현재 분석 결과 파싱
        parsed_analysis = parse_structured_ai_response(analysis_result)
        
        # 2. 이전 분석 정보 가져오기
        previous_analysis = user.settings.last_analysis_result
        last_analysis_time = user.settings.last_analysis_at

        # 3. 새로운 분석 결과를 DB에 저장할 준비
        current_time = datetime.now(last_analysis_time.tzinfo if last_analysis_time else None)
        new_setting_data = {
            "last_analysis_result": analysis_result,
            "last_analysis_at": current_time
        }

        # 4. 오늘의 첫 분석인지 확인
        is_first_analysis_today = not last_analysis_time or last_analysis_time.date() < current_time.date()

        if is_first_analysis_today:
            logger.info(f"✅ 오늘의 첫 분석입니다. 알림을 전송하고 결과를 저장합니다.")
            update_user_investment_settings(db, user.id, new_setting_data)
            return True, parsed_analysis

        # 5. 이전 분석 결과가 없는 경우 (오늘 첫 분석이 아닌데 이전 결과가 없는 경우)
        if not previous_analysis:
            logger.warning(f"⚠️ 이전 분석 결과가 없습니다. 알림을 전송하고 결과를 저장합니다.")
            update_user_investment_settings(db, user.id, new_setting_data)
            return True, parsed_analysis

        # 6. 이전과 현재 분석의 "종합 의견"을 추출하여 유사도 계산
        current_summary = parsed_analysis.get("summary", "")
        previous_parsed = parse_structured_ai_response(previous_analysis)
        previous_summary = previous_parsed.get("summary", "")

        # 종합 의견이 없는 경우, 비교가 불가능하므로 변화로 간주
        if not current_summary or not previous_summary:
            logger.warning("현재 또는 이전 분석에서 '종합 의견'을 추출할 수 없어, 중요한 변경으로 간주하고 알림을 보냅니다.")
            update_user_investment_settings(db, user.id, new_setting_data)
            return True, parsed_analysis

        logger.debug("--- 현재 종합 의견 ---")
        logger.debug(current_summary)
        logger.debug("--- 이전 종합 의견 ---")
        logger.debug(previous_summary)
        logger.debug("--------------------")
        
        embedding_current = embedding_model.encode([current_summary])
        embedding_previous = embedding_model.encode([previous_summary])
        
        similarity = cosine_similarity(embedding_current, embedding_previous)[0][0]
        
        logger.debug(f"📊 이전 결과와의 코사인 유사도: {similarity:.4f}")

        # 7. 유사도 임계값을 기준으로 알림 여부 결정
        SIMILARITY_THRESHOLD = 0.95
        
        should_notify = False
        if similarity < SIMILARITY_THRESHOLD:
            logger.info(f"✅ 유사도({similarity:.4f})가 임계값({SIMILARITY_THRESHOLD}) 미만. 중요한 변화로 판단하여 알림을 전송하고 결과를 저장합니다.")
            should_notify = True
            # 알림을 보낼 때만 최신 분석 결과로 업데이트
            update_user_investment_settings(db, user.id, new_setting_data)
        else:
            logger.info(f"❌ 유사도({similarity:.4f})가 임계값({SIMILARITY_THRESHOLD}) 이상. 변화가 미미하여 알림을 전송하지 않습니다.")
            # 알림을 보내지 않으므로 결과도 저장하지 않음

        return should_notify, parsed_analysis
        
    except Exception as e:
        logger.error(f"❌ 코사인 유사도 기반 알림 판단 중 오류: {e}", exc_info=True)
        # 오류 발생 시에는 일단 알림을 보내는 것을 기본으로 함
        return True, {"etfs": [], "summary": analysis_result}
