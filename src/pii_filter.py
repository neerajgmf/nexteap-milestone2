"""
PII Filter Module
Removes personally identifiable information from review text before LLM processing.
"""

import re
from typing import List, Tuple


# Regex patterns for common PII
PII_PATTERNS: List[Tuple[str, str, str]] = [
    # Email addresses
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', 'email'),
    
    # Phone numbers (Indian format)
    (r'\b(?:\+91[-.\s]?)?[6-9]\d{9}\b', '[PHONE]', 'phone_in'),
    
    # Phone numbers (generic)
    (r'\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE]', 'phone_generic'),
    
    # URLs
    (r'https?://[^\s]+', '[URL]', 'url'),
    (r'www\.[^\s]+', '[URL]', 'url_www'),
    
    # Indian PAN numbers
    (r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', '[PAN]', 'pan'),
    
    # Indian Aadhaar (12 digits, often space-separated)
    (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[AADHAAR]', 'aadhaar'),
    
    # Account numbers (8-18 digits)
    (r'\b\d{8,18}\b', '[ACCOUNT]', 'account'),
    
    # UPI IDs
    (r'\b[a-zA-Z0-9._-]+@[a-zA-Z]{3,}\b', '[UPI]', 'upi'),
    
    # Names that look like full names (Title Case with 2-3 words)
    # This is aggressive - only use if needed
    # (r'\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b', '[NAME]', 'name'),
]


def filter_pii(text: str, aggressive: bool = False) -> str:
    """
    Remove PII from text using regex patterns.
    
    Args:
        text: Input text to clean
        aggressive: If True, also attempt to filter names (may have false positives)
        
    Returns:
        Cleaned text with PII replaced by tokens
    """
    if not text:
        return ""
    
    cleaned = text
    
    for pattern, replacement, _ in PII_PATTERNS:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    
    # Aggressive name filtering (optional)
    if aggressive:
        # Match patterns like "Mr. John", "Ms. Jane Doe"
        cleaned = re.sub(r'\b(?:Mr|Mrs|Ms|Dr|Shri|Smt)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b', '[NAME]', cleaned)
    
    # Clean up multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def detect_pii(text: str) -> List[dict]:
    """
    Detect PII in text without removing it.
    
    Returns:
        List of detected PII with type and matched text
    """
    if not text:
        return []
    
    detected = []
    
    for pattern, _, pii_type in PII_PATTERNS:
        matches = re.finditer(pattern, text, flags=re.IGNORECASE)
        for match in matches:
            detected.append({
                'type': pii_type,
                'match': match.group(),
                'start': match.start(),
                'end': match.end()
            })
    
    return detected


def batch_filter_pii(texts: List[str], aggressive: bool = False) -> List[str]:
    """Filter PII from a list of texts."""
    return [filter_pii(t, aggressive) for t in texts]


# Quick test
if __name__ == "__main__":
    test_cases = [
        "Contact me at john.doe@email.com or +91-9876543210",
        "My account 1234567890123456 has issues",
        "Check www.example.com for details",
        "UPI: user@okaxis works great",
        "PAN ABCDE1234F not updating",
        "Great app! Love it!",  # No PII
    ]
    
    print("PII Filter Test:")
    print("-" * 50)
    for text in test_cases:
        cleaned = filter_pii(text)
        detected = detect_pii(text)
        print(f"Original: {text}")
        print(f"Cleaned:  {cleaned}")
        print(f"Detected: {[d['type'] for d in detected]}")
        print()

