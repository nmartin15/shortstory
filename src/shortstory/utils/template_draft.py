"""
Template-based story draft generation utilities.

This module provides functions for generating story drafts using template-based
approaches when LLM is unavailable. All functions are designed to be composable
and testable independently.
"""

from typing import Dict, Any, List, Tuple, Optional
from .word_count import WordCountValidator


def extract_character_info(character: Any) -> Dict[str, Any]:
    """
    Extract character information from various formats.
    
    Args:
        character: Character description (dict or string)
        
    Returns:
        Dictionary with char_desc, char_name, char_quirks, char_contradictions
    """
    if isinstance(character, dict):
        return {
            "char_desc": character.get("description", str(character)),
            "char_name": character.get("name", "the character"),
            "char_quirks": character.get("quirks", []),
            "char_contradictions": character.get("contradictions", ""),
        }
    else:
        return {
            "char_desc": str(character) if character else "",
            "char_name": "the character",
            "char_quirks": [],
            "char_contradictions": "",
        }


def determine_pov_pronouns(pov: str, char_name: str) -> Tuple[str, str]:
    """
    Determine POV pronouns based on point of view.
    
    Args:
        pov: Point of view string (e.g., "first person", "third person")
        char_name: Character name for third person POV
        
    Returns:
        Tuple of (pov_pronoun, pov_possessive)
    """
    if "first" in pov.lower():
        return "I", "my"
    elif "second" in pov.lower():
        return "you", "your"
    else:
        pronoun = char_name if char_name != "the character" else "they"
        return pronoun, "their"


def generate_beginning_section(
    idea: str,
    char_desc: str,
    char_name: str,
    char_quirks: List[str],
    beginning_label: str,
    pov_pronoun: str,
) -> List[str]:
    """
    Generate the beginning section of a story.
    
    Args:
        idea: Story idea/premise
        char_desc: Character description
        char_name: Character name
        char_quirks: List of character quirks
        beginning_label: Label for beginning section (e.g., "setup")
        pov_pronoun: POV pronoun ("I", "you", or character name)
        
    Returns:
        List of story text parts for beginning section
    """
    parts = []
    parts.append(f"## {beginning_label.title()}\n")
    
    if pov_pronoun == "I":
        parts.append(f"{idea}\n\n")
        if char_desc:
            parts.append(f"{char_desc}\n\n")
    else:
        parts.append(f"{idea}\n\n")
        if char_desc:
            display_name = char_name.capitalize() if char_name != "the character" else "The character"
            parts.append(f"{display_name}: {char_desc}\n\n")
    
    if char_quirks:
        quirks_text = ", ".join(char_quirks[:2])  # Limit to avoid word count
        if pov_pronoun == "I":
            parts.append(f"I had {quirks_text}.\n\n")
        elif pov_pronoun == "you":
            parts.append(f"You had {quirks_text}.\n\n")
        else:
            parts.append(f"{pov_pronoun.capitalize()} had {quirks_text}.\n\n")
    
    return parts


def generate_middle_section(
    theme: Optional[str],
    char_contradictions: str,
    middle_label: str,
    genre: str,
) -> List[str]:
    """
    Generate the middle section of a story.
    
    Args:
        theme: Story theme
        char_contradictions: Character contradictions
        middle_label: Label for middle section (e.g., "complication")
        genre: Story genre
        
    Returns:
        List of story text parts for middle section
    """
    parts = []
    parts.append(f"## {middle_label.title()}\n")
    
    if theme:
        parts.append(f"The question lingered: {theme}\n\n")
    
    if char_contradictions:
        parts.append(f"{char_contradictions}\n\n")
    
    # Add complication based on genre
    if "horror" in genre.lower():
        parts.append("Something shifted. The familiar became strange, the safe became uncertain.\n\n")
    elif "romance" in genre.lower():
        parts.append("Connection sparked, then faltered. The space between closeness and distance narrowed.\n\n")
    elif "crime" in genre.lower() or "noir" in genre.lower():
        parts.append("The pieces didn't fit. Every answer raised new questions.\n\n")
    else:
        parts.append("The situation deepened. What seemed simple revealed hidden layers.\n\n")
    
    return parts


