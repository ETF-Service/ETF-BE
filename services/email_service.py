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

    def send_portfolio_analysis_notification(self, user_email: str, user_name: str, data: Dict[str, Any]) -> bool:
        """포트폴리오 분석 결과 알림 이메일 전송 - 파싱된 데이터 사용"""
        if not self.enabled:
            logger.warning("이메일 서비스가 비활성화되어 있습니다.")
            return False

        try:
            subject = f"[ETF앱] 포트폴리오 투자 분석 알림 ({data.get('etf_count', 0)}개 종목)"
            html_content = self._create_portfolio_analysis_template(user_name, data)
            
            return self._send_email_direct(user_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"포트폴리오 분석 알림 이메일 전송 실패: {e}")
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

    def _create_portfolio_analysis_template(self, user_name: str, data: Dict[str, Any]) -> str:
        """포트폴리오 분석 알림 이메일 템플릿 (파싱된 데이터를 직접 사용)"""
        etf_list = data.get('etf_list', [])
        total_amount = data.get('total_amount', 0)
        etf_count = data.get('etf_count', 0)
        parsed_analysis = data.get('parsed_analysis', {})
        
        # ETF 목록 HTML 생성
        etf_html = ""
        for etf in etf_list:
            etf_html += f"<li>{etf}</li>"
        
        # ETF별 분석 결과 HTML 생성
        etf_analysis_html = ""
        if parsed_analysis.get('etfs'):
            for etf_info in parsed_analysis['etfs']:
                etf_analysis_html += f"""
                <div class="etf-item">
                    <h4>{etf_info.get('symbol', '')} ({etf_info.get('name', '')})</h4>
                    <div class="recommendation">- <strong>권고 사항</strong>: {etf_info.get('recommendation', 'N/A')}</div>
                    <div class="reason">- <strong>이유</strong>: {etf_info.get('reason', 'N/A')}</div>
                </div>
                """
        else:
            etf_analysis_html = f"<p>상세 분석 정보를 불러오지 못했습니다.</p>"
        
        # 종합 의견 표시
        summary_html = ""
        if parsed_analysis.get('summary'):
            summary_html = f"""
            <div class="summary-box">
                <h3>📋 종합 의견</h3>
                <p>{parsed_analysis['summary']}</p>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>포트폴리오 투자 분석 알림</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #9c27b0 0%, #673ab7 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .section {{ margin-bottom: 25px; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .highlight {{ background: #f3e5f5; padding: 15px; border-radius: 5px; border-left: 4px solid #9c27b0; }}
                .etf-list {{ list-style: none; padding: 0; }}
                .etf-list li {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
                .metric {{ display: inline-block; background: #f5f5f5; padding: 8px 12px; border-radius: 5px; margin: 5px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                .button {{ display: inline-block; background: #9c27b0; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
                .etf-item {{ border-bottom: 1px solid #eee; padding: 15px 0; }}
                .etf-item:last-child {{ border-bottom: none; }}
                .recommendation {{ font-weight: bold; color: #9c27b0; }}
                .reason {{ color: #666; font-style: italic; margin-top: 5px; }}
                .summary-box {{ background: #f0f8ff; padding: 15px; border-radius: 5px; border-left: 4px solid #4caf50; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 포트폴리오 투자 분석 알림</h1>
                    <p>안녕하세요, {user_name}님!</p>
                </div>
                
                <div class="content">
                    <div class="section">
                        <h2>📈 ETF 포트폴리오 분석 결과</h2>
                        <p>오늘 투자일인 {etf_count}개 ETF에 대한 통합 분석 결과입니다.</p>
                    </div>
                    
                    <div class="section">
                        <h3>💰 투자할 ETF 목록</h3>
                        <ul class="etf-list">
                            {etf_html}
                        </ul>
                        <div style="text-align: center; margin-top: 20px;">
                            <div class="metric">총 투자 금액: {total_amount:,g}만 원</div>
                            <div class="metric">ETF 개수: {etf_count}개</div>
                        </div>
                    </div>
                    
                    <div class="section highlight">
                        <h3>🤖 AI 포트폴리오 분석</h3>
                        {etf_analysis_html}
                    </div>
                    
                    {summary_html}
                    
                    <div class="section" style="text-align: center;">
                        <a href="#" class="button">앱에서 자세히 보기</a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>본 메일은 ETF 투자 관리 시스템에서 자동으로 발송되었습니다.</p>
                    <p>© ETF 투자 관리팀</p>
                </div>
            </div>
        </body>
        </html>
        """

# 전역 인스턴스 생성
email_service = EmailService() 