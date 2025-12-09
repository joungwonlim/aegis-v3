"""
AEGIS v3.0 - Token Caching Test
동일 인스턴스 내에서 토큰 캐싱이 작동하는지 테스트
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetchers.kis_client import KISClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_token_caching():
    """토큰 캐싱 테스트"""
    print("=" * 60)
    print("🧪 토큰 캐싱 테스트")
    print("=" * 60)
    print()

    # 1. KISClient 인스턴스 생성
    print("1️⃣ KISClient 인스턴스 생성")
    client = KISClient()
    print()

    # 2. 첫 번째 토큰 발급
    print("2️⃣ 첫 번째 get_access_token() 호출 (새 토큰 발급 예상)")
    token1 = client.get_access_token()
    print(f"   Token: {token1[:50]}...")
    print(f"   만료 시간: {client.token_expires_at}")
    print()

    # 3. 두 번째 토큰 요청 (캐시 사용 예상)
    print("3️⃣ 두 번째 get_access_token() 호출 (캐시 재사용 예상)")
    token2 = client.get_access_token()
    print(f"   Token: {token2[:50]}...")
    print(f"   만료 시간: {client.token_expires_at}")
    print()

    # 4. 결과 확인
    print("4️⃣ 결과 확인")
    if token1 == token2:
        print("   ✅ 토큰 캐싱 성공! (동일한 토큰 재사용)")
        print("   ✅ 1분 제한 회피 가능")
    else:
        print("   ❌ 토큰 캐싱 실패 (다른 토큰 발급)")

    print()
    print("=" * 60)

if __name__ == "__main__":
    test_token_caching()