def generate_end_section(
    theme: Optional[str],
    end_label: str,
    pov_pronoun: str,
    pov_possessive: str,
) -> List[str]:
    """
    Generate the end section of a story.
    
    Args:
        theme: Story theme
        end_label: Label for end section (e.g., "resolution")
        pov_pronoun: POV pronoun
        pov_possessive: POV possessive pronoun
        
    Returns:
        List of story text parts for end section
    """
    parts = []
    parts.append(f"## {end_label.title()}\n")
    
    # Generate a full-length ending with multiple paragraphs
    parts.append("The moment of resolution arrived not with fanfare, but with quiet recognition. ")
    parts.append(f"{pov_pronoun.capitalize()} understood that the journey had transformed {pov_possessive} understanding of {pov_possessive}self and {pov_possessive} place in the world.\n\n")
    
    parts.append("The details that had seemed insignificant now carried weight. ")
    parts.append("Each choice, each moment of hesitation or action, had led to this point. ")
    parts.append("The story found its shape not through grand gestures, but through the accumulation of small moments—each word chosen, each detail placed with intention.\n\n")
    
    parts.append(f"As the narrative drew to a close, the central question that had driven the story remained, but {pov_pronoun} had found {pov_possessive} own answer. ")
    parts.append(f"It wasn't the answer {pov_pronoun} had expected at the beginning, but it was {pov_possessive} own, earned through experience and reflection.\n\n")
    
    if theme:
        parts.append(f"The theme echoed throughout: {theme}. ")
        parts.append("But now it was no longer just a question—it was a lived experience, a truth discovered through the telling of the story itself.\n\n")
    
    return parts


def get_expansion_sections(char_name: str, pov_pronoun: str, pov_possessive: str) -> List[List[str]]:
    """
    Get expansion sections for story lengthening.
    
    Args:
        char_name: Character name
        pov_pronoun: POV pronoun
        pov_possessive: POV possessive pronoun
        
    Returns:
        List of expansion sections, each containing paragraphs
    """
    display_name = char_name if char_name != "the character" else "The character"
    
    return [
        [
            "The story continued to unfold, revealing layers of complexity that had been hidden beneath the surface.",
            f"{display_name} discovered that every action had consequences, every choice opened new paths while closing others."
        ],
        [
            "In the quiet moments between the dramatic events, there were opportunities for reflection.",
            f"The character grappled with {pov_possessive} own nature, questioning assumptions and discovering hidden strengths.",
            "These internal struggles were as important as the external conflicts, shaping the character's growth throughout the narrative."
        ],
        [
            f"The world around {pov_pronoun} responded to {pov_possessive} choices, creating ripples that extended far beyond {pov_possessive} immediate awareness.",
            "Other characters entered and left the story, each bringing their own perspectives and challenges.",
            "These interactions deepened the narrative, adding texture and complexity to the central story."
        ],
        [
            "As the story progressed, the stakes continued to rise.",
            "What had begun as a simple situation evolved into something more profound, testing the character's resolve and forcing difficult decisions.",
            "Each challenge revealed new aspects of the character's personality, showing both strengths and vulnerabilities."
        ],
        [
            "The resolution came gradually, not as a sudden revelation but as a series of realizations that built upon each other.",
            "The character came to understand that some questions don't have simple answers, and that growth often comes from accepting complexity rather than seeking clarity."
        ]
    ]


def get_filler_templates(char_name: str, pov_pronoun: str) -> List[str]:
    """
    Get filler templates for story lengthening.
    
    Args:
        char_name: Character name
        pov_pronoun: POV pronoun
        
    Returns:
        List of filler template strings
    """
    display_name = char_name if char_name != "the character" else "The character"
    
    return [
        (
            f"\n\nThe narrative wove together multiple threads, each contributing to the overall tapestry of the story. "
            f"{display_name} navigated through challenges both internal and external, "
            f"learning that the journey itself was as important as the destination.\n\n"
        ),
        (
            "\n\nThe story continued to develop, revealing new dimensions and deepening the reader's understanding of the characters and their world. "
            "Each scene built upon the previous ones, creating a rich and immersive narrative experience.\n\n"
        ),
        (
            f"\n\n{pov_pronoun.capitalize()} reflected on the path that had led to this moment, recognizing how each decision had shaped the outcome. "
            f"The themes of the story resonated more deeply now, having been tested through experience.\n\n"
        ),
    ]


