#!/usr/bin/env python3
"""
Free Cloud LLM Integration (Cerebras, OpenRouter, Vercel AI Gateway)
====================================================================
Multi-provider LLM analyzer using OpenAI-compatible APIs.
Fast, hosted, free tier available.

Supported Providers:
1. Cerebras - Ultra-fast inference (2000-3000 tokens/sec)
2. OpenRouter - Access to multiple free models
3. Vercel AI Gateway - Unified gateway to multiple providers

Setup:
1. Get API key from chosen provider
2. Add to .env file:
   CEREBRAS_API_KEY=your_key
   OPENROUTER_API_KEY=your_key
   AI_GATEWAY_API_KEY=your_key

Performance:
- Cerebras: ~2000-3000 tokens/sec (FASTEST!)
- OpenRouter: ~30-100 tokens/sec
- Vercel AI Gateway: Depends on underlying provider

Documentation:
- Cerebras: https://cerebras.ai/docs
- OpenRouter: https://openrouter.ai/docs
- Vercel AI Gateway: https://vercel.com/docs/ai-gateway
- OpenAI SDK: https://github.com/openai/openai-python
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from src.core import config
from src.core.constants import API_KEY_MASK_PREFIX, API_KEY_MASK_SUFFIX, API_KEY_MIN_LENGTH
from src.infrastructure.cache import CustomCache
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Check availability of optional dependencies
try:
    from openai import OpenAI

    _openai_imported = True
except ImportError:
    _openai_imported = False
OPENAI_AVAILABLE = _openai_imported

try:
    from cerebras.cloud.sdk import Cerebras

    _cerebras_imported = True
except ImportError:
    _cerebras_imported = False
CEREBRAS_SDK_AVAILABLE = _cerebras_imported

try:
    from tqdm import tqdm

    _tqdm_imported = True
except ImportError:
    _tqdm_imported = False
TQDM_AVAILABLE = _tqdm_imported

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


class CloudLLMAnalyzer:
    """Free hosted LLM analyzer using OpenAI-compatible APIs"""

    # Provider configurations (sorted by speed - fastest first!)
    PROVIDERS: ClassVar[dict] = {
        "cerebras": {
            "name": "Cerebras",
            "base_url": "https://api.cerebras.ai/v1",
            "env_key": "CEREBRAS_API_KEY",
            "models": {
                "default": "llama-3.3-70b",  # Best balance
                "fast": "llama3.1-8b",  # Fastest (~2200 tokens/sec)
                "ultra": "llama-3.3-70b",  # Ultra fast & smart
                "smart": "llama-3.3-70b",  # Best reasoning
            },
            "emoji": "🧠",
            "speed": "EXTREME SPEED! (2000-3000 tokens/sec)",
            "use_native_sdk": True,  # Use Cerebras SDK for best performance
        },
        "openrouter": {
            "name": "OpenRouter",
            "base_url": "https://openrouter.ai/api/v1",
            "env_key": "OPENROUTER_API_KEY",
            "models": {
                "default": "google/gemma-2-9b-it:free",
                "fast": "google/gemma-2-9b-it:free",
                "smart": "meta-llama/llama-3.1-8b-instruct:free",
                "qwen": "qwen/qwen-2-7b-instruct:free",
            },
            "emoji": "🌐",
            "speed": "Medium-Fast (30-100 tokens/sec)",
            "use_native_sdk": False,
        },
        "vercel": {
            "name": "Vercel AI Gateway",
            "base_url": None,  # Set dynamically from env
            "env_key": "AI_GATEWAY_API_KEY",
            "url_env_key": "AI_GATEWAY_URL",  # e.g., https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/openai
            "models": {
                "default": "gpt-3.5-turbo",  # Depends on gateway config
                "fast": "gpt-3.5-turbo",
                "smart": "gpt-4o-mini",
            },
            "emoji": "▲",
            "speed": "Variable (depends on provider)",
            "use_native_sdk": False,
        },
    }

    def __init__(self, provider: str = "cerebras", model: str = "default"):
        """
        Initialize Free Cloud LLM analyzer

        Args:
            provider: 'cerebras', 'openrouter', or 'vercel'
            model: 'default', 'fast', or 'smart' (or specific model name)
        """
        self.provider = provider.lower()
        self.enabled = False
        self.request_count = 0
        self.client: Any = None
        self.api_key = ""

        # Validate provider
        if not self._validate_provider():
            return

        self.config = self.PROVIDERS[self.provider]
        self.model = self._resolve_model_name(model)

        # Setup cache
        self._setup_cache()

        # Log initialization
        self._log_initialization()

        # Check dependencies
        if not self._check_dependencies():
            return

        # Get and validate API key
        if not self._setup_api_key():
            return

        # Initialize API client
        self._initialize_client()

    def _validate_provider(self) -> bool:
        """Validate provider is supported"""
        if self.provider not in self.PROVIDERS:
            logger.error(f"Unknown provider: {self.provider}")
            logger.info(f"Available providers: {', '.join(self.PROVIDERS.keys())}")
            return False
        return True

    def _resolve_model_name(self, model: str) -> str:
        """Resolve model name from alias or use as-is"""
        if model in self.config["models"]:
            return self.config["models"][model]
        return model  # Use as-is (custom model name)

    def _setup_cache(self) -> None:
        """Setup cache directory and manager"""
        self.cache_dir = Path(config.get_session_dir()) / f"{self.provider}_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "responses.json"
        self.cache_manager = CustomCache(self.cache_file, logger)

    def _log_initialization(self) -> None:
        """Log initialization info"""
        logger.info("=" * 80)
        logger.info(f"{self.config['emoji']} {self.config['name'].upper()} INITIALIZATION")
        logger.info("=" * 80)
        logger.info(f"Provider: {self.config['name']}")
        logger.info(f"Model: {self.model}")
        logger.info(f"Speed: {self.config['speed']}")
        logger.info(f"CustomCache directory: {self.cache_dir}")
        logger.info(f"CustomCached responses: {len(self.cache_manager)}")

    def _check_dependencies(self) -> bool:
        """Check required dependencies are installed"""
        if not self.config.get("use_native_sdk") and not OPENAI_AVAILABLE:
            logger.warning("openai library not installed")
            logger.warning("Install: uv sync")
            return False
        return True

    def _setup_api_key(self) -> bool:
        """Get and validate API key from environment"""
        self.api_key = os.getenv(self.config["env_key"], "")

        if not self.api_key:
            logger.warning(f"{self.config['env_key']} not found in environment")
            logger.warning(f"⚠️  {self.config['name']} API key not found")
            logger.warning(f"   Set {self.config['env_key']} in .env file")
            return False

        # Mask API key for logging
        masked_key = (
            f"{self.api_key[:API_KEY_MASK_PREFIX]}...{self.api_key[-API_KEY_MASK_SUFFIX:]}"
            if len(self.api_key) > API_KEY_MIN_LENGTH
            else "***"
        )
        logger.info(f"API Key loaded: {masked_key}")
        return True

    def _initialize_client(self) -> None:
        """Initialize API client (Cerebras SDK or OpenAI)"""
        try:
            if (
                self.provider == "cerebras"
                and self.config.get("use_native_sdk")
                and CEREBRAS_SDK_AVAILABLE
            ):
                self.client = Cerebras(api_key=self.api_key)
                logger.info("Using native Cerebras SDK")
            else:
                base_url = self._get_base_url()
                if not base_url:
                    return

                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=base_url,
                    timeout=30.0,
                    max_retries=2,
                )
                logger.info(f"Using OpenAI SDK with base_url: {base_url}")

            self.enabled = True
            logger.info(f"{self.config['emoji']} {self.config['name']} ready: {self.model}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize {self.config['name']}: {e}")

    def _get_base_url(self) -> str:
        """Get base URL for OpenAI SDK (with special Vercel handling)"""
        base_url = self.config["base_url"]

        # Special handling for Vercel AI Gateway (URL from env)
        if self.provider == "vercel":
            base_url = os.getenv(self.config.get("url_env_key", ""), "")
            if not base_url:
                logger.warning(f"{self.config.get('url_env_key')} not found in environment")
                return ""

        return base_url

    def clear_cache(self):
        """Clear all cached responses"""
        self.cache_manager.clear()
        logger.success(f"✅ {self.config['name']} cache cleared")

    def _build_prompts(self, phone_data: dict) -> tuple[str, str]:
        """Build system and user prompts for LLM analysis.

        Args:
            phone_data: Phone listing data

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        title = phone_data.get("title", "")
        description = phone_data.get("description", "")
        price = phone_data.get("price", 0)

        system_prompt = """Ты анализируешь объявления о продаже телефонов на OLX.kz (Казахстан).

ВАЖНЫЕ ПРАВИЛА:
1. Отмечай ТОЛЬКО реальные дефекты, явно упомянутые в описании
2. Пустое описание - это НОРМАЛЬНО для OLX, НЕ дефект
3. Ставь "is_usable": false ТОЛЬКО для серьезных проблем (не работает, нет сети)
4. ТАКЖЕ определяй ОТЛИЧНЫЕ объявления для бонусов:
   - Идеальное состояние (отличное, идеальное)
   - Полный комплект + коробка + аксессуары
   - Как новый (состояние нового)
   - На гарантии
5. Отдельно отмечай подозрительные объявления (несуществующие модели, невозможные цены)

Верни анализ ТОЛЬКО в формате JSON без дополнительного текста:
{
    "severity": "none|minor|major|critical",
    "is_usable": true/false,
    "issues_found": ["только реальные проблемы"],
    "bonus_points": 0-30,
    "bonus_reasons": ["причины бонуса"],
    "suspicious_flags": ["фейковая модель", "цена подозрительна"],
    "is_suspicious": true/false,
    "recommendation": "краткая рекомендация",
    "confidence": 0.0-1.0
}"""

        user_prompt = f"""Название: {title}
Цена: {price} KZT
Описание: {description if description else "[НЕТ ОПИСАНИЯ - ЭТО НОРМАЛЬНО]"}"""

        return system_prompt, user_prompt

    def _send_llm_request(self, system_prompt: str, user_prompt: str) -> str:
        """Send request to LLM and get streamed response.

        Args:
            system_prompt: System instructions
            user_prompt: User query

        Returns:
            Complete response text

        Raises:
            Exception: If client not initialized or API error
        """
        if not self.client:
            msg = "Client not initialized"
            raise RuntimeError(msg)

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            max_tokens=500,
            temperature=0.3,
        )

        # Collect streamed response
        result_text = ""
        for chunk in stream:
            if hasattr(chunk, "choices") and chunk.choices and chunk.choices[0].delta.content:  # type: ignore[union-attr]
                result_text += chunk.choices[0].delta.content  # type: ignore[union-attr]

        return result_text

    def _parse_json_response(self, result_text: str) -> dict[str, Any]:
        """Extract and parse JSON from LLM response.

        Args:
            result_text: Raw LLM response

        Returns:
            Parsed JSON as dictionary

        Raises:
            json.JSONDecodeError: If JSON parsing fails
        """
        # Extract JSON (handle markdown code blocks)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```", maxsplit=1)[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        # Remove any leading/trailing non-JSON text
        start_idx = result_text.find("{")
        end_idx = result_text.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            result_text = result_text[start_idx:end_idx]

        return json.loads(result_text)

    def _log_analysis_result(self, request_id: str, analysis: dict[str, Any]) -> None:
        """Log the parsed analysis result.

        Args:
            request_id: Request identifier
            analysis: Parsed analysis dictionary
        """
        logger.info(f"{request_id} | PARSED RESULT:")
        logger.info(f"  Severity: {analysis.get('severity', 'unknown')}")
        logger.info(f"  Usable: {analysis.get('is_usable', 'unknown')}")
        logger.info(f"  Bonus points: {analysis.get('bonus_points', 0)}")
        logger.info(f"  Suspicious: {analysis.get('is_suspicious', False)}")

        if analysis.get("bonus_reasons"):
            logger.info("  Bonus reasons:")
            for reason in analysis["bonus_reasons"]:
                logger.info(f"    ⭐ {reason}")

        if analysis.get("issues_found"):
            logger.info("  Issues found:")
            for issue in analysis["issues_found"]:
                logger.info(f"    • {issue}")

    def analyze_listing(self, phone_data: dict, retry_count: int = 3) -> dict[Any, Any]:
        """
        Analyze a single phone listing using free cloud LLM

        Args:
            phone_data: Dictionary containing phone information
            retry_count: Number of retries on failure (default: 3)

        Returns:
            Analysis results (same format as Gemini)
        """
        if not self.enabled:
            return {"analyzed": False, "reason": f"{self.config['name']} not available"}

        # Check cache first
        cache_key = CustomCache.generate_phone_cache_key(phone_data)
        if cache_key in self.cache_manager:
            logger.debug(f"📦 CustomCache HIT: {phone_data.get('title', '')[:50]}")
            cached_result = self.cache_manager.get(cache_key)
            assert isinstance(cached_result, dict), "CustomCache should contain dict"
            return cached_result

        self.request_count += 1
        request_id = f"REQ_{self.request_count:03d}"

        # Log request info
        title = phone_data.get("title", "")
        description = phone_data.get("description", "")
        price = phone_data.get("price", 0)

        logger.info("=" * 80)
        logger.info(f"{request_id} | NEW {self.config['name'].upper()} REQUEST")
        logger.info("=" * 80)
        logger.info(f"Phone: {title}")
        logger.info(f"Price: {price} KZT")
        logger.info(f"Description length: {len(description)} chars")

        # Build prompts
        system_prompt, user_prompt = self._build_prompts(phone_data)

        logger.debug(f"{request_id} | PROMPT (user part):")
        logger.debug("-" * 80)
        logger.debug(user_prompt)
        logger.debug("-" * 80)

        # Retry logic
        for attempt in range(1, retry_count + 1):
            start_time = time.time()

            try:
                logger.info(
                    f"{request_id} | Sending request to {self.config['name']} (attempt {attempt}/{retry_count})..."
                )

                # Get LLM response
                result_text = self._send_llm_request(system_prompt, user_prompt)

                elapsed_time = time.time() - start_time
                logger.info(f"{request_id} | Response received in {elapsed_time:.2f}s")

                logger.debug(f"{request_id} | RAW RESPONSE:")
                logger.debug("-" * 80)
                logger.debug(result_text)
                logger.debug("-" * 80)

                # Parse JSON response
                analysis = self._parse_json_response(result_text)
                analysis["analyzed"] = True
                analysis["source"] = self.provider

                # Log parsed result
                self._log_analysis_result(request_id, analysis)
                logger.info(f"{request_id} | ✅ Analysis completed successfully")

                # CustomCache the result
                result_dict: dict[Any, Any] = analysis
                self.cache_manager.set(cache_key, result_dict)

                return result_dict

            except json.JSONDecodeError as e:
                logger.error(
                    f"{request_id} | JSON parsing error (attempt {attempt}/{retry_count}): {e}"
                )
                logger.error(f"Raw text that failed to parse: {result_text[:200]}")
                if attempt == retry_count:
                    return {"analyzed": False, "error": f"JSON parsing error: {e!s}"}
                time.sleep(1)

            except Exception as e:
                logger.error(f"{request_id} | Error (attempt {attempt}/{retry_count}): {e}")
                if attempt == retry_count:
                    return {"analyzed": False, "error": str(e)}
                time.sleep(2**attempt)  # Exponential backoff

        return {"analyzed": False, "error": "Max retries exceeded"}

    async def _send_llm_request_async(self, system_prompt: str, user_prompt: str) -> str:
        """Send async request to LLM and get response (non-streaming for compatibility).

        Args:
            system_prompt: System instructions
            user_prompt: User query

        Returns:
            Complete response text

        Raises:
            Exception: If client not initialized or API error
        """
        if not self.client:
            msg = "Client not initialized"
            raise RuntimeError(msg)

        # Use non-streaming for async (Cerebras SDK doesn't support async streaming well)
        # Run the sync call in a thread pool to avoid blocking
        def _sync_call():
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=False,  # Non-streaming for async
                max_tokens=500,
                temperature=0.3,
            )
            return response.choices[0].message.content or ""

        # Run sync call in thread pool
        result_text = await asyncio.to_thread(_sync_call)
        return result_text

    async def analyze_listing_async(self, phone_data: dict, retry_count: int = 3) -> dict[Any, Any]:
        """
        Analyze a single phone listing using free cloud LLM (ASYNC version)

        Args:
            phone_data: Dictionary containing phone information
            retry_count: Number of retries on failure (default: 3)

        Returns:
            Analysis results (same format as Gemini)
        """
        if not self.enabled:
            return {"analyzed": False, "reason": f"{self.config['name']} not available"}

        # Check cache first (dict reads are atomic in Python)
        cache_key = CustomCache.generate_phone_cache_key(phone_data)
        if cache_key in self.cache_manager:
            logger.debug(f"📦 CustomCache HIT (async): {phone_data.get('title', '')[:50]}")
            cached_result = self.cache_manager.get(cache_key)
            assert isinstance(cached_result, dict), "CustomCache should contain dict"
            return cached_result

        self.request_count += 1
        request_id = f"REQ_{self.request_count:03d}"

        # Build prompts
        system_prompt, user_prompt = self._build_prompts(phone_data)

        # Retry logic
        for attempt in range(1, retry_count + 1):
            start_time = time.time()

            try:
                # Get LLM response (async)
                result_text = await self._send_llm_request_async(system_prompt, user_prompt)

                elapsed_time = time.time() - start_time
                logger.info(f"{request_id} | Response received in {elapsed_time:.2f}s (async)")

                # Parse JSON response
                analysis = self._parse_json_response(result_text)
                analysis["analyzed"] = True
                analysis["source"] = self.provider

                # CustomCache the result
                result_dict: dict[Any, Any] = analysis
                self.cache_manager.set(cache_key, result_dict)

                return result_dict

            except json.JSONDecodeError as e:
                logger.error(
                    f"{request_id} | JSON parsing error (attempt {attempt}/{retry_count}): {e}"
                )
                if attempt == retry_count:
                    return {"analyzed": False, "error": f"JSON parsing error: {e!s}"}
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"{request_id} | Error (attempt {attempt}/{retry_count}): {e}")
                if attempt == retry_count:
                    return {"analyzed": False, "error": str(e)}
                await asyncio.sleep(2**attempt)  # Exponential backoff

        return {"analyzed": False, "error": "Max retries exceeded"}

    async def analyze_batch_async(  # noqa: PLR0915
        self, phones: list[dict], max_phones: int = 10, max_concurrent: int = 5
    ) -> list[dict]:
        """
        Analyze multiple phone listings CONCURRENTLY (async version)

        Args:
            phones: List of phone data dictionaries
            max_phones: Maximum number of phones to analyze
            max_concurrent: Maximum concurrent requests (default: 5)

        Returns:
            List of phone data with added analysis field
        """
        if not self.enabled:
            logger.warning(f"{self.config['name']} not enabled")
            return phones

        logger.info("=" * 80)
        logger.info(f"ASYNC BATCH ANALYSIS ({self.config['name']})")
        logger.info("=" * 80)
        logger.info(f"Max concurrent requests: {max_concurrent}")
        logger.info(f"Total phones to analyze: {min(len(phones), max_phones)}")

        # Initialize counters
        analyzed_phones = []
        successful_analyses = 0
        failed_analyses = 0
        critical_issues = 0
        major_issues = 0
        bonus_phones = 0
        batch_start_time = time.time()

        phones_to_analyze = phones[:max_phones]

        # ✅ CORRECT: Use asyncio.gather with semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_semaphore(phone: dict, index: int):
            """Analyze phone with concurrency limit"""
            async with semaphore:
                logger.info(
                    f"[{index}/{len(phones_to_analyze)}] Analyzing: {phone.get('title', 'Unknown')[:60]}"
                )
                return await self.analyze_listing_async(phone)

        # Create tasks for all phones
        tasks = [analyze_with_semaphore(phone, i + 1) for i, phone in enumerate(phones_to_analyze)]

        logger.info(
            f"⚡ Executing {len(tasks)} async requests (max {max_concurrent} concurrent)..."
        )

        # Execute all analyses concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, (phone, analysis_result) in enumerate(zip(phones_to_analyze, results)):
            analysis: dict[str, Any]
            if isinstance(analysis_result, Exception):
                logger.error(f"[{i + 1}] Exception: {analysis_result}")
                analysis = {"analyzed": False, "error": str(analysis_result)}
                failed_analyses += 1
            else:
                analysis = analysis_result  # type: ignore[assignment]
                phone[f"{self.provider}_analysis"] = analysis

                # Count success/failure
                if analysis.get("analyzed"):
                    successful_analyses += 1

                    # Apply score adjustments
                    is_bonus, is_critical, is_major = self._apply_score_adjustments(phone, analysis)
                    bonus_phones += 1 if is_bonus else 0
                    critical_issues += 1 if is_critical else 0
                    major_issues += 1 if is_major else 0
                else:
                    failed_analyses += 1

            analyzed_phones.append(phone)

        # Add remaining phones
        analyzed_phones.extend(phones[max_phones:])

        # Log completion
        batch_elapsed = time.time() - batch_start_time
        logger.info("=" * 80)
        logger.info(f"ASYNC BATCH ANALYSIS COMPLETED ({self.config['name']})")
        logger.info("=" * 80)
        logger.info(f"Total requests: {len(phones_to_analyze)}")
        logger.info(f"Successful: {successful_analyses}")
        logger.info(f"Failed: {failed_analyses}")
        logger.info(f"Upvoted (excellent): {bonus_phones}")
        logger.info(f"Critical issues: {critical_issues}")
        logger.info(f"Major issues: {major_issues}")
        logger.info(f"Total time: {batch_elapsed:.2f}s")
        logger.info(f"Average time per request: {batch_elapsed / max(successful_analyses, 1):.2f}s")

        logger.info(f"\n📊 {self.config['name']} Async Analysis Summary:")
        logger.success(f"   ✅ Successful: {successful_analyses}/{max_phones}")
        logger.info(f"   ⭐ Upvoted: {bonus_phones}")
        logger.warning(f"   ❌ Critical: {critical_issues}")
        logger.warning(f"   ⚠️  Major: {major_issues}")
        logger.info(
            f"   ⏱️  Total time: {batch_elapsed:.1f}s ({batch_elapsed / max(successful_analyses, 1):.1f}s/phone)"
        )

        return analyzed_phones

    def _log_batch_start(self, phones_count: int) -> None:
        """Log batch analysis start info"""
        logger.info("=" * 80)
        logger.info(f"BATCH ANALYSIS STARTED ({self.config['name']})")
        logger.info("=" * 80)
        logger.info(f"Provider: {self.config['name']}")
        logger.info(f"Model: {self.model}")
        logger.info(f"Total phones to analyze: {phones_count}")
        logger.info(f"Batch started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(
            f"\n{self.config['emoji']} Analyzing with {self.config['name']} ({self.model})..."
        )
        logger.info(f"   {self.config['speed']}")

    def _apply_bonus_points(self, phone: dict, bonus_points: int) -> bool:
        """Apply bonus points to phone score

        Returns:
            True if bonus was applied
        """
        if bonus_points <= 0 or "value_score" not in phone:
            return False

        original_score = phone["value_score"]
        phone["value_score"] = original_score + bonus_points
        phone[f"{self.provider}_bonus"] = bonus_points
        if TQDM_AVAILABLE:
            tqdm.write(
                f"      ⭐ Bonus +{bonus_points}pts! Score: {original_score} → {phone['value_score']}"
            )
        return True

    def _apply_suspicious_penalty(self, phone: dict) -> None:
        """Apply suspicious listing penalty"""
        if "value_score" not in phone:
            return

        phone["is_suspicious"] = True
        original_score = phone["value_score"]
        phone["value_score"] = max(0, original_score - 30)
        phone[f"{self.provider}_penalty"] = -30

    def _apply_critical_penalty(self, phone: dict) -> bool:
        """Apply critical issue penalty

        Returns:
            True if penalty was applied
        """
        if "value_score" not in phone:
            return False

        original_score = phone["value_score"]
        phone["value_score"] = max(0, original_score - 60)
        phone[f"{self.provider}_penalty"] = phone.get(f"{self.provider}_penalty", 0) - 60
        return True

    def _apply_major_penalty(self, phone: dict) -> bool:
        """Apply major issue penalty

        Returns:
            True if penalty was applied
        """
        if "value_score" not in phone:
            return False

        original_score = phone["value_score"]
        phone["value_score"] = max(0, original_score - 25)
        phone[f"{self.provider}_penalty"] = phone.get(f"{self.provider}_penalty", 0) - 25
        return True

    def _apply_score_adjustments(self, phone: dict, analysis: dict) -> tuple[bool, bool, bool]:
        """Apply score adjustments based on analysis results

        Returns:
            Tuple of (is_bonus, is_critical, is_major)
        """
        if not analysis.get("analyzed"):
            return (False, False, False)

        # Apply bonus points
        is_bonus = self._apply_bonus_points(phone, analysis.get("bonus_points", 0))

        # Apply suspicious penalty
        if analysis.get("is_suspicious"):
            self._apply_suspicious_penalty(phone)

        # Apply critical/major penalties
        is_critical = False
        is_major = False

        if analysis.get("severity") == "critical" and not analysis.get("is_usable"):
            is_critical = self._apply_critical_penalty(phone)
        elif analysis.get("severity") == "major":
            is_major = self._apply_major_penalty(phone)

        return (is_bonus, is_critical, is_major)

    def _log_batch_complete(  # noqa: PLR0913
        self,
        successful: int,
        failed: int,
        bonus: int,
        critical: int,
        major: int,
        elapsed: float,
        max_phones: int,
    ) -> None:
        """Log batch analysis completion info"""
        logger.info("=" * 80)
        logger.info(f"BATCH ANALYSIS COMPLETED ({self.config['name']})")
        logger.info("=" * 80)
        logger.info(f"Total requests: {self.request_count}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Upvoted (excellent): {bonus}")
        logger.info(f"Critical issues: {critical}")
        logger.info(f"Major issues: {major}")
        logger.info(f"Total time: {elapsed:.2f}s")
        logger.info(f"Average time per request: {elapsed / max(successful, 1):.2f}s")

        logger.info(f"\n📊 {self.config['name']} Analysis Summary:")
        logger.success(f"   ✅ Successful: {successful}/{max_phones}")
        logger.info(f"   ⭐ Upvoted: {bonus}")
        logger.warning(f"   ❌ Critical: {critical}")
        logger.warning(f"   ⚠️  Major: {major}")
        logger.info(f"   ⏱️  Total time: {elapsed:.1f}s ({elapsed / max(successful, 1):.1f}s/phone)")

    def analyze_batch(self, phones: list[dict], max_phones: int = 10) -> list[dict]:
        """
        Analyze multiple phone listings with progress bar

        Args:
            phones: List of phone data dictionaries
            max_phones: Maximum number of phones to analyze

        Returns:
            List of phone data with added analysis field
        """
        if not self.enabled:
            logger.warning(f"{self.config['name']} not enabled")
            return phones

        self._log_batch_start(min(len(phones), max_phones))

        # Initialize counters
        analyzed_phones = []
        successful_analyses = 0
        failed_analyses = 0
        critical_issues = 0
        major_issues = 0
        bonus_phones = 0
        batch_start_time = time.time()

        # Progress bar setup
        phones_to_analyze = phones[:max_phones]
        iterator = (
            tqdm(
                enumerate(phones_to_analyze, 1),
                total=len(phones_to_analyze),
                desc=f"{self.config['emoji']} {self.config['name']}",
                ncols=100,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            )
            if TQDM_AVAILABLE
            else enumerate(phones_to_analyze, 1)
        )

        # Analyze each phone
        for i, phone in iterator:
            title_short = phone.get("title", "Unknown")[:60]
            if not TQDM_AVAILABLE:
                logger.info(f"   Analyzing {i}/{len(phones_to_analyze)}: {title_short}...")

            # Run analysis
            analysis = self.analyze_listing(phone)
            phone[f"{self.provider}_analysis"] = analysis

            # Count success/failure
            if analysis.get("analyzed"):
                successful_analyses += 1

                # Apply score adjustments
                is_bonus, is_critical, is_major = self._apply_score_adjustments(phone, analysis)
                bonus_phones += 1 if is_bonus else 0
                critical_issues += 1 if is_critical else 0
                major_issues += 1 if is_major else 0
            else:
                failed_analyses += 1

            analyzed_phones.append(phone)

        # Add remaining phones
        analyzed_phones.extend(phones[max_phones:])

        # Log completion
        batch_elapsed = time.time() - batch_start_time
        self._log_batch_complete(
            successful_analyses,
            failed_analyses,
            bonus_phones,
            critical_issues,
            major_issues,
            batch_elapsed,
            max_phones,
        )

        return analyzed_phones
