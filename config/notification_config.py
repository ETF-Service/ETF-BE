"""
알림 시스템 전역 설정
"""
import os
from typing import List

# AI 분석 임계값 (모든 사용자 동일)
AI_ANALYSIS_THRESHOLD = float(os.getenv("AI_ANALYSIS_THRESHOLD", "0.7"))

# 알림 시간 (투자일 1시간 전 고정)
NOTIFICATION_TIME = int(os.getenv("NOTIFICATION_TIME", "1"))

# 스케줄러 간격 (1시간마다 실행)
SCHEDULER_INTERVAL = int(os.getenv("SCHEDULER_INTERVAL", "3600"))

# 알림 타입 정의
NOTIFICATION_TYPES = {
    "INVESTMENT_REMINDER": "investment_reminder",
    "AI_ANALYSIS": "ai_analysis", 
    "SYSTEM": "system"
}

# 알림 전송 방식 정의
NOTIFICATION_CHANNELS = {
    "APP": "app",
    "EMAIL": "email",
    "SMS": "sms"
}

# 기본 알림 채널 (앱 내 알림)
DEFAULT_NOTIFICATION_CHANNELS = "app"

# 알림 활성화 기본값
DEFAULT_NOTIFICATION_ENABLED = True

# 알림 제목 템플릿
NOTIFICATION_TITLES = {
    "investment_reminder": "투자일 알림",
    "ai_analysis": "AI 투자 분석 결과",
    "system": "시스템 알림"
}

# 알림 내용 템플릿
NOTIFICATION_CONTENT_TEMPLATES = {
    "investment_reminder": "오늘은 {etf_name} ETF 투자일입니다. {amount}원을 투자하시겠습니까?",
    "ai_analysis": "AI 분석 결과, 투자 비중 조정이 권장됩니다. 자세한 내용을 확인해보세요.",
    "system": "시스템 점검이 완료되었습니다."
}

def get_notification_channels_list(channels_str: str) -> List[str]:
    """알림 채널 문자열을 리스트로 변환"""
    if not channels_str:
        return [DEFAULT_NOTIFICATION_CHANNELS]
    return [channel.strip() for channel in channels_str.split(",") if channel.strip()]

def is_channel_enabled(channels_str: str, channel: str) -> bool:
    """특정 채널이 활성화되어 있는지 확인"""
    channels = get_notification_channels_list(channels_str)
    return channel in channels

def get_ai_analysis_threshold() -> float:
    """AI 분석 임계값 반환"""
    return AI_ANALYSIS_THRESHOLD

def get_notification_time() -> int:
    """알림 시간 반환 (투자일 몇 시간 전)"""
    return NOTIFICATION_TIME

def get_scheduler_interval() -> int:
    """스케줄러 실행 간격 반환 (초)"""
    return SCHEDULER_INTERVAL

def get_notification_titles() -> dict:
    """알림 제목 템플릿 반환"""
    return NOTIFICATION_TITLES

def get_notification_types() -> dict:
    """알림 타입 정의 반환"""
    return NOTIFICATION_TYPES

def get_notification_channels() -> dict:
    """알림 채널 정의 반환"""
    return NOTIFICATION_CHANNELS 