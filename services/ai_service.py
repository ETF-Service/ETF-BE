import requests

AI_SERVER_URL = "http://localhost:8001/chat"

class AIService:
    @staticmethod
    def get_ai_answer(messages, api_key, model_type):
        payload = {
            "messages": messages,
            "api_key": api_key,
            "model_type": model_type
        }
        try:
            response = requests.post(AI_SERVER_URL, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data.get("answer", "AI 답변을 가져올 수 없습니다.")
        except Exception as e:
            return f"AI 서버 호출 오류: {str(e)}" 