def expand_story_to_target_length(
    story_parts: List[str],
    current_words: int,
    target_words: int,
    word_validator: WordCountValidator,
    char_name: str,
    pov_pronoun: str,
    pov_possessive: str,
) -> List[str]:
    """
    Expand story to reach target word count.
    
    Args:
        story_parts: Current list of story text parts
        current_words: Current word count
        target_words: Target word count
        word_validator: WordCountValidator instance
        char_name: Character name
        pov_pronoun: POV pronoun
        pov_possessive: POV possessive pronoun
        
    Returns:
        Updated list of story text parts
    """
    if current_words >= target_words:
        return story_parts
    
    # Get expansion sections
    expansion_sections = get_expansion_sections(char_name, pov_pronoun, pov_possessive)
    
    # Add expansion sections until target is met
    for section in expansion_sections:
        if current_words >= target_words:
            break
        for paragraph in section:
            if current_words >= target_words:
                break
            story_parts.append(f"\n\n{paragraph}")
            # Only count words every few additions to reduce overhead
            if len(story_parts) % 3 == 0:
                joined_text = "".join(story_parts)
                current_words = word_validator.count_words(joined_text)
    
    # Final word count check before filler
    joined_text = "".join(story_parts)
    current_words = word_validator.count_words(joined_text)
    
    # If still not enough, add contextual filler
    if current_words < target_words:
        filler_templates = get_filler_templates(char_name, pov_pronoun)
        max_filler_iterations = 20  # Prevent infinite loops
        iteration = 0
        template_index = 0
        
        while current_words < target_words and iteration < max_filler_iterations:
            # Rotate through filler templates for variety
            filler_template = filler_templates[template_index % len(filler_templates)]
            story_parts.append(filler_template)
            template_index += 1
            iteration += 1
            # Count words every 2 iterations to reduce overhead
            if iteration % 2 == 0:
                joined_text = "".join(story_parts)
                current_words = word_validator.count_words(joined_text)
    
    return story_parts


def generate_template_draft(
    idea: str,
    character: Any,
    theme: Optional[str],
    outline: Any,
    scaffold: Dict[str, Any],
    word_validator: WordCountValidator,
) -> str:
    """
    Generate a complete template-based story draft.
    
    This is the main entry point for template draft generation. It orchestrates
    all the component functions to create a complete story.
    
    Args:
        idea: The story idea/premise
        character: Character description (dict or string)
        theme: The story's theme
        outline: Outline structure (OutlineModel or dict)
        scaffold: Scaffold data with POV, tone, etc.
        word_validator: WordCountValidator instance
        
    Returns:
        Generated story text following the template structure
    """
    # Extract character info
    char_info = extract_character_info(character)
    char_desc = char_info["char_desc"]
    char_name = char_info["char_name"]
    char_quirks = char_info["char_quirks"]
    char_contradictions = char_info["char_contradictions"]
    
    # Get outline structure using type converter
    from .type_converters import extract_outline_acts, extract_outline_genre
    acts = extract_outline_acts(outline)
    beginning_label = acts.get("beginning", "setup")
    middle_label = acts.get("middle", "complication")
    end_label = acts.get("end", "resolution")
    outline_genre = extract_outline_genre(outline)
    
    # Get POV from scaffold and determine pronouns
    pov = scaffold.get("pov", "flexible")
    pov_pronoun, pov_possessive = determine_pov_pronouns(pov, char_name)
    
    # Generate story sections
    story_parts = []
    story_parts.extend(generate_beginning_section(
        idea, char_desc, char_name, char_quirks, beginning_label, pov_pronoun
    ))
    story_parts.extend(generate_middle_section(
        theme, char_contradictions, middle_label, outline_genre
    ))
    story_parts.extend(generate_end_section(
        theme, end_label, pov_pronoun, pov_possessive
    ))
    
    # Calculate target word count
    joined_text = "".join(story_parts)
    current_words = word_validator.count_words(joined_text)
    target_words = max(2000, int(word_validator.max_words * 0.3))  # At least 2000 words or 30% of max
    
    # Expand story to target length
    story_parts = expand_story_to_target_length(
        story_parts, current_words, target_words, word_validator,
        char_name, pov_pronoun, pov_possessive
    )
    
    # Final join - only done once at the end
    return "".join(story_parts)
