"""
Rule-based text revision utilities.

This module provides functions for applying rule-based text revisions when LLM
is unavailable. All functions use optimized regex patterns for performance.
"""

import re
from typing import Dict, Any, Optional, Tuple


# Cliché replacements - common clichés mapped to more specific alternatives
CLICHE_REPLACEMENTS: Dict[str, str] = {
    "dark and stormy night": "a night that swallowed sound",
    "once upon a time": "it began",
    "in the nick of time": "just as the moment shifted",
    "all hell broke loose": "everything fractured",
    "calm before the storm": "the pause before change",
    "needle in a haystack": "something nearly impossible to find",
    "tip of the iceberg": "only the surface",
    "dead as a doornail": "completely still",
    "raining cats and dogs": "rain that pounded",
    "piece of cake": "effortless",
    "blessing in disguise": "something that seemed wrong but wasn't",
    "beat around the bush": "avoid the point",
    "break the ice": "create connection",
    "hit the nail on the head": "exactly right",
    "let the cat out of the bag": "reveal the secret",
}

# Vague language replacements - remove vague intensifiers
VAGUE_REPLACEMENTS: Dict[str, str] = {
    " very ": " ",
    " really ": " ",
    " quite ": " ",
    " somewhat ": " ",
    " kind of ": " ",
    " sort of ": " ",
}

# Redundant phrase replacements - simplify wordy phrases
REDUNDANT_PHRASES: Dict[str, str] = {
    "due to the fact that": "because",  # Longest first
    "the fact that": "that",
    "in order to": "to",
}


def _build_cliche_pattern() -> Tuple[re.Pattern, Dict[str, str]]:
    """
    Build regex pattern for cliché replacement.
    
    Returns:
        Tuple of (compiled regex pattern, lowercase mapping dict)
    """
    # Create mapping of lowercase clichés to replacements for lookup
    cliche_lower_map: Dict[str, str] = {
        cliche.lower(): replacement 
        for cliche, replacement in CLICHE_REPLACEMENTS.items()
    }
    
    # Sort by length (longest first) to avoid partial matches
    sorted_cliches = sorted(CLICHE_REPLACEMENTS.keys(), key=len, reverse=True)
    pattern = re.compile(
        "|".join(re.escape(cliche) for cliche in sorted_cliches),
        re.IGNORECASE
    )
    
    return pattern, cliche_lower_map


def _build_vague_pattern() -> re.Pattern:
    """
    Build regex pattern for vague language removal.
    
    Returns:
        Compiled regex pattern
    """
    return re.compile("|".join(re.escape(vague) for vague in VAGUE_REPLACEMENTS.keys()))


def _build_redundant_pattern() -> Tuple[re.Pattern, Dict[str, str]]:
    """
    Build regex pattern for redundant phrase replacement.
    
    Returns:
        Tuple of (compiled regex pattern, lowercase mapping dict)
    """
    # Create mapping of lowercase phrases to replacements
    redundant_lower_map: Dict[str, str] = {
        phrase.lower(): replacement 
        for phrase, replacement in REDUNDANT_PHRASES.items()
    }
    
    # Sort by length (longest first) to ensure longest matches are found first
    sorted_phrases = sorted(REDUNDANT_PHRASES.keys(), key=len, reverse=True)
    pattern = re.compile(
        "|".join(re.escape(phrase) for phrase in sorted_phrases),
        re.IGNORECASE
    )
    
    return pattern, redundant_lower_map


# Compile patterns once at module level for performance
_CLICHE_PATTERN, _CLICHE_LOWER_MAP = _build_cliche_pattern()
_VAGUE_PATTERN = _build_vague_pattern()
_REDUNDANT_PATTERN, _REDUNDANT_LOWER_MAP = _build_redundant_pattern()


def replace_cliches(text: str) -> str:
    """
    Replace common clichés with more specific language.
    
    Uses optimized regex pattern to replace all clichés in a single pass.
    Case-insensitive matching.
    
    Args:
        text: Text to process
        
    Returns:
        Text with clichés replaced
    """
    def cliche_replacer(match: re.Match) -> str:
        """Replace matched cliché with more specific alternative."""
        matched_text = match.group(0).lower()
        return _CLICHE_LOWER_MAP.get(matched_text, match.group(0))
    
    return _CLICHE_PATTERN.sub(cliche_replacer, text)


def remove_vague_language(text: str) -> str:
    """
    Remove vague intensifiers and qualifiers.
    
    Removes words like "very", "really", "quite", etc. to sharpen language.
    
    Args:
        text: Text to process
        
    Returns:
        Text with vague language removed
    """
    return _VAGUE_PATTERN.sub(lambda m: VAGUE_REPLACEMENTS[m.group(0)], text)


def replace_redundant_phrases(text: str) -> str:
    """
    Replace redundant phrases with simpler alternatives.
    
    Replaces wordy phrases like "due to the fact that" with "because".
    Case-insensitive matching.
    
    Args:
        text: Text to process
        
    Returns:
        Text with redundant phrases replaced
    """
    def redundant_replacer(match: re.Match) -> str:
        """Replace matched redundant phrase with simpler alternative."""
        matched_text = match.group(0).lower()
        return _REDUNDANT_LOWER_MAP.get(matched_text, match.group(0))
    
    return _REDUNDANT_PATTERN.sub(redundant_replacer, text)


def apply_rule_based_revisions(
    text: str,
    distinctiveness_check: Optional[Dict[str, Any]] = None
) -> str:
    """
    Apply all rule-based text revisions.
    
    This is the main entry point for rule-based revisions. It applies:
    1. Cliché replacement
    2. Vague language removal
    3. Redundant phrase replacement
    
    Uses optimized regex patterns to perform all replacements efficiently,
    especially with large texts. All replacements are combined into single
    regex patterns to minimize passes through the text.
    
    Args:
        text: Text to revise
        distinctiveness_check: Results from check_distinctiveness 
            (currently unused but kept for API compatibility)
        
    Returns:
        Revised text with clichés replaced, vague language removed, and
        redundant phrases simplified
        
    Example:
        >>> text = "It was a very dark and stormy night."
        >>> revised = apply_rule_based_revisions(text)
        >>> print(revised)
        "It was a night that swallowed sound."
    """
    if not text:
        return text
    
    # Apply all revisions in sequence
    revised_text = replace_cliches(text)
    revised_text = remove_vague_language(revised_text)
    revised_text = replace_redundant_phrases(revised_text)
    
    return revised_text
