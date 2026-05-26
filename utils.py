"""
Utility functions for message handling, markdown, and text processing.
"""

import html
import re
from typing import List

from config import config


def split_message(text: str, limit: int = config.MESSAGE_CHAR_LIMIT) -> List[str]:
    """
    Split long message into chunks respecting Telegram limits.
    
    Handles:
    - Paragraphs (preserves formatting)
    - Hard-split oversized single paragraphs
    - Guarantees every chunk <= limit
    
    Args:
        text: Text to split
        limit: Character limit per message (default: 4096)
    
    Returns:
        List of message chunks, each guaranteed <= limit
    """
    if len(text) <= limit:
        return [text]

    chunks: List[str] = []
    
    # Try splitting by paragraphs first
    paragraphs = text.split("\n\n")
    
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If a single paragraph exceeds limit, hard-split it
        if len(paragraph) > limit:
            # Save current chunk if exists
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            # Hard-split the oversized paragraph by sentences
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            temp_chunk = ""
            
            for sentence in sentences:
                if len(temp_chunk) + len(sentence) + 1 > limit:
                    if temp_chunk:
                        chunks.append(temp_chunk)
                    temp_chunk = sentence
                else:
                    temp_chunk += (f" {sentence}" if temp_chunk else sentence)
            
            if temp_chunk:
                chunks.append(temp_chunk)
        else:
            # Try to add paragraph to current chunk
            test_chunk = (
                current_chunk + f"\n\n{paragraph}"
                if current_chunk
                else paragraph
            )
            
            if len(test_chunk) <= limit:
                current_chunk = test_chunk
            else:
                # Paragraph doesn't fit, save current and start new
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph
    
    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    # Final validation: ensure no chunk exceeds limit
    result = []
    for chunk in chunks:
        if len(chunk) > limit:
            # Emergency: hard-split by characters
            for i in range(0, len(chunk), limit):
                result.append(chunk[i : i + limit])
        else:
            result.append(chunk)
    
    return result if result else [text[:limit]]


def escape_markdown(text: str) -> str:
    """
    Safely escape text for Markdown mode.
    
    Args:
        text: Raw text that may contain Markdown special chars
    
    Returns:
        Escaped text safe for Markdown parsing
    """
    # Escape special characters for Markdown
    special_chars = ["\\", "`", "*", "_", "{", "}", "[", "]", "(", ")", "#", "+", "-", ".", "!"]
    result = text
    for char in special_chars:
        result = result.replace(char, f"\\{char}")
    return result


def escape_html(text: str) -> str:
    """
    Safely escape text for HTML mode.
    
    Args:
        text: Raw text that may contain HTML special chars
    
    Returns:
        Escaped text safe for HTML parsing
    """
    return html.escape(text)


def safe_format_message(text: str, safe: bool = True) -> tuple[str, str]:
    """
    Format message safely for Telegram.
    
    Args:
        text: Message text (may be from LLM)
        safe: If True, use HTML with escaping. If False, return plain text.
    
    Returns:
        Tuple of (formatted_text, parse_mode)
    """
    if safe:
        # Use HTML mode with proper escaping
        return escape_html(text), "HTML"
    else:
        # Plain text (safest)
        return text, ""


def validate_prompt(prompt: str) -> bool:
    """
    Validate user prompt.
    
    Args:
        prompt: User prompt text
    
    Returns:
        True if valid
    
    Raises:
        ValueError: If validation fails
    """
    if not prompt or not isinstance(prompt, str):
        raise ValueError("Prompt must be a non-empty string")
    
    if len(prompt) > config.MAX_PROMPT_LENGTH:
        raise ValueError(
            f"Prompt too long: {len(prompt)} > {config.MAX_PROMPT_LENGTH} characters"
        )
    
    if len(prompt) < config.MIN_PROMPT_LENGTH:
        raise ValueError(
            f"Prompt too short: {len(prompt)} < {config.MIN_PROMPT_LENGTH} characters"
        )
    
    return True


def truncate_for_log(text: str, max_len: int = 100) -> str:
    """
    Safely truncate text for logging (avoid secrets in logs).
    
    Args:
        text: Text to truncate
        max_len: Maximum length
    
    Returns:
        Truncated text with ellipsis if needed
    """
    if not text:
        return ""
    
    s = str(text)
    if len(s) > max_len:
        return s[:max_len - 3] + "..."
    
    return s
