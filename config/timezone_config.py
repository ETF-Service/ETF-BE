"""
시간대 설정
한국 시간(KST) 기준으로 시간을 처리하기 위한 설정
"""

import os
from datetime import datetime, timezone, timedelta

# 환경변수에서 시간대 설정 (기본값: KST)
TIMEZONE_OFFSET = int(os.getenv("TIMEZONE_OFFSET", "9"))  # UTC+9 (한국 시간)
TIMEZONE_NAME = os.getenv("TIMEZONE_NAME", "Asia/Seoul")

# 한국 시간대 설정 (KST: UTC+9)
KST = timezone(timedelta(hours=TIMEZONE_OFFSET))

def get_kst_now():
    """현재 한국 시간 반환"""
    return datetime.now(KST)

def format_kst_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """datetime 객체를 한국 시간으로 포맷팅"""
    if dt.tzinfo is None:
        # timezone 정보가 없으면 UTC로 가정하고 KST로 변환
        dt = dt.replace(tzinfo=timezone.utc)
    
    kst_dt = dt.astimezone(KST)
    return kst_dt.strftime(format_str)

def get_kst_date_string() -> str:
    """현재 한국 날짜를 문자열로 반환 (YYYY-MM-DD)"""
    return get_kst_now().strftime("%Y-%m-%d")

def get_kst_time_string() -> str:
    """현재 한국 시간을 문자열로 반환 (HH:MM:SS)"""
    return get_kst_now().strftime("%H:%M:%S")

def get_kst_datetime_string() -> str:
    """현재 한국 날짜시간을 문자열로 반환 (YYYY-MM-DD HH:MM:SS)"""
    return get_kst_now().strftime("%Y-%m-%d %H:%M:%S")

def parse_kst_datetime(date_string: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """문자열을 한국 시간 datetime 객체로 파싱"""
    dt = datetime.strptime(date_string, format_str)
    return dt.replace(tzinfo=KST) 