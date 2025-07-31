#!/usr/bin/env python3
"""
Railway 배포 테스트 스크립트
ETF Backend API의 Railway 배포를 테스트합니다.
"""

import requests
import json
import time
import sys
import os
from typing import Dict, Any, Optional

class RailwayDeploymentTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'ETF-Backend-Tester/1.0'
        })
    
    def test_health_endpoints(self) -> Dict[str, Any]:
        """헬스체크 엔드포인트 테스트"""
        results = {}
        
        # 기본 헬스체크
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            results['root_health'] = {
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response': response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            results['root_health'] = {
                'status_code': None,
                'success': False,
                'error': str(e)
            }
        
        # 상세 헬스체크
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            results['health_endpoint'] = {
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response': response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            results['health_endpoint'] = {
                'status_code': None,
                'success': False,
                'error': str(e)
            }
        
        return results
    
    def test_user_endpoints(self) -> Dict[str, Any]:
        """사용자 관련 엔드포인트 테스트"""
        results = {}
        
        # 사용자 등록 테스트
        test_user = {
            "email": f"test_{int(time.time())}@example.com",
            "password": "testpassword123",
            "username": f"testuser_{int(time.time())}"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/users/register",
                json=test_user,
                timeout=10
            )
            results['user_register'] = {
                'status_code': response.status_code,
                'success': response.status_code in [200, 201],
                'response': response.json() if response.status_code < 500 else None
            }
        except Exception as e:
            results['user_register'] = {
                'status_code': None,
                'success': False,
                'error': str(e)
            }
        
        # 사용자 로그인 테스트
        try:
            response = self.session.post(
                f"{self.base_url}/users/login",
                json={
                    "email": test_user["email"],
                    "password": test_user["password"]
                },
                timeout=10
            )
            results['user_login'] = {
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response': response.json() if response.status_code == 200 else None
            }
            
            # 토큰 저장
            if response.status_code == 200:
                token = response.json().get('access_token')
                if token:
                    self.session.headers.update({'Authorization': f'Bearer {token}'})
        except Exception as e:
            results['user_login'] = {
                'status_code': None,
                'success': False,
                'error': str(e)
            }
        
        return results
    
    def test_etf_endpoints(self) -> Dict[str, Any]:
        """ETF 관련 엔드포인트 테스트"""
        results = {}
        
        # ETF 목록 조회
        try:
            response = self.session.get(f"{self.base_url}/etfs/", timeout=10)
            results['etf_list'] = {
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response': response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            results['etf_list'] = {
                'status_code': None,
                'success': False,
                'error': str(e)
            }
        
        # 특정 ETF 조회 (첫 번째 ETF가 있다고 가정)
        try:
            response = self.session.get(f"{self.base_url}/etfs/1", timeout=10)
            results['etf_detail'] = {
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response': response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            results['etf_detail'] = {
                'status_code': None,
                'success': False,
                'error': str(e)
            }
        
        return results
    
    def test_chat_endpoints(self) -> Dict[str, Any]:
        """채팅 관련 엔드포인트 테스트"""
        results = {}
        
        # 채팅 메시지 전송 테스트
        test_message = {
            "message": "안녕하세요! ETF 투자에 대해 알려주세요.",
            "user_id": 1
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/chat/send",
                json=test_message,
                timeout=30  # AI 응답은 시간이 더 걸릴 수 있음
            )
            results['chat_send'] = {
                'status_code': response.status_code,
                'success': response.status_code in [200, 201],
                'response': response.json() if response.status_code < 500 else None
            }
        except Exception as e:
            results['chat_send'] = {
                'status_code': None,
                'success': False,
                'error': str(e)
            }
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """모든 테스트 실행"""
        print(f"🚀 ETF Backend Railway 배포 테스트 시작")
        print(f"📍 테스트 대상 URL: {self.base_url}")
        print("=" * 60)
        
        all_results = {}
        
        # 1. 헬스체크 테스트
        print("1️⃣ 헬스체크 엔드포인트 테스트...")
        all_results['health'] = self.test_health_endpoints()
        
        # 2. 사용자 엔드포인트 테스트
        print("2️⃣ 사용자 엔드포인트 테스트...")
        all_results['user'] = self.test_user_endpoints()
        
        # 3. ETF 엔드포인트 테스트
        print("3️⃣ ETF 엔드포인트 테스트...")
        all_results['etf'] = self.test_etf_endpoints()
        
        # 4. 채팅 엔드포인트 테스트
        print("4️⃣ 채팅 엔드포인트 테스트...")
        all_results['chat'] = self.test_chat_endpoints()
        
        return all_results
    
    def print_results(self, results: Dict[str, Any]):
        """테스트 결과 출력"""
        print("\n" + "=" * 60)
        print("📊 테스트 결과 요약")
        print("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        
        for category, category_results in results.items():
            print(f"\n📁 {category.upper()} 테스트:")
            for test_name, test_result in category_results.items():
                total_tests += 1
                status = "✅ PASS" if test_result.get('success') else "❌ FAIL"
                status_code = test_result.get('status_code', 'N/A')
                
                print(f"  {status} {test_name} (HTTP {status_code})")
                
                if test_result.get('success'):
                    passed_tests += 1
                else:
                    if 'error' in test_result:
                        print(f"    오류: {test_result['error']}")
        
        print(f"\n📈 전체 결과: {passed_tests}/{total_tests} 테스트 통과")
        
        if passed_tests == total_tests:
            print("🎉 모든 테스트가 성공적으로 통과했습니다!")
            return True
        else:
            print("⚠️  일부 테스트가 실패했습니다.")
            return False

def main():
    """메인 함수"""
    # 명령행 인수에서 URL 가져오기
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        # 환경변수에서 URL 가져오기
        base_url = os.getenv('RAILWAY_URL', 'https://etf-be-production.up.railway.app')
    
    # URL이 http:// 또는 https://로 시작하지 않으면 http:// 추가
    if not base_url.startswith(('http://', 'https://')):
        base_url = f"http://{base_url}"
    
    print("ETF Backend Railway 배포 테스트")
    print(f"테스트 URL: {base_url}")
    print()
    
    # 테스터 생성 및 테스트 실행
    tester = RailwayDeploymentTester(base_url)
    results = tester.run_all_tests()
    
    # 결과 출력
    success = tester.print_results(results)
    
    # 상세 결과를 JSON 파일로 저장
    with open('railway_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 상세 결과가 'railway_test_results.json' 파일에 저장되었습니다.")
    
    # 종료 코드 설정
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 