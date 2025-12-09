"""
AEGIS v3.0 - DeepSeek Client
DeepSeek V3 (Chat) + DeepSeek R1 (Reasoner)

역할 구분:
- DeepSeek V3: 빠르고 유연한 '일반 분석가' (GPT-4o급, 1/10 비용)
- DeepSeek R1: 깊고 논리적인 '심층 감사관' (추론 특화)
"""
import httpx
import logging
from typing import Dict, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """
    DeepSeek API 클라이언트

    모델:
    - deepseek-chat (V3): 빠른 분석, 실시간 수급/섹터 분석
    - deepseek-reasoner (R1): 최종 검증, 논리적 허점 검증
    """

    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url

    async def chat_v3(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        DeepSeek V3 (Chat) 호출

        용도:
        - 실시간 수급/섹터 분석
        - 뉴스/공시 감성 분석
        - 차트 패턴 분석

        Args:
            prompt: 사용자 프롬프트
            system: 시스템 프롬프트 (선택)
            temperature: 창의성 (0~2)
            max_tokens: 최대 토큰 수

        Returns:
            DeepSeek V3 응답 텍스트
        """
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",  # DeepSeek V3
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                )

                if response.status_code != 200:
                    logger.error(f"DeepSeek V3 API error: {response.status_code} - {response.text}")
                    raise Exception(f"API error: {response.status_code}")

                result = response.json()
                content = result['choices'][0]['message']['content']

                logger.debug(f"✅ DeepSeek V3 response: {content[:100]}...")
                return content

        except Exception as e:
            logger.error(f"❌ DeepSeek V3 error: {e}", exc_info=True)
            raise

    async def reason_r1(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Dict:
        """
        DeepSeek R1 (Reasoner) 호출

        용도:
        - 매수 전 최종 검증 (Veto Power)
        - 논리적 허점 검증
        - 리스크 평가

        특징:
        - <think> 태그 안에 추론 과정 포함
        - 최종 답변은 별도로 반환

        Args:
            prompt: 사용자 프롬프트
            system: 시스템 프롬프트 (선택)
            temperature: 창의성 (낮을수록 보수적)
            max_tokens: 최대 토큰 수

        Returns:
            {
                "reasoning": "추론 과정 (think 태그 내용)",
                "answer": "최종 답변",
                "full_content": "전체 응답"
            }
        """
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:  # R1은 느림
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-reasoner",  # DeepSeek R1
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                )

                if response.status_code != 200:
                    logger.error(f"DeepSeek R1 API error: {response.status_code} - {response.text}")
                    raise Exception(f"API error: {response.status_code}")

                result = response.json()
                message = result['choices'][0]['message']

                # R1은 reasoning_content (추론 과정) + content (최종 답변) 분리
                reasoning = message.get('reasoning_content', '')
                answer = message.get('content', '')
                full_content = f"{reasoning}\n\n{answer}" if reasoning else answer

                logger.debug(f"✅ DeepSeek R1 response: reasoning={len(reasoning)} chars, answer={len(answer)} chars")

                return {
                    "reasoning": reasoning,
                    "answer": answer,
                    "full_content": full_content
                }

        except Exception as e:
            logger.error(f"❌ DeepSeek R1 error: {e}", exc_info=True)
            raise


# Singleton Instance
deepseek_client = DeepSeekClient()
