from sqlalchemy.orm import Session
from sqlalchemy import and_
from models import Notification, InvestmentSettings
from schemas.notification import NotificationCreate, NotificationUpdate, NotificationSettingsUpdate
from datetime import datetime
from typing import List, Optional

def create_notification(db: Session, notification: NotificationCreate) -> Notification:
    """알림 생성"""
    db_notification = Notification(**notification.dict())
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

def get_notifications_by_user(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100,
    unread_only: bool = False
) -> List[Notification]:
    """사용자별 알림 조회"""
    query = db.query(Notification).filter(Notification.user_id == user_id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    return query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()

def get_notification_by_id(db: Session, notification_id: int) -> Optional[Notification]:
    """ID로 알림 조회"""
    return db.query(Notification).filter(Notification.id == notification_id).first()

def get_notifications_by_user_id_and_type(
    db: Session, 
    user_id: int, 
    notification_type: str, 
    limit: int = 1
) -> List[Notification]:
    """사용자 ID와 알림 타입으로 알림 목록 조회 (최신순)"""
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.type == notification_type
    ).order_by(Notification.created_at.desc()).limit(limit).all()

def update_notification(
    db: Session, 
    notification_id: int, 
    notification_update: NotificationUpdate
) -> Optional[Notification]:
    """알림 업데이트 (주로 읽음 처리)"""
    db_notification = get_notification_by_id(db, notification_id)
    if not db_notification:
        return None
    
    update_data = notification_update.dict(exclude_unset=True)
    
    # 읽음 처리 시 read_at 자동 설정
    if update_data.get('is_read') and not db_notification.read_at:
        update_data['read_at'] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(db_notification, field, value)
    
    db.commit()
    db.refresh(db_notification)
    return db_notification


def get_notification_settings(db: Session, user_id: int) -> Optional[InvestmentSettings]:
    """사용자의 알림 설정 조회"""
    return db.query(InvestmentSettings).filter(InvestmentSettings.user_id == user_id).first()

def update_notification_settings(
    db: Session, 
    user_id: int, 
    settings_update: NotificationSettingsUpdate
) -> Optional[InvestmentSettings]:
    """알림 설정 업데이트"""
    db_settings = get_notification_settings(db, user_id)
    if not db_settings:
        return None
    
    update_data = settings_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_settings, field, value)
    
    db.commit()
    db.refresh(db_settings)
    return db_settings

def get_users_with_notifications_enabled(db: Session) -> List[InvestmentSettings]:
    """알림이 활성화된 사용자 목록 조회"""
    return db.query(InvestmentSettings).filter(
        InvestmentSettings.notification_enabled == True
    ).all() 