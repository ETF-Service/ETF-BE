import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import requests
import json

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@etfapp.com')
        self.from_name = os.getenv('SENDGRID_FROM_NAME', 'ETF 투자 관리팀')
        
        if not self.sendgrid_api_key:
            logger.warning("SENDGRID_API_KEY가 설정되지 않았습니다. 이메일 전송이 비활성화됩니다.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("이메일 서비스 초기화 완료")

    def send_ai_analysis_notification(self, user_email: str, user_name: str, data: Dict[str, Any]) -> bool:
        """AI 분석 결과 알림 이메일 전송"""
        if not self.enabled:
            logger.warning("이메일 서비스가 비활성화되어 있습니다.")
            return False

        try:
            subject = f"[ETF앱] {data.get('etf_symbol', 'ETF')} 투자 분석 알림"
            html_content = self._create_ai_analysis_email_template(user_name, data)
            
            return self._send_email_direct(user_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"AI 분석 알림 이메일 전송 실패: {e}")
            return False

    def send_investment_reminder(self, user_email: str, user_name: str, data: Dict[str, Any]) -> bool:
        """투자일 알림 이메일 전송"""
        if not self.enabled:
            logger.warning("이메일 서비스가 비활성화되어 있습니다.")
            return False

        try:
            subject = "[ETF앱] 오늘은 투자일입니다!"
            html_content = self._create_investment_reminder_template(user_name, data)
            
            return self._send_email_direct(user_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"투자일 알림 이메일 전송 실패: {e}")
            return False

    def send_system_notification(self, user_email: str, user_name: str, title: str, content: str) -> bool:
        """시스템 알림 이메일 전송"""
        if not self.enabled:
            logger.warning("이메일 서비스가 비활성화되어 있습니다.")
            return False

        try:
            html_content = self._create_system_notification_template(user_name, title, content)
            
            return self._send_email_direct(user_email, title, html_content)
            
        except Exception as e:
            logger.error(f"시스템 알림 이메일 전송 실패: {e}")
            return False

    def _send_email_direct(self, to_email: str, subject: str, html_content: str) -> bool:
        """SendGrid API를 직접 호출하여 이메일 전송"""
        try:
            email_data = {
                "personalizations": [
                    {
                        "to": [
                            {
                                "email": to_email,
                                "name": "사용자"
                            }
                        ],
                        "subject": subject
                    }
                ],
                "from": {
                    "email": self.from_email,
                    "name": self.from_name
                },
                "content": [
                    {
                        "type": "text/html",
                        "value": html_content
                    }
                ]
            }
            
            headers = {
                'Authorization': f'Bearer {self.sendgrid_api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                'https://api.sendgrid.com/v3/mail/send',
                headers=headers,
                json=email_data,
                verify=False  # SSL 검증 비활성화
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"이메일 전송 성공: {to_email} - {subject}")
                return True
            else:
                logger.error(f"이메일 전송 실패: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"이메일 전송 중 오류: {e}")
            return False

    def _create_ai_analysis_email_template(self, user_name: str, data: Dict[str, Any]) -> str:
        """AI 분석 알림 이메일 템플릿"""
        etf_symbol = data.get('etf_symbol', 'ETF')
        analysis_summary = data.get('analysis_summary', '분석 결과가 없습니다.')
        recommendation = data.get('recommendation', '권장사항이 없습니다.')
        confidence_score = data.get('confidence_score', 0)
        current_weight = data.get('current_weight', 0)
        recommended_weight = data.get('recommended_weight', 0)
        adjustment_amount = data.get('adjustment_amount', 0)
        detailed_analysis = data.get('detailed_analysis', '상세 분석 내용이 없습니다.')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ETF 투자 분석 알림</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .section {{ margin-bottom: 25px; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .highlight {{ background: #e3f2fd; padding: 15px; border-radius: 5px; border-left: 4px solid #2196f3; }}
                .metric {{ display: inline-block; background: #f5f5f5; padding: 8px 12px; border-radius: 5px; margin: 5px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                .button {{ display: inline-block; background: #2196f3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 ETF 투자 분석 알림</h1>
                    <p>안녕하세요, {user_name}님!</p>
                </div>
                
                <div class="content">
                    <div class="section">
                        <h2>📊 {etf_symbol} ETF 투자 분석</h2>
                        <p>오늘 {etf_symbol} ETF 투자일입니다. AI가 분석한 결과를 확인해보세요.</p>
                    </div>
                    
                    <div class="section highlight">
                        <h3>🤖 AI 분석 결과</h3>
                        <p>{analysis_summary}</p>
                        <div class="metric">신뢰도: {confidence_score}%</div>
                    </div>
                    
                    <div class="section">
                        <h3>📈 투자 권장사항</h3>
                        <p><strong>권장사항:</strong> {recommendation}</p>
                        <div style="display: flex; justify-content: space-between; margin: 20px 0;">
                            <div class="metric">기존 비중: {current_weight}%</div>
                            <div class="metric">권장 비중: {recommended_weight}%</div>
                            <div class="metric">조정 금액: {adjustment_amount:,}원</div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h3>💡 상세 분석</h3>
                        <p>{detailed_analysis}</p>
                    </div>
                    
                    <div class="section" style="text-align: center;">
                        <a href="#" class="button">앱에서 자세히 보기</a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>본 메일은 ETF 투자 관리 시스템에서 자동으로 발송되었습니다.</p>
                    <p>© 2024 ETF 투자 관리팀</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _create_investment_reminder_template(self, user_name: str, data: Dict[str, Any]) -> str:
        """투자일 알림 이메일 템플릿"""
        etf_list = data.get('etf_list', '')
        total_amount = data.get('total_amount', 0)
        
        # etf_list가 문자열인 경우 처리
        if isinstance(etf_list, str):
            etf_items = [item.strip() for item in etf_list.split(',')]
            etf_count = len(etf_items)
            etf_html = ""
            for etf in etf_items:
                etf_html += f"<li>• {etf}</li>"
        else:
            # etf_list가 리스트인 경우 (기존 로직)
            etf_count = len(etf_list)
            etf_html = ""
            for etf in etf_list:
                etf_html += f"<li>• {etf.get('name', 'ETF')}: {etf.get('amount', 0):,}원</li>"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>투자일 알림</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4caf50 0%, #45a049 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .section {{ margin-bottom: 25px; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .highlight {{ background: #e8f5e8; padding: 15px; border-radius: 5px; border-left: 4px solid #4caf50; }}
                .etf-list {{ list-style: none; padding: 0; }}
                .etf-list li {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                .button {{ display: inline-block; background: #4caf50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💰 오늘은 투자일입니다!</h1>
                    <p>안녕하세요, {user_name}님!</p>
                </div>
                
                <div class="content">
                    <div class="section highlight">
                        <h2>⏰ 투자 시간을 잊지 마세요!</h2>
                        <p>오늘은 설정하신 투자일입니다. 정기적인 투자로 안정적인 수익을 만들어보세요.</p>
                    </div>
                    
                    <div class="section">
                        <h3>📊 투자할 ETF 목록</h3>
                        <ul class="etf-list">
                            {etf_html}
                        </ul>
                    </div>
                    
                    <div class="section" style="text-align: center; background: #f0f8ff;">
                        <h3>💵 총 투자 금액</h3>
                        <h2 style="color: #2196f3; font-size: 2em; margin: 10px 0;">{total_amount:,}원</h2>
                        <p>총 {etf_count}개의 ETF에 투자하실 예정입니다.</p>
                    </div>
                    
                    <div class="section" style="text-align: center;">
                        <a href="#" class="button">투자하기</a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>본 메일은 ETF 투자 관리 시스템에서 자동으로 발송되었습니다.</p>
                    <p>© 2024 ETF 투자 관리팀</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _create_system_notification_template(self, user_name: str, title: str, content: str) -> str:
        """시스템 알림 이메일 템플릿"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>시스템 알림</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .section {{ margin-bottom: 25px; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔔 시스템 알림</h1>
                    <p>안녕하세요, {user_name}님!</p>
                </div>
                
                <div class="content">
                    <div class="section">
                        <h2>{title}</h2>
                        <p>{content}</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p>본 메일은 ETF 투자 관리 시스템에서 자동으로 발송되었습니다.</p>
                    <p>© 2024 ETF 투자 관리팀</p>
                </div>
            </div>
        </body>
        </html>
        """

# 전역 인스턴스 생성
email_service = EmailService() 