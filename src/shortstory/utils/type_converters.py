"""
Type conversion utilities for pipeline stages.

This module provides helper functions to convert between Pydantic models and dictionaries,
eliminating duplicated conversion logic throughout the codebase.

All functions handle both model and dict inputs for backward compatibility.
"""

from typing import Dict, Any, Optional, Tuple
from ..models import (
    PremiseModel,
    OutlineModel,
    CharacterModel,
    StoryMetadata,
)

logger = __import__('logging').getLogger(__name__)


def extract_premise_fields(premise: Any) -> Tuple[str, Optional[Any], Optional[str]]:
    """
    Extract idea, character, and theme from a premise (model or dict).
    
    Args:
        premise: PremiseModel instance or dict with premise data
        
    Returns:
        Tuple of (idea: str, character: Optional[Any], theme: Optional[str])
        
    Raises:
        ValueError: If premise is not PremiseModel or dict
    """
    if isinstance(premise, PremiseModel):
        idea = premise.idea.strip() if premise.idea else ""
        character = premise.character
        theme = premise.theme.strip() if premise.theme else None
        return idea, character, theme
    elif isinstance(premise, dict):
        idea = premise.get("idea", "").strip()
        character = premise.get("character")
        theme = premise.get("theme")
        if theme and isinstance(theme, str):
            theme = theme.strip()
        elif not theme:
            theme = None
        return idea, character, theme
    else:
        raise ValueError(
            f"Premise must be PremiseModel or dict, got {type(premise).__name__}"
        )


def premise_to_dict(premise: Any) -> Dict[str, Any]:
    """
    Convert premise to dictionary format.
    
    Args:
        premise: PremiseModel instance or dict
        
    Returns:
        Dictionary with premise data
    """
    if isinstance(premise, PremiseModel):
        if hasattr(premise, 'model_dump'):
            return premise.model_dump(exclude_none=True)
        else:
            return premise.dict(exclude_none=True)
    elif isinstance(premise, dict):
        return premise
    else:
        raise ValueError(
            f"Premise must be PremiseModel or dict, got {type(premise).__name__}"
        )


def outline_to_dict(outline: Any) -> Dict[str, Any]:
    """
    Convert outline to dictionary format.
    
    Args:
        outline: OutlineModel instance or dict
        
    Returns:
        Dictionary with outline data
    """
    if isinstance(outline, OutlineModel):
        if hasattr(outline, 'model_dump'):
            return outline.model_dump(exclude_none=True)
        else:
            return outline.dict(exclude_none=True)
    elif isinstance(outline, dict):
        return outline
    else:
        raise ValueError(
            f"Outline must be OutlineModel or dict, got {type(outline).__name__}"
        )


def character_to_dict(character: Any) -> Optional[Dict[str, Any]]:
    """
    Convert character to dictionary format.
    
    Args:
        character: CharacterModel instance, dict, or None
        
    Returns:
        Dictionary with character data, or None if character is None
    """
    if character is None:
        return None
    elif isinstance(character, CharacterModel):
        if hasattr(character, 'model_dump'):
            return character.model_dump(exclude_none=True)
        else:
            return character.dict(exclude_none=True)
    elif isinstance(character, dict):
        return character
    else:
        # Fallback: convert to description string wrapped in dict
        return {"description": str(character)}


def extract_character_info(character: Any) -> Optional[Dict[str, Any]]:
    """
    Extract character information for voice profile development.
    
    Handles various character formats and returns a normalized dict.
    
    Args:
        character: CharacterModel, dict, or None
        
    Returns:
        Dictionary with character info, or None if character is None
    """
    if character is None:
        return None
    
    if isinstance(character, CharacterModel):
        return character_to_dict(character)
    elif isinstance(character, dict):
        return character
    else:
        # Fallback for string or other types
        return {"description": str(character)}


def create_premise_dict_for_llm(
    idea: str,
    character: Optional[Any],
    theme: Optional[str]
) -> Dict[str, Any]:
    """
    Create a premise dictionary suitable for LLM functions.
    
    Args:
        idea: Story idea string
        character: CharacterModel, dict, or None
        theme: Theme string or None
        
    Returns:
        Dictionary with idea, character (as dict), and theme
    """
    character_dict = character_to_dict(character)
    return {
        "idea": idea,
        "character": character_dict or {},
        "theme": theme or ""
    }


def extract_outline_acts(outline: Any) -> Dict[str, str]:
    """
    Extract acts structure from outline.
    
    Args:
        outline: OutlineModel instance or dict
        
    Returns:
        Dictionary with 'beginning', 'middle', 'end' keys
    """
    if isinstance(outline, OutlineModel):
        acts = outline.acts or {}
        return {
            "beginning": acts.get("beginning", "setup"),
            "middle": acts.get("middle", "complication"),
            "end": acts.get("end", "resolution")
        }
    elif isinstance(outline, dict):
        acts = outline.get("acts", {})
        return {
            "beginning": acts.get("beginning", "setup"),
            "middle": acts.get("middle", "complication"),
            "end": acts.get("end", "resolution")
        }
    else:
        raise ValueError(
            f"Outline must be OutlineModel or dict, got {type(outline).__name__}"
        )


def extract_outline_genre(outline: Any) -> str:
    """
    Extract genre from outline.
    
    Args:
        outline: OutlineModel instance or dict
        
    Returns:
        Genre string (defaults to empty string if not found)
    """
    if isinstance(outline, OutlineModel):
        return outline.genre or ""
    elif isinstance(outline, dict):
        return outline.get("genre", "")
    else:
        return ""
