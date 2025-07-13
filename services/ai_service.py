import json
from typing import AsyncGenerator
import asyncio

class AIService:
    def __init__(self):
        self.ai_base_url = "http://localhost:8501"  # Streamlit AI 서비스 URL
    
    async def get_response(self, message: str, user_name: str, portfolios, settings) -> str:
        """AI 서비스에서 일반 응답 받기"""
        try:
            # 실제 AI 서비스 연동 전까지는 모의 응답
            return f"안녕하세요 {user_name}님! '{message}'에 대한 답변입니다. 현재 AI 서비스 연동 중입니다."
        except Exception as e:
            raise Exception(f"AI 서비스 통신 오류: {str(e)}")
    
    async def get_response_stream(self, message: str, user_name: str, portfolios, settings) -> AsyncGenerator[str, None]:
        """AI 서비스에서 스트리밍 응답 받기"""
        try:
            # 실제 AI 서비스 연동 전까지는 모의 스트리밍 응답
            response = f"안녕하세요 {user_name}님! '{message}'에 대한 답변입니다.\n\n"
            response += "현재 AI 서비스 연동 중입니다. 곧 실제 ETF 분석 기능을 제공할 예정입니다.\n\n"
            response += "지원 예정 기능:\n"
            response += "• 실시간 시장 분석\n"
            response += "• 개인화된 투자 조언\n"
            response += "• 포트폴리오 리밸런싱 추천\n"
            response += "• 리스크 관리 가이드"
            
            # 스트리밍 시뮬레이션
            words = response.split()
            for word in words:
                yield word + " "
                await asyncio.sleep(0.1)  # 100ms 딜레이
                
        except Exception as e:
            yield f"AI 서비스 통신 오류: {str(e)}" 