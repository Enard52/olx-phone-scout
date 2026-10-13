#!/usr/bin/env python3
"""
Google GenAI SDK Integration for Phone Listing Analysis (Gemini 2.0+)
======================================================================
Features:
- ✅ New Google GenAI SDK (centralized Client object)
- ✅ Progress saving with checkpoints
- ✅ Visual progress bar (tqdm)
- ✅ Response caching
- ✅ Native async support (parallel requests)
- ✅ Upvoting for excellent condition
- ✅ Exception handling with retry logic

Setup:
1. Install: uv sync (google-genai, tqdm are project deps)
2. Set environment variable: export GEMINI_API_KEY="your-key-here"
   (or GOOGLE_API_KEY works too)
3. Or create .env file with: GEMINI_API_KEY=your-key-here
"""

# Setup sys.path FIRST before any project imports
# Standard library imports
import asyncio
import json
import os
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import requests as req_lib
from PIL import Image

from src.core import config
from src.core.constants import API_KEY_MASK_PREFIX, API_KEY_MASK_SUFFIX, API_KEY_MIN_LENGTH, HTTP_OK
from src.infrastructure.cache import CustomCache
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Check availability of optional dependencies
try:
    from dotenv import load_dotenv

    load_dotenv()
    _dotenv_imported = True
except ImportError:
    _dotenv_imported = False
DOTENV_AVAILABLE = _dotenv_imported

try:
    from google import genai
    from google.genai import types

    _gemini_imported = True
except ImportError:
    _gemini_imported = False
GEMINI_AVAILABLE = _gemini_imported

try:
    from tqdm import tqdm

    _tqdm_imported = True
except ImportError:
    _tqdm_imported = False
TQDM_AVAILABLE = _tqdm_imported


class GeminiAnalyzer:
    """Enhanced analyzer using Google GenAI SDK (Gemini 2.0+)"""

    def __init__(
        self,
        api_key: str | None = None,
        use_photos: bool = False,
        use_async: bool = False,
        max_concurrent: int = 5,
    ):
        """
        Initialize Gemini analyzer with new SDK

        Args:
            api_key: Google Gemini API key (optional, will try GEMINI_API_KEY or GOOGLE_API_KEY env vars)
            use_photos: Whether to upload photos to Gemini (default: False)
            use_async: Whether to use async processing (default: False)
            max_concurrent: Maximum concurrent requests for async mode (default: 5)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.enabled = False
        self.client = None
        self.request_count = 0
        self.use_photos = use_photos
        self.use_async = use_async
        self.max_concurrent = max_concurrent

        # CustomCache management
        self.cache_dir = Path(config.get_session_dir()) / "gemini_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "responses.json"
        self.cache_manager = CustomCache(self.cache_file, logger)

        # Progress checkpoint
        self.checkpoint_file = self.cache_dir / "checkpoint.json"

        logger.info("=" * 80)
        logger.info("GEMINI API INITIALIZATION (Google GenAI SDK)")
        logger.info("=" * 80)
        logger.info("SDK: Google GenAI (Gemini 2.0+)")
        logger.info(f"Photo upload: {'ENABLED' if use_photos else 'DISABLED (saves tokens)'}")
        logger.info(f"Async mode: {'ENABLED' if use_async else 'DISABLED'}")
        if use_async:
            logger.info(f"Max concurrent requests: {max_concurrent}")
        logger.info(f"CustomCache directory: {self.cache_dir}")
        logger.info(f"CustomCached responses: {len(self.cache_manager)}")

        # Check if library is available
        if not GEMINI_AVAILABLE:
            logger.warning("Google GenAI SDK not installed")
            logger.info("Install with: uv sync")
            print("⚠️  Google GenAI SDK not installed")
            print("   Run: uv sync")
            return

        # Check if API key is available
        if not self.api_key:
            logger.warning("Gemini API key not found")
            logger.info("To use AI analysis:")
            logger.info("  1. Get API key from: https://ai.google.dev/")
            logger.info("  2. Create .env file with: GEMINI_API_KEY=your-key-here")
            logger.info("  3. Or set environment variable: export GEMINI_API_KEY=your-key")
            print("⚠️  Gemini API key not found")
            print("   To use AI analysis:")
            print("   1. Get API key from: https://ai.google.dev/")
            print("   2. Create .env file with: GEMINI_API_KEY=your-key-here")
            return

        # Mask API key for logging
        masked_key = (
            f"{self.api_key[:API_KEY_MASK_PREFIX]}...{self.api_key[-API_KEY_MASK_SUFFIX:]}"
            if len(self.api_key) > API_KEY_MIN_LENGTH
            else "***"
        )
        logger.info(f"API Key loaded: {masked_key}")

        # Initialize client with new SDK
        try:
            logger.info("Creating GenAI Client...")
            self.client = genai.Client(api_key=self.api_key)
            self.enabled = True
            logger.info("✅ Google GenAI Client initialized successfully")
            logger.info("Model: gemini-2.0-flash-exp")
            print("✅ Google GenAI SDK initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GenAI Client: {e}", exc_info=True)
            print(f"⚠️  Failed to initialize GenAI Client: {e}")

    def clear_cache(self):
        """Clear all cached responses"""
        self.cache_manager.clear()
        print("✅ Gemini cache cleared")

    def _save_checkpoint(self, analyzed_phones: list[dict], current_index: int):
        """Save progress checkpoint"""
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "total_phones": len(analyzed_phones),
            "current_index": current_index,
            "successful": sum(
                1
                for p in analyzed_phones[:current_index]
                if p.get("gemini_analysis", {}).get("analyzed")
            ),
        }
        try:
            with Path.open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2)
            logger.debug(f"💾 Checkpoint saved at index {current_index}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def _load_checkpoint(self) -> dict[Any, Any] | None:
        """Load progress checkpoint"""
        if self.checkpoint_file.exists():
            try:
                with Path.open(self.checkpoint_file, encoding="utf-8") as f:
                    checkpoint: dict[Any, Any] = json.load(f)
                    return checkpoint
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        return None

    def _create_analysis_prompt(self, phone_data: dict) -> str:
        """Create the analysis prompt for Gemini.

        Args:
            phone_data: Phone listing data

        Returns:
            Formatted prompt string
        """
        title = phone_data.get("title", "")
        description = phone_data.get("description", "")
        price = phone_data.get("price", 0)

        return f"""You are analyzing a used phone listing from OLX.kz marketplace.

CRITICAL RULES:
1. ONLY flag ACTUAL defects EXPLICITLY mentioned in description or visible in photos
2. Empty description is NORMAL on OLX - NOT a defect
3. Set "is_usable": false ONLY for REAL serious problems (broken, не работает, network issues)
4. ALSO identify EXCELLENT listings that deserve BONUS points:
   - Perfect/mint condition (отличное состояние, идеальное)
   - Full box + accessories (полный комплект)
   - Like new (как новый, состояние нового)
   - Under warranty (на гарантии)

5. Flag suspicious listings separately (fake models, impossible prices)

Title: {title}
Price: {price} KZT
Description: {description if description else "[NO DESCRIPTION PROVIDED - THIS IS NORMAL]"}

Provide analysis in JSON format:
{{
    "severity": "none|minor|major|critical",
    "is_usable": true/false,
    "issues_found": ["only ACTUAL problems mentioned"],
    "bonus_points": 0-30,
    "bonus_reasons": ["why bonus given"],
    "suspicious_flags": ["fake model", "price too low"],
    "is_suspicious": true/false,
    "recommendation": "brief recommendation",
    "confidence": 0.0-1.0
}}

SEVERITY (based on ACTUAL defects):
- none: No defects OR no description
- minor: Cosmetic only (царапины, потертости)
- major: Significant (трещина, missing accessories)
- critical: Unusable (не работает, нет сети, экран разбит)

BONUS POINTS (for upvoting excellent listings):
- +30: Perfect condition + full box + accessories + warranty
- +20: Excellent condition + box + accessories
- +15: Great condition + box
- +10: Like new condition
- +5: Full box/accessories OR under warranty
- 0: Normal used condition

Respond ONLY with valid JSON."""

    def _upload_photos_to_content(self, phone_data: dict, request_id: str) -> tuple[list[Any], int]:
        """Upload photos and add them to content parts.

        Args:
            phone_data: Phone listing data
            request_id: Request ID for logging

        Returns:
            Tuple of (content parts list, upload count)
        """
        content_parts: list[Any] = []
        uploaded_count = 0
        photos = phone_data.get("photos", [])

        logger.info(f"{request_id} | 📸 Uploading {len(photos)} photos...")

        for i, photo_url in enumerate(photos[:8], 1):
            try:
                photo_response = req_lib.get(photo_url, timeout=10)
                if photo_response.status_code == HTTP_OK:
                    img = Image.open(BytesIO(photo_response.content))
                    content_parts.append(img)
                    uploaded_count += 1
                    logger.debug(f"{request_id} |    Photo {i}: ✅")
                else:
                    logger.warning(
                        f"{request_id} |    Photo {i}: ❌ HTTP {photo_response.status_code}"
                    )
            except Exception as e:
                logger.warning(f"{request_id} |    Photo {i}: ❌ {str(e)[:50]}")

        logger.info(f"{request_id} | ✅ Uploaded {uploaded_count}/{len(photos[:8])} photos")
        return content_parts, uploaded_count

    def _parse_json_response(self, response_text: str) -> dict[Any, Any]:
        """Parse JSON from Gemini response, handling markdown code blocks.

        Args:
            response_text: Raw response text from Gemini

        Returns:
            Parsed JSON dictionary

        Raises:
            json.JSONDecodeError: If JSON parsing fails
        """
        result_text = response_text.strip()

        # Extract JSON from markdown code blocks
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        analysis = json.loads(result_text)
        analysis["analyzed"] = True
        return analysis

    def _log_analysis_result(self, analysis: dict[Any, Any], request_id: str) -> None:
        """Log the parsed analysis result.

        Args:
            analysis: Parsed analysis dictionary
            request_id: Request ID for logging
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

        logger.info(f"{request_id} | ✅ Analysis completed successfully")

    def _check_cache(self, phone_data: dict) -> dict[Any, Any] | None:
        """Check cache for existing analysis"""
        cache_key = CustomCache.generate_phone_cache_key(phone_data)
        if cache_key in self.cache_manager:
            logger.debug(f"📦 CustomCache HIT: {phone_data.get('title', '')[:50]}")
            cached_result = self.cache_manager.get(cache_key)
            assert isinstance(cached_result, dict), "CustomCache should contain dict"
            return cached_result
        return None

    def _log_request_info(self, request_id: str, phone_data: dict) -> None:
        """Log request information"""
        title = phone_data.get("title", "")
        description = phone_data.get("description", "")
        price = phone_data.get("price", 0)

        logger.info("=" * 80)
        logger.info(f"{request_id} | NEW API REQUEST")
        logger.info("=" * 80)
        logger.info(f"Phone: {title}")
        logger.info(f"Price: {price} KZT")
        logger.info(f"Description length: {len(description)} chars")

    def _prepare_content_parts(self, prompt: str, phone_data: dict, request_id: str) -> list[Any]:
        """Prepare content parts including photos if enabled"""
        content_parts: list[Any] = [prompt]

        if self.use_photos and phone_data.get("photos"):
            photo_parts, _uploaded_count = self._upload_photos_to_content(phone_data, request_id)
            content_parts.extend(photo_parts)
        else:
            logger.debug(f"{request_id} | 📝 Text-only analysis")

        return content_parts

    def _call_gemini_api(self, content_parts: list[Any], request_id: str) -> tuple[str, float]:
        """Call Gemini API and return response text and elapsed time"""
        if not self.client:
            raise RuntimeError("Client not initialized")

        start_time = time.time()
        response = self.client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=content_parts,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )

        elapsed_time = time.time() - start_time
        logger.info(f"{request_id} | Response received in {elapsed_time:.2f}s")

        result_text = (response.text or "").strip()
        logger.debug(f"{request_id} | RAW RESPONSE:")
        logger.debug("-" * 80)
        logger.debug(result_text)
        logger.debug("-" * 80)

        return result_text, elapsed_time

    def _handle_api_error(
        self, error: Exception, request_id: str, attempt: int, retry_count: int
    ) -> dict[Any, Any] | None:
        """Handle API errors and return error dict if terminal, None to retry"""
        logger.error(f"{request_id} | API error (attempt {attempt}/{retry_count}): {error}")

        error_str = str(error).lower()
        if "quota" in error_str or "rate" in error_str:
            logger.error(f"{request_id} | QUOTA/RATE LIMIT ERROR")
            print("⚠️  API quota/rate limit exceeded. Saving progress...")
            return {"analyzed": False, "error": "API quota exceeded", "fatal": True}

        if attempt == retry_count:
            print(f"⚠️  API error after {retry_count} attempts: {error}")
            return {"analyzed": False, "error": str(error)}

        return None  # Retry

    def analyze_listing(self, phone_data: dict, retry_count: int = 3) -> dict[Any, Any]:
        """Analyze a single phone listing using Gemini AI.

        Args:
            phone_data: Dictionary containing phone information
            retry_count: Number of retries on failure (default: 3)

        Returns:
            Analysis results with severity, issues, bonus_points, and recommendation
        """
        if not self.enabled:
            return {"analyzed": False, "reason": "GenAI Client not available"}

        # Check cache first
        cached = self._check_cache(phone_data)
        if cached:
            return cached

        self.request_count += 1
        request_id = f"REQ_{self.request_count:03d}"

        self._log_request_info(request_id, phone_data)

        prompt = self._create_analysis_prompt(phone_data)
        logger.debug(f"{request_id} | PROMPT:")
        logger.debug("-" * 80)
        logger.debug(prompt)
        logger.debug("-" * 80)

        cache_key = CustomCache.generate_phone_cache_key(phone_data)

        # Retry logic
        for attempt in range(1, retry_count + 1):
            try:
                logger.info(f"{request_id} | Sending request (attempt {attempt}/{retry_count})...")

                # Prepare content
                content_parts = self._prepare_content_parts(prompt, phone_data, request_id)

                # Call API
                result_text, _elapsed = self._call_gemini_api(content_parts, request_id)

                # Parse JSON response
                analysis = self._parse_json_response(result_text)

                # Log parsed result
                self._log_analysis_result(analysis, request_id)

                # CustomCache and return
                result_dict: dict[Any, Any] = analysis
                self.cache_manager.set(cache_key, result_dict)

                return result_dict

            except json.JSONDecodeError as e:
                logger.error(
                    f"{request_id} | JSON parsing error (attempt {attempt}/{retry_count}): {e}"
                )
                if attempt == retry_count:
                    print(f"⚠️  JSON parsing error after {retry_count} attempts")
                    return {"analyzed": False, "error": f"JSON parsing error: {e!s}"}
                time.sleep(2**attempt)

            except Exception as e:
                error_result = self._handle_api_error(e, request_id, attempt, retry_count)
                if error_result:
                    return error_result
                time.sleep(2**attempt)

        return {"analyzed": False, "error": "Max retries exceeded"}

    def _parse_async_response(self, result_text: str) -> dict:
        """Parse async response JSON"""
        # Extract JSON from markdown code blocks if present
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```", maxsplit=1)[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        analysis = json.loads(result_text)
        analysis["analyzed"] = True
        return analysis

    async def analyze_listing_async(self, phone_data: dict, retry_count: int = 3) -> dict[Any, Any]:
        """Async version using new SDK's client.aio"""
        if not self.enabled:
            return {"analyzed": False, "reason": "GenAI Client not available"}

        # Check cache first (safe in async context - dict reads are atomic in Python)
        cached = self._check_cache(phone_data)
        if cached:
            logger.debug(f"📦 CustomCache HIT (async): {phone_data.get('title', '')[:50]}")
            return cached

        self.request_count += 1
        cache_key = CustomCache.generate_phone_cache_key(phone_data)
        prompt = self._create_analysis_prompt(phone_data)

        for attempt in range(1, retry_count + 1):
            try:
                # Use new SDK's async client.aio.models.generate_content()
                if not self.client:
                    return {"analyzed": False, "error": "Client not initialized"}

                response = await self.client.aio.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                    ),
                )

                result_text = (response.text or "").strip()
                analysis = self._parse_async_response(result_text)

                # CustomCache and return
                result_dict: dict[Any, Any] = analysis
                self.cache_manager.set(cache_key, result_dict)

                return result_dict

            except Exception as e:
                if attempt == retry_count:
                    return {"analyzed": False, "error": str(e)}
                await asyncio.sleep(2**attempt)

        return {"analyzed": False, "error": "Max retries exceeded"}

    def _apply_bonus_adjustment(self, phone: dict, bonus_points: int) -> int:
        """Apply bonus points to phone score.

        Args:
            phone: Phone data dictionary
            bonus_points: Bonus points to add

        Returns:
            Number of bonus phones incremented (0 or 1)
        """
        if bonus_points <= 0 or "value_score" not in phone:
            return 0

        original_score = phone["value_score"]
        phone["value_score"] = original_score + bonus_points
        phone["gemini_bonus"] = bonus_points
        logger.info(f"⭐ Excellent! Score: {original_score} → {phone['value_score']}")
        if TQDM_AVAILABLE:
            tqdm.write(
                f"      ⭐ Bonus +{bonus_points}pts! Score: {original_score} → {phone['value_score']}"
            )
        return 1

    def _apply_penalty_adjustments(self, phone: dict, analysis: dict) -> tuple[int, int]:
        """Apply penalty adjustments for issues.

        Args:
            phone: Phone data dictionary
            analysis: Analysis results

        Returns:
            Tuple of (critical_issues_count, major_issues_count)
        """
        critical_count = 0
        major_count = 0

        if "value_score" not in phone:
            return critical_count, major_count

        # Suspicious listing penalty
        if analysis.get("is_suspicious"):
            phone["is_suspicious"] = True
            original_score = phone["value_score"]
            phone["value_score"] = max(0, original_score - 30)
            phone["gemini_penalty"] = -30
            if TQDM_AVAILABLE:
                tqdm.write(f"      🚩 Suspicious! Score: {original_score} → {phone['value_score']}")

        # Critical issue penalty
        if analysis.get("severity") == "critical" and not analysis.get("is_usable"):
            critical_count = 1
            original_score = phone["value_score"]
            phone["value_score"] = max(0, original_score - 60)
            phone["gemini_penalty"] = phone.get("gemini_penalty", 0) - 60
            if TQDM_AVAILABLE:
                tqdm.write(f"      ❌ Critical! Score: {original_score} → {phone['value_score']}")

        # Major issue penalty
        elif analysis.get("severity") == "major":
            major_count = 1
            original_score = phone["value_score"]
            phone["value_score"] = max(0, original_score - 25)
            phone["gemini_penalty"] = phone.get("gemini_penalty", 0) - 25
            if TQDM_AVAILABLE:
                tqdm.write(f"      ⚠️  Major! Score: {original_score} → {phone['value_score']}")

        return critical_count, major_count

    def _log_batch_summary(self, stats: dict[str, int | float]) -> None:
        """Log batch analysis summary.

        Args:
            stats: Dictionary containing batch statistics (successful, failed,
                   bonus, critical, major, elapsed)
        """
        successful = stats["successful"]
        failed = stats["failed"]
        bonus = stats["bonus"]
        critical = stats["critical"]
        major = stats["major"]
        elapsed = stats["elapsed"]

        logger.info("=" * 80)
        logger.info("BATCH ANALYSIS COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Total requests: {self.request_count}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Upvoted (excellent): {bonus}")
        logger.info(f"Critical issues: {critical}")
        logger.info(f"Major issues: {major}")
        logger.info(f"Batch time: {elapsed:.1f}s ({elapsed / 60:.1f} min)")
        logger.info(f"Average per phone: {elapsed / max(successful, 1):.1f}s")

        print("\n✅ Batch analysis complete!")
        print(f"   Success: {successful} | Failed: {failed}")
        print(f"   Excellent: {bonus} ⭐ | Issues: {critical + major} ⚠️")

    def _log_gemini_batch_start(self, phones_count: int) -> None:
        """Log batch analysis start information"""
        logger.info("=" * 80)
        logger.info("BATCH ANALYSIS STARTED (Google GenAI SDK)")
        logger.info("=" * 80)
        logger.info(f"Total phones to analyze: {phones_count}")
        logger.info(f"Batch started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n🔍 Analyzing top {phones_count} listings with Gemini AI...")

    def _get_gemini_start_index(self, max_phones: int) -> int:
        """Get starting index from checkpoint if available"""
        checkpoint = self._load_checkpoint()
        if checkpoint:
            start_index = checkpoint.get("current_index", 0)
            logger.info(f"📍 Resuming from checkpoint at index {start_index}")
            print(f"📍 Resuming from index {start_index}/{max_phones}")
            return start_index
        return 0

    def _create_gemini_iterator(self, phones: list[dict]) -> Any:
        """Create progress bar iterator"""
        if TQDM_AVAILABLE:
            return tqdm(
                enumerate(phones, 1),
                total=len(phones),
                desc="🤖 Gemini AI Analysis",
                ncols=100,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            )
        return enumerate(phones, 1)

    def _handle_gemini_fatal(
        self, analysis: dict, analyzed_phones: list, i: int, max_phones: int
    ) -> bool:
        """Handle fatal error during analysis. Returns True if fatal"""
        if not analysis.get("fatal"):
            return False

        logger.error("Fatal error - saving progress")
        print(f"\n❌ Fatal error: {analysis.get('error')}")
        print(f"💾 Progress saved. Analyzed {i - 1}/{max_phones} phones")
        self._save_checkpoint(analyzed_phones, i)
        return True

    def _process_gemini_result(self, phone: dict, analysis: dict) -> tuple[int, int, int, int, int]:
        """Process analysis result and return counters"""
        if analysis.get("analyzed"):
            bonus = self._apply_bonus_adjustment(phone, analysis.get("bonus_points", 0))
            crit, maj = self._apply_penalty_adjustments(phone, analysis)
            return 1, 0, bonus, crit, maj  # successful, failed, bonus, critical, major
        return 0, 1, 0, 0, 0

    def analyze_batch(self, phones: list[dict], max_phones: int = 10) -> list[dict]:
        """
        Analyze multiple phone listings with progress saving and visual progress bar

        Args:
            phones: List of phone data dictionaries
            max_phones: Maximum number of phones to analyze

        Returns:
            List of phone data with added 'gemini_analysis' field
        """
        if not self.enabled:
            logger.warning("GenAI Client not enabled")
            return phones

        # Setup
        phones_count = min(len(phones), max_phones)
        self._log_gemini_batch_start(phones_count)
        start_index = self._get_gemini_start_index(max_phones)

        # Initialize counters
        analyzed_phones = []
        stats = {"successful": 0, "failed": 0, "bonus": 0, "critical": 0, "major": 0}
        batch_start_time = time.time()

        # Create progress iterator
        phones_to_analyze = phones[:max_phones]
        iterator = self._create_gemini_iterator(phones_to_analyze)

        # Analyze each phone
        for i, phone in iterator:
            # Skip already analyzed
            if i <= start_index and phone.get("gemini_analysis", {}).get("analyzed"):
                analyzed_phones.append(phone)
                stats["successful"] += 1
                continue

            # Log progress
            if not TQDM_AVAILABLE:
                print(
                    f"   Analyzing {i}/{len(phones_to_analyze)}: {phone.get('title', 'Unknown')[:60]}..."
                )

            # Run analysis
            analysis = self.analyze_listing(phone)
            phone["gemini_analysis"] = analysis
            analyzed_phones.append(phone)

            # Handle fatal errors
            if self._handle_gemini_fatal(analysis, analyzed_phones, i, max_phones):
                break

            # Process results
            succ, fail, bon, crit, maj = self._process_gemini_result(phone, analysis)
            stats["successful"] += succ
            stats["failed"] += fail
            stats["bonus"] += bon
            stats["critical"] += crit
            stats["major"] += maj

            # Save checkpoint periodically
            if i % 10 == 0:
                self._save_checkpoint(analyzed_phones, i)

        # Add remaining phones
        analyzed_phones.extend(phones[max_phones:])

        # Clear checkpoint
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()

        # Log summary
        elapsed_time: float = time.time() - batch_start_time
        summary_stats: dict[str, int | float] = {**stats, "elapsed": elapsed_time}
        self._log_batch_summary(summary_stats)

        return analyzed_phones

    def get_analysis_summary(self, phone: dict) -> str:
        """Get human-readable summary"""
        analysis = phone.get("gemini_analysis", {})

        if not analysis.get("analyzed"):
            return ""

        severity = analysis.get("severity", "unknown")
        bonus_points = analysis.get("bonus_points", 0)
        bonus_reasons = analysis.get("bonus_reasons", [])
        issues = analysis.get("issues_found", [])

        severity_emoji = {"none": "✅", "minor": "⚠️", "major": "🔴", "critical": "❌"}

        summary = f"\n🤖 AI ANALYSIS ({severity_emoji.get(severity, '❓')} {severity.upper()}):\n"

        if bonus_points > 0:
            summary += f"   ⭐ EXCELLENT! Bonus: +{bonus_points} points\n"
            if bonus_reasons:
                for reason in bonus_reasons:
                    summary += f"      • {reason}\n"

        if analysis.get("is_suspicious"):
            summary += "   🚩 SUSPICIOUS!\n"
            for flag in analysis.get("suspicious_flags", []):
                summary += f"      • {flag}\n"

        if not analysis.get("is_usable"):
            summary += "   ⛔ NOT USABLE\n"

        if issues:
            summary += "   Defects:\n"
            for issue in issues:
                summary += f"      • {issue}\n"

        return summary
