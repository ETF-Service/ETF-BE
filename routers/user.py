from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.user import UserCreate, UserLogin
from schemas.notification import NotificationSettings, NotificationSettingsUpdate
from schemas.etf import InvestmentSettingsUpdate
from crud.user import get_user_by_userId, create_user, get_user_by_email, check_user_exists
from crud.etf import update_investment_settings, get_investment_settings_by_user_id
from utils.security import verify_password
from utils.auth import create_access_token, get_current_user
import logging

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):
    """사용자 회원가입"""
    try:
        # 1. 중복 검사 (한 번의 함수 호출로 처리)
        if check_user_exists(db, user_id=user.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 존재하는 사용자 ID입니다."
            )
        
        if check_user_exists(db, email=user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 존재하는 이메일입니다."
            )
        
        # 2. 사용자 생성
        db_user = create_user(db, user)
        
        # 3. 트랜잭션 커밋
        db.commit()
        
        logger.info(f"새 사용자 가입: {user.user_id} ({user.email})")
        
        return {
            "message": "회원가입 성공", 
            "user_id": db_user.user_id,
            "name": db_user.name,
            "email": db_user.email
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"회원가입 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 처리 중 오류가 발생했습니다."
        )

@router.post("/auth/login")
def login_endpoint(user: UserLogin, db: Session = Depends(get_db)):
    """사용자 로그인"""
    try:
        # 1. 사용자 조회
        db_user = get_user_by_userId(db, user.user_id)
        if not db_user:
            logger.warning(f"로그인 실패: 존재하지 않는 사용자 ID - {user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="아이디 또는 비밀번호가 올바르지 않습니다."
            )
        
        # 2. 비밀번호 검증
        if not verify_password(user.password, str(db_user.hashed_password)):
            logger.warning(f"로그인 실패: 잘못된 비밀번호 - {user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="아이디 또는 비밀번호가 올바르지 않습니다."
            )
        
        # 3. JWT 토큰 생성
        access_token = create_access_token(data={"sub": db_user.user_id})
        
        logger.info(f"사용자 로그인 성공: {user.user_id}")
        
        return {
            "message": "로그인 성공", 
            "user_id": db_user.user_id,
            "name": db_user.name,
            "email": db_user.email,
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"로그인 처리 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 처리 중 오류가 발생했습니다."
        )

@router.get("/users/me")
def get_current_user_info(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """현재 로그인한 사용자 정보 조회"""
    try:
        db_user = get_user_by_userId(db, current_user)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        return {
            "user_id": db_user.user_id,
            "name": db_user.name,
            "email": db_user.email,
            "created_at": db_user.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 정보 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 정보 조회 중 오류가 발생했습니다."
        )

@router.delete("/users/me")
def delete_current_user(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """현재 로그인한 사용자 계정 삭제"""
    try:
        db_user = get_user_by_userId(db, current_user)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 사용자 삭제 (CRUD 함수에서 처리)
        from crud.user import delete_user
        success = delete_user(db, db_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="사용자 삭제에 실패했습니다."
            )
        
        # 트랜잭션 커밋
        db.commit()
        
        logger.info(f"사용자 계정 삭제: {current_user}")
        
        return {"message": "계정이 성공적으로 삭제되었습니다."}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"사용자 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="계정 삭제 중 오류가 발생했습니다."
        )

@router.post("/auth/logout")
def logout_endpoint(current_user: str = Depends(get_current_user)):
    """사용자 로그아웃"""
    try:
        # JWT 토큰은 클라이언트에서 삭제하므로 서버에서는 로그만 남김
        logger.info(f"사용자 로그아웃: {current_user}")
        
        return {
            "message": "로그아웃 성공",
            "user_id": current_user
        }
        
    except Exception as e:
        logger.error(f"로그아웃 처리 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그아웃 처리 중 오류가 발생했습니다."
        )

@router.get("/users/me/notification-settings")
def get_notification_settings(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """사용자 알림 설정 조회"""
    try:
        db_user = get_user_by_userId(db, current_user)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 투자 설정에서 알림 설정 조회
        settings = get_investment_settings_by_user_id(db, db_user.id)
        if not settings:
            # 기본 설정 반환
            return NotificationSettings(
                notification_enabled=True,
            )
        
        return NotificationSettings(
            notification_enabled=settings.notification_enabled,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"알림 설정 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="알림 설정 조회 중 오류가 발생했습니다."
        )

@router.put("/users/me/notification-settings")
def update_notification_settings(
    settings: NotificationSettingsUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 알림 설정 업데이트"""
    try:
        db_user = get_user_by_userId(db, current_user)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 기존 설정 조회
        current_settings = get_investment_settings_by_user_id(db, db_user.id)
        if not current_settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="투자 설정을 찾을 수 없습니다."
            )
        
        investment_settings = InvestmentSettingsUpdate(
            notification_enabled=settings.notification_enabled,
        )
        
        # 설정 업데이트
        success = update_investment_settings(db, current_settings.id, investment_settings)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="알림 설정 업데이트에 실패했습니다."
            )
        
        # 트랜잭션 커밋
        db.commit()
        
        logger.info(f"알림 설정 업데이트: {current_user} - {investment_settings}")
        
        return {"message": "알림 설정이 성공적으로 업데이트되었습니다."}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"알림 설정 업데이트 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="알림 설정 업데이트 중 오류가 발생했습니다."
        )
