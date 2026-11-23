"""
Scaffold metadata extraction utilities.

This module provides helper functions for extracting and normalizing metadata
from scaffold structures and genre configurations. Handles various data formats
for backward compatibility.
"""

from typing import Dict, Any, Optional
from ..models import StoryMetadata
from .story_prompt_builder import Tone, Pace


def extract_pov(
    detailed_scaffold: Dict[str, Any],
    constraints: Dict[str, Any]
) -> str:
    """
    Extract point of view from scaffold or constraints.
    
    Handles both dict and nested dict formats for backward compatibility.
    
    Args:
        detailed_scaffold: Scaffold structure dictionary
        constraints: Genre constraints dictionary
        
    Returns:
        POV string (defaults to "flexible")
    """
    # Try to get POV from narrative_voice in scaffold
    narrative_voice = detailed_scaffold.get("narrative_voice", {})
    if isinstance(narrative_voice, dict):
        pov = narrative_voice.get("pov")
        if pov:
            return pov
    
    # Fall back to constraints
    return constraints.get("pov_preference", "flexible")


def extract_tone(
    detailed_scaffold: Dict[str, Any],
    constraints: Dict[str, Any]
) -> str:
    """
    Extract tone from scaffold or constraints.
    
    Handles both string and dict formats for backward compatibility.
    
    Args:
        detailed_scaffold: Scaffold structure dictionary
        constraints: Genre constraints dictionary
        
    Returns:
        Tone string (defaults to Tone.BALANCED.value)
    """
    tone_default = constraints.get("tone", Tone.BALANCED.value)
    
    # Try to get tone from scaffold
    tone_value = detailed_scaffold.get("tone", tone_default)
    
    # Handle dict format (e.g., {"emotional_register": "dark"})
    if isinstance(tone_value, dict):
        tone = tone_value.get("emotional_register", tone_default)
    else:
        # Handle string format or None
        tone = tone_value if tone_value else tone_default
    
    return tone


def extract_pace(
    detailed_scaffold: Dict[str, Any],
    constraints: Dict[str, Any]
) -> str:
    """
    Extract pace from scaffold or constraints.
    
    Handles both string and dict formats for backward compatibility.
    Pace can be in style_guidelines.pacing or directly in scaffold.pace.
    
    Args:
        detailed_scaffold: Scaffold structure dictionary
        constraints: Genre constraints dictionary
        
    Returns:
        Pace string (defaults to Pace.MODERATE.value)
    """
    pace_default = constraints.get("pace", Pace.MODERATE.value)
    
    # Try to get pace from style_guidelines first
    style_guidelines = detailed_scaffold.get("style_guidelines", {})
    if isinstance(style_guidelines, dict):
        pace = style_guidelines.get("pacing")
        if pace:
            return pace
    
    # Try direct pace field in scaffold
    pace_value = detailed_scaffold.get("pace")
    if isinstance(pace_value, str):
        return pace_value
    
    # Fall back to default
    return pace_default


def extract_sensory_focus(
    detailed_scaffold: Dict[str, Any],
    constraints: Dict[str, Any]
) -> list:
    """
    Extract sensory focus from scaffold or constraints.
    
    Args:
        detailed_scaffold: Scaffold structure dictionary
        constraints: Genre constraints dictionary
        
    Returns:
        List of sensory focus items (defaults to ["balanced"])
    """
    # Try to get from sensory_specificity in scaffold
    sensory_specificity = detailed_scaffold.get("sensory_specificity", {})
    if isinstance(sensory_specificity, dict):
        primary_senses = sensory_specificity.get("primary_senses")
        if primary_senses:
            return primary_senses if isinstance(primary_senses, list) else [primary_senses]
    
    # Fall back to constraints
    sensory_focus = constraints.get("sensory_focus", ["balanced"])
    return sensory_focus if isinstance(sensory_focus, list) else [sensory_focus]


def extract_scaffold_metadata(
    detailed_scaffold: Dict[str, Any],
    constraints: Dict[str, Any]
) -> StoryMetadata:
    """
    Extract and normalize metadata from scaffold structure.
    
    This is the main entry point for extracting metadata. It handles various
    data formats for backward compatibility and returns a validated StoryMetadata
    instance.
    
    Args:
        detailed_scaffold: Scaffold structure dictionary
        constraints: Genre constraints dictionary
        
    Returns:
        StoryMetadata instance with extracted tone, pace, and POV
        
    Example:
        >>> scaffold = {"narrative_voice": {"pov": "first person"}}
        >>> constraints = {"tone": "dark", "pace": "fast"}
        >>> metadata = extract_scaffold_metadata(scaffold, constraints)
        >>> assert metadata.pov == "first person"
        >>> assert metadata.tone == "dark"
    """
    pov = extract_pov(detailed_scaffold, constraints)
    tone = extract_tone(detailed_scaffold, constraints)
    pace = extract_pace(detailed_scaffold, constraints)
    
    return StoryMetadata(
        tone=tone,
        pace=pace,
        pov=pov,
    )
