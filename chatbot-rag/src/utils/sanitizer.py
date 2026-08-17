"""Response sanitizer utility for cleaning HTML and removing sensitive data."""

import re
from typing import List


class ResponseSanitizer:
    """Utility class for sanitizing responses and removing sensitive information."""

    def __init__(self, allowed_tags: List[str] = None):
        """
        Initialize the sanitizer.

        Args:
            allowed_tags: List of HTML tags that are allowed (default: basic formatting tags)
        """
        self.allowed_tags = allowed_tags or [
            "p",
            "br",
            "strong",
            "em",
            "ul",
            "ol",
            "li",
        ]
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        # Pattern for dangerous tags
        self.script_pattern = re.compile(
            r"<script.*?</script>", re.DOTALL | re.IGNORECASE
        )
        self.dangerous_tag_pattern = re.compile(
            r"<(iframe|object|embed|applet|meta|link|style).*?</\1>",
            re.DOTALL | re.IGNORECASE,
        )
        # Pattern for inline event handlers
        self.event_handler_pattern = re.compile(
            r'\s*on\w+\s*=\s*["\'].*?["\']', re.IGNORECASE
        )
        # Pattern for javascript: protocol
        self.javascript_protocol_pattern = re.compile(r"javascript:", re.IGNORECASE)

        # Sensitive data patterns
        self.email_pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )
        self.phone_pattern = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
        self.ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

    def sanitize_html(self, html: str) -> str:
        """
        Sanitize HTML by removing dangerous tags and attributes.

        Args:
            html: HTML string to sanitize

        Returns:
            Sanitized HTML string
        """
        if not html:
            return ""

        # Remove script tags
        html = self._strip_scripts(html)

        # Remove dangerous tags
        html = self.dangerous_tag_pattern.sub("", html)

        # Remove inline event handlers
        html = self.event_handler_pattern.sub("", html)

        # Remove javascript: protocol
        html = self.javascript_protocol_pattern.sub("", html)

        return html.strip()

    def remove_sensitive_data(self, text: str, redact_char: str = "X") -> str:
        """
        Remove or redact sensitive data like emails, phone numbers, SSNs.

        Args:
            text: Text to sanitize
            redact_char: Character to use for redaction

        Returns:
            Text with sensitive data removed
        """
        if not text:
            return ""

        # Redact emails
        text = self.email_pattern.sub(lambda m: redact_char * len(m.group()), text)

        # Redact phone numbers
        text = self.phone_pattern.sub(lambda m: redact_char * len(m.group()), text)

        # Redact SSNs
        text = self.ssn_pattern.sub(lambda m: redact_char * len(m.group()), text)

        return text

    def validate_url(self, url: str) -> bool:
        """
        Validate if a URL is safe (not javascript: protocol, etc.).

        Args:
            url: URL to validate

        Returns:
            True if URL is safe, False otherwise
        """
        if not url:
            return False

        # Check for javascript: protocol
        if self.javascript_protocol_pattern.search(url):
            return False

        # Check for data: protocol (can be used for XSS)
        if url.strip().lower().startswith("data:"):
            return False

        # Only allow http, https, and relative URLs
        url_lower = url.strip().lower()
        if url_lower.startswith(("http://", "https://", "/", "./")):
            return True

        return False

    def _strip_scripts(self, html: str) -> str:
        """
        Remove all script tags from HTML.

        Args:
            html: HTML string

        Returns:
            HTML without script tags
        """
        return self.script_pattern.sub("", html)
