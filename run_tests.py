#!/usr/bin/env python3
"""
테스트 실행 스크립트
"""
import subprocess
import sys
import os

def run_tests():
    """테스트 실행"""
    print("🧪 ETF 백엔드 테스트를 시작합니다...")
    
    # 테스트 디렉토리로 이동
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # pytest 실행
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--cov=.", 
            "--cov-report=html",
            "--cov-report=term-missing"
        ], capture_output=True, text=True)
        
        print("📊 테스트 결과:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️  경고/에러:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ 모든 테스트가 통과했습니다!")
        else:
            print("❌ 일부 테스트가 실패했습니다.")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 