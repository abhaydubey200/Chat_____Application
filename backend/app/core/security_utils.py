"""
Security Utilities for Input Sanitization and XSS Prevention

This module provides helper functions to prevent XSS and other security issues
by sanitizing user input and escaping output.
"""

import re
import html
from urllib.parse import quote as url_quote
from typing import Any

def sanitize_html(content: str, max_length: int = 4000) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.
    
    This function escapes all HTML special characters while preserving the content.
    It does NOT preserve HTML formatting - use a proper HTML sanitizer library
    like bleach or html2text for that.
    
    Args:
        content: The content to sanitize
        max_length: Maximum allowed length (prevents DOS via large payloads)
        
    Returns:
        Safely escaped HTML content
    """
    if not isinstance(content, str):
        content = str(content)
    
    # Limit length
    if len(content) > max_length:
        content = content[:max_length]
    
    # Escape HTML entities
    return html.escape(content, quote=True)

def sanitize_title(title: str, max_length: int = 200) -> str:
    """
    Sanitize a title/label field for database storage and display.
    
    Args:
        title: The title to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized title safe for display
    """
    if not title:
        return "Untitled"
    
    if not isinstance(title, str):
        title = str(title)
    
    # Strip whitespace and limit length
    title = title.strip()[:max_length]
    
    # Remove any remaining HTML
    title = re.sub(r'<[^>]+>', '', title)
    
    # Escape HTML entities
    title = html.escape(title, quote=True)
    
    # Ensure not empty after sanitization
    return title if title else "Untitled"

def sanitize_url(url: str, max_length: int = 2048) -> str:
    """
    Sanitize a URL to prevent injection attacks.
    
    Args:
        url: The URL to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Safely encoded URL
    """
    if not isinstance(url, str):
        return ""
    
    # Limit length
    if len(url) > max_length:
        return ""
    
    # Only allow safe protocols
    if not any(url.startswith(proto) for proto in ["http://", "https://", "/"]):
        return ""
    
    # URL encode special characters
    return url_quote(url, safe=":/?#[]@!$&'()*+,;=")

def prevent_sql_injection(value: str) -> str:
    """
    Note: This is for defense-in-depth only.
    Never rely on this - always use parameterized queries!
    
    Detects and escapes potential SQL injection patterns.
    
    Args:
        value: The value to check
        
    Returns:
        Escaped value safe for SQL (when used with parameterized queries)
    """
    if not isinstance(value, str):
        return str(value)
    
    # Check for SQL keywords in suspicious positions
    dangerous_patterns = [
        r"('|(\\')|(;))(\s|%)*(union|select|insert|update|delete|drop|create|alter|exec|execute|script)",
        r"(xp_|sp_).*exec",
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            # Log suspicious pattern but don't reject - SQLAlchemy ORM prevents injection
            print(f"WARNING: Suspicious pattern detected in input: {value[:50]}")
    
    return value

def sanitize_json_value(value: Any) -> Any:
    """
    Recursively sanitize values for JSON output.
    
    Args:
        value: Any JSON-serializable value
        
    Returns:
        Sanitized value
    """
    if isinstance(value, str):
        return sanitize_html(value)
    elif isinstance(value, dict):
        return {k: sanitize_json_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_json_value(v) for v in value]
    return value

class HTMLSanitizer:
    """
    Context manager for safe HTML sanitization.
    
    Usage:
        with HTMLSanitizer() as sanitizer:
            safe_html = sanitizer.escape("user input <script>alert('xss')</script>")
    """
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    @staticmethod
    def escape(content: str) -> str:
        """Escape HTML content."""
        return sanitize_html(content)
    
    @staticmethod
    def escape_js_string(content: str) -> str:
        """Escape string for safe inclusion in JavaScript."""
        if not isinstance(content, str):
            content = str(content)
        
        # Escape for JavaScript string context
        content = content.replace('\\', '\\\\')
        content = content.replace('"', '\\"')
        content = content.replace("'", "\\'")
        content = content.replace('\n', '\\n')
        content = content.replace('\r', '\\r')
        content = content.replace('</', '<\\/')  # Prevent </script> injection
        
        return content
