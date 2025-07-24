"""
알림 관련 API 라우터
알림 조회, 읽음 처리, 설정 관리 등의 엔드포인트 제공
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database import get_db
from crud.notification import (
    get_notifications_by_user,
    get_notification_by_id,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    delete_notification,
    get_unread_notification_count,
    get_notification_settings,
    update_notification_settings
)
from schemas.notification import (
    Notification,
    NotificationUpdate,
    NotificationSettings,
    NotificationSettingsUpdate
)
from utils.auth import get_current_user
from models.user import User
from crud.user import get_user_by_userId

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/", response_model=List[Notification])
async def get_notifications(
    skip: int = Query(0, ge=0, description="건너뛸 레코드 수"),
    limit: int = Query(100, ge=1, le=1000, description="가져올 레코드 수"),
    unread_only: bool = Query(False, description="읽지 않은 알림만 조회"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """사용자의 알림 목록 조회"""
    try:
        user = get_user_by_userId(db, current_user)
        notifications = get_notifications_by_user(
            db=db,
            user_id=user.id,
            skip=skip,
            limit=limit,
            unread_only=unread_only
        )
        return notifications
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/count")
async def get_notification_count(
    unread_only: bool = Query(True, description="읽지 않은 알림 개수만 조회"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """알림 개수 조회"""
    try:
        user = get_user_by_userId(db, current_user)
        if unread_only:
            count = get_unread_notification_count(db, user.id)
        else:
            notifications = get_notifications_by_user(db, current_user.id, limit=1000)
            count = len(notifications)
        
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 개수 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/{notification_id}", response_model=Notification)
async def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """특정 알림 조회"""
    try:
        user = get_user_by_userId(db, current_user)
        notification = get_notification_by_id(db, notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
        
        # 본인의 알림만 조회 가능
        if notification.user_id != user.id:
            raise HTTPException(status_code=403, detail="다른 사용자의 알림을 조회할 수 없습니다")
        
        return notification
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 조회 중 오류가 발생했습니다: {str(e)}")

@router.put("/{notification_id}/read", response_model=Notification)
async def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """알림을 읽음으로 표시"""
    try:
        user = get_user_by_userId(db, current_user)
        notification = get_notification_by_id(db, notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
        
        # 본인의 알림만 수정 가능
        if notification.user_id != user.id:
            raise HTTPException(status_code=403, detail="다른 사용자의 알림을 수정할 수 없습니다")
        
        updated_notification = mark_notification_as_read(db, notification_id)
        if not updated_notification:
            raise HTTPException(status_code=500, detail="알림 읽음 처리 중 오류가 발생했습니다")
        
        return updated_notification
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 읽음 처리 중 오류가 발생했습니다: {str(e)}")

@router.put("/read-all")
async def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """모든 알림을 읽음으로 표시"""
    try:
        user = get_user_by_userId(db, current_user)
        count = mark_all_notifications_as_read(db, user.id)
        return {"message": f"{count}개의 알림을 읽음으로 표시했습니다", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 읽음 처리 중 오류가 발생했습니다: {str(e)}")

@router.delete("/{notification_id}")
async def delete_notification_endpoint(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """알림 삭제"""
    try:
        user = get_user_by_userId(db, current_user)
        notification = get_notification_by_id(db, notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
        
        # 본인의 알림만 삭제 가능
        if notification.user_id != user.id:
            raise HTTPException(status_code=403, detail="다른 사용자의 알림을 삭제할 수 없습니다")
        
        success = delete_notification(db, notification_id)
        if not success:
            raise HTTPException(status_code=500, detail="알림 삭제 중 오류가 발생했습니다")
        
        return {"message": "알림이 삭제되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 삭제 중 오류가 발생했습니다: {str(e)}")

@router.get("/settings", response_model=NotificationSettings)
async def get_notification_settings_endpoint(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """알림 설정 조회"""
    try:
        user = get_user_by_userId(db, current_user)
        settings = get_notification_settings(db, user.id)
        if not settings:
            raise HTTPException(status_code=404, detail="알림 설정을 찾을 수 없습니다")
        
        return NotificationSettings(
            notification_enabled=settings.notification_enabled,
            notification_channels=settings.notification_channels
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 설정 조회 중 오류가 발생했습니다: {str(e)}")

@router.put("/settings", response_model=NotificationSettings)
async def update_notification_settings_endpoint(
    settings_update: NotificationSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """알림 설정 업데이트"""
    try:
        user = get_user_by_userId(db, current_user)
        updated_settings = update_notification_settings(
            db, 
            user.id, 
            settings_update
        )
        
        if not updated_settings:
            raise HTTPException(status_code=404, detail="알림 설정을 찾을 수 없습니다")
        
        return NotificationSettings(
            notification_enabled=updated_settings.notification_enabled,
            notification_channels=updated_settings.notification_channels
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 설정 업데이트 중 오류가 발생했습니다: {str(e)}")

@router.post("/test")
async def send_test_notification(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """테스트 알림 전송 (개발용)"""
    try:
        user = get_user_by_userId(db, current_user)
        from crud.notification import create_notification
        from schemas.notification import NotificationCreate
        from config.notification_config import NOTIFICATION_TYPES
        
        test_notification = NotificationCreate(
            user_id=user.id,
            title="테스트 알림",
            content="이것은 테스트 알림입니다. 알림 시스템이 정상적으로 작동하고 있습니다.",
            type=NOTIFICATION_TYPES['SYSTEM'],
            sent_via='app'
        )
        
        notification = create_notification(db, test_notification)
        return {"message": "테스트 알림이 전송되었습니다", "notification_id": notification.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 알림 전송 중 오류가 발생했습니다: {str(e)}")
