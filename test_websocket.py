"""
AEGIS v3.0 - WebSocket Connection Test
WebSocket 승인키 테스트 스크립트
"""
import asyncio
import sys
from datetime import datetime

from app.config import settings
from fetchers.kis_client import KISClient


async def test_websocket_connection():
    """WebSocket 연결 테스트"""
    print("=" * 60)
    print("🧪 KIS WebSocket 연결 테스트")
    print("=" * 60)
    print()

    # 1. 승인키 확인 (자동 발급 방식)
    print("1️⃣ WebSocket 승인키 (자동 발급)")
    print("   KIS_APP_KEY + KIS_APP_SECRET로 자동 발급됩니다.")
    print("   .env에 하드코딩할 필요 없습니다.")
    print()

    # 2. KIS Client 초기화
    print("2️⃣ KIS Client 초기화")
    try:
        client = KISClient()
        print(f"   ✅ Client 초기화 완료")
        print(f"   계좌번호: {settings.kis_account_number}")
        print(f"   APP_KEY: {settings.kis_app_key[:20]}...")
        print()
    except Exception as e:
        print(f"   ❌ 초기화 실패: {e}")
        return False

    # 3. WebSocket 연결
    print("3️⃣ WebSocket 연결 시도")
    print(f"   연결 시작: {datetime.now().strftime('%H:%M:%S')}")

    try:
        success = await client.connect_websocket()

        if success:
            print(f"   ✅ WebSocket 연결 성공!")
            print()

            # 4. 실시간 시세 구독 (삼성전자)
            print("4️⃣ 실시간 시세 구독 (삼성전자 005930)")

            try:
                await client.subscribe_realtime_price("005930")
                print(f"   ✅ 구독 완료")
                print()

                # 5. 데이터 수신 대기
                print("5️⃣ 데이터 수신 대기 (10초)")
                print("   실시간 데이터 수신 중...")
                print()

                received_data = []

                async def collect_data(data):
                    """데이터 수집"""
                    received_data.append(data)
                    print(f"   📊 [{datetime.now().strftime('%H:%M:%S')}] 데이터 수신: {data.get('stck_prpr', 'N/A')}원")

                # 데이터 수신 (10초)
                try:
                    await asyncio.wait_for(
                        client.listen_realtime_data(collect_data),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    pass

                print()
                print(f"   ✅ 총 {len(received_data)}개 데이터 수신")

                if len(received_data) > 0:
                    print()
                    print("   📈 수신 샘플:")
                    for i, data in enumerate(received_data[:3]):
                        print(f"      {i+1}. 가격: {data.get('stck_prpr', 'N/A')}원, 시간: {data.get('stck_cntg_hour', 'N/A')}")

            except Exception as e:
                print(f"   ❌ 구독 실패: {e}")

            # 6. 연결 종료
            print()
            print("6️⃣ WebSocket 연결 종료")
            await client.disconnect_websocket()
            print(f"   ✅ 연결 종료 완료")
            print()

            return True

        else:
            print(f"   ❌ WebSocket 연결 실패")
            print()
            print("   가능한 원인:")
            print("   - 승인키가 올바르지 않음")
            print("   - 네트워크 연결 문제")
            print("   - 한투 서버 점검 중")
            print()
            return False

    except Exception as e:
        print(f"   ❌ 연결 중 오류: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 함수"""
    try:
        result = await test_websocket_connection()

        print()
        print("=" * 60)
        if result:
            print("✅ WebSocket 테스트 성공!")
            print()
            print("다음 단계:")
            print("1. Korean Market Trap Detector 실시간 감지 활성화")
            print("2. Micro Optimizer 체결강도 실시간 체크")
            print("3. 실시간 수급 데이터 수집 시작")
        else:
            print("❌ WebSocket 테스트 실패")
            print()
            print("문제 해결:")
            print("1. 승인키 발급: https://apiportal.koreainvestment.com")
            print("2. 가이드 참조: docs/dev/26-KIS-WEBSOCKET-SETUP.md")
            print("3. 고객센터: 1544-5000")
        print("=" * 60)

        return 0 if result else 1

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자 중단")
        return 1
    except Exception as e:
        print(f"\n\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    """스크립트 실행"""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ 실행 오류: {e}")
        sys.exit(1)
