"""
ShortStoryPipeline - Main pipeline class

See pipeline.md for architecture documentation.
See CONCEPTS.md for core principles and terminology.
"""

import re
import logging
from typing import Optional, Dict, Any

from .models import (
    PremiseModel,
    OutlineModel,
    CharacterModel,
    StoryMetadata,
)
from .utils import (
    WordCountValidator,
    check_distinctiveness,
    validate_premise,
    validate_story_voices,
)
from .utils.type_converters import (
    extract_premise_fields,
    premise_to_dict,
    outline_to_dict,
    character_to_dict,
    extract_character_info,
    create_premise_dict_for_llm,
    extract_outline_acts,
    extract_outline_genre,
)
from .utils.template_draft import generate_template_draft
from .utils.rule_based_revisions import apply_rule_based_revisions
from .utils.scaffold_metadata import (
    extract_scaffold_metadata,
    extract_sensory_focus,
)
from .utils.llm import (
    generate_story_draft,
    revise_story_text,
    generate_outline_structure,
    generate_scaffold_structure,
)
from .genres import get_genre_config

logger = logging.getLogger(__name__)


class ShortStoryPipeline:
    """
    Modular pipeline for short story creation.
    
    Stages:
    1. Premise capture
    2. Outline generation
    3. Scaffolding
    4. Drafting
    5. Revision
    """
    
    def __init__(self, max_word_count=7500, genre=None, genre_config=None):
        """
        Initialize the pipeline.
        
        Args:
            max_word_count: Maximum word count (default: 7500)
            genre: Genre name (optional)
            genre_config: Genre configuration dict (optional)
        """
        self.premise: Optional[PremiseModel] = None
        self.outline: Optional[OutlineModel] = None
        self._scaffold_data: Optional[Dict[str, Any]] = None
        self._draft_data: Optional[Dict[str, Any]] = None
        self._revised_draft_data: Optional[Dict[str, Any]] = None
        self.word_validator = WordCountValidator(max_word_count)
        self.genre = genre
        self.genre_config = genre_config
    
    def capture_premise(self, idea, character, theme, validate=True):
        """
        Stage 1: Capture premise with distinctiveness validation.
        
        Args:
            idea: Initial concept (must avoid generic setups)
            character: Character sketch with quirks, contradictions, voice markers (dict or CharacterModel)
            theme: Central question (resonant, not clichéd)
            validate: If True, run distinctiveness validation
        
        Returns:
            PremiseModel instance with validation results
        """
        # Validate premise
        validation_result = None
        if validate:
            validation_result = validate_premise(idea, character, theme)
            if not validation_result["is_valid"]:
                raise ValueError(
                    f"Premise validation failed: {validation_result['errors']}"
                )
        
        # Create CharacterModel if character is a dict, or use existing CharacterModel
        if isinstance(character, dict):
            character_model = CharacterModel(**character)
        elif isinstance(character, CharacterModel):
            character_model = character
        else:
            character_model = None
        
        # Create PremiseModel
        self.premise = PremiseModel(
            idea=idea,
            character=character_model,
            theme=theme,
            validation=validation_result,
        )
        return self.premise
    
    def _get_genre_config(self, genre):
        """
        Get genre configuration (helper method to avoid DRY violation).
        
        Args:
            genre: Genre name
            
        Returns:
            Genre configuration dict (never None, returns empty dict if not found)
        """
        if genre:
            config = get_genre_config(genre)
            return config if config is not None else {}
        return {}
    
    def generate_outline(self, premise=None, genre=None, use_llm=True):
        """
        Stage 2: Generate outline with unexpected beats.
        
        Generates a detailed outline structure with specific beats for beginning, middle, and end.
        Uses LLM if available, with template fallback. Validates against predictable patterns.
        
        Args:
            premise: PremiseModel or dict (uses self.premise if None)
            genre: Genre name (uses self.genre if None)
            use_llm: If True, use LLM for generation (default: True)
        
        Returns:
            OutlineModel instance with detailed beats for beginning, middle, end following genre structure
        """
        if premise is None:
            premise = self.premise
        if premise is None:
            raise ValueError("Cannot generate outline without premise. Call capture_premise() first.")
        
        if genre is None:
            genre = self.genre
        
        # Get genre-specific outline structure
        genre_config = self._get_genre_config(genre)
        # genre_config is always a dict (never None)
        outline_structure = genre_config.get("outline", ["setup", "complication", "resolution"])
        framework = genre_config.get("framework", "narrative_arc")
        
        # Extract premise elements using type converter
        idea, character, theme = extract_premise_fields(premise)
        
        if not idea:
            raise ValueError("Cannot generate outline without story idea in premise.")
        
        # Build premise dict for generate_outline_structure
        premise_dict = create_premise_dict_for_llm(idea, character, theme)
        
        # Generate detailed outline structure
        # Note: generate_outline_structure doesn't actually use LLM currently,
        # so we pass None to avoid client initialization
        detailed_outline = generate_outline_structure(
            premise=premise_dict,
            genre=genre or "General Fiction",
            genre_config=genre_config,
            client=None,  # Pass None to avoid client initialization (not used anyway)
        )
        
        # Validate outline against predictable beats
        from .cliche_detector import get_cliche_detector
        cliche_detector = get_cliche_detector()
        
        # Check for predictable beats in the outline
        outline_text = f"{detailed_outline.get('beginning', {}).get('hook', '')} {detailed_outline.get('middle', {}).get('complication', '')} {detailed_outline.get('end', {}).get('resolution', '')}"
        beat_check = cliche_detector._detect_predictable_beats(outline_text)
        
        # Build OutlineModel
        acts = {
            "beginning": outline_structure[0] if len(outline_structure) > 0 else "setup",
            "middle": outline_structure[1] if len(outline_structure) > 1 else "complication",
            "end": outline_structure[2] if len(outline_structure) > 2 else "resolution"
        }
        
        # Ensure genre is a string (default to "General Fiction" if None)
        genre_str = genre if genre else "General Fiction"
        
        self.outline = OutlineModel(
            genre=genre_str,
            framework=framework,
            structure=outline_structure,
            acts=acts,
        )
        
        # Store detailed outline data in a separate dict for backward compatibility
        # (OutlineModel doesn't include all the detailed beats, so we keep them accessible)
        self._outline_details = {
            "beginning": detailed_outline.get("beginning", {}),
            "middle": detailed_outline.get("middle", {}),
            "end": detailed_outline.get("end", {}),
            "memorable_moments": detailed_outline.get("memorable_moments", []),
            "voice_opportunities": detailed_outline.get("voice_opportunities", []),
            "beat_validation": {
                "predictable_beats_found": len(beat_check),
                "beats": beat_check,
                "is_valid": len(beat_check) == 0,
            }
        }
        
        return self.outline
    
    def scaffold(self, outline=None, genre=None, use_llm=True):
        """
        Stage 3: Establish distinctive voice, POV, tone, style.
        
        Generates detailed voice profiles, conflict mapping, and prose characteristics
        that establish distinctive narrative and character voices. Uses LLM if available,
        with template fallback. Integrates Character Voice Analyzer for voice development.
        
        Applies genre-specific constraints (tone, pace, POV preference, sensory focus).
        
        NOTE: Genre constraints are GUIDELINES, not rigid rules. Distinctiveness
        and memorability remain the primary goals. Genre provides structure,
        but every story must have unique voice and avoid generic elements.
        
        Args:
            outline: Outline object (uses self.outline if None)
            genre: Genre name (uses self.genre if None)
            use_llm: If True, use LLM for generation (default: True)
        
        Returns:
            Scaffold object with detailed voice profiles, conflicts, and style guidelines
        """
        if outline is None:
            outline = self.outline
        if outline is None:
            raise ValueError("Cannot scaffold without outline. Call generate_outline() first.")
        
        if self.premise is None:
            raise ValueError("Cannot scaffold without premise. Call capture_premise() first.")
        
        if genre is None:
            genre = self.genre
        
        # Get genre-specific constraints
        genre_config = self._get_genre_config(genre)
        # genre_config is always a dict (never None)
        constraints = genre_config.get("constraints", {})
        
        # Convert premise and outline to dicts for generate_scaffold_structure
        premise_dict = premise_to_dict(self.premise)
        outline_dict = outline_to_dict(outline)
        
        # Generate detailed scaffold structure
        # Note: generate_scaffold_structure doesn't actually use LLM currently,
        # so we pass None to avoid client initialization
        detailed_scaffold = generate_scaffold_structure(
            premise=premise_dict,
            outline=outline_dict,
            genre_config=genre_config,
            client=None,  # Pass None to avoid client initialization (not used anyway)
        )
        
        # Extract character info from premise for voice profile development
        _, character, _ = extract_premise_fields(self.premise)
        character_info = extract_character_info(character)
        
        # If we have character info, enhance voice profiles
        if character_info and detailed_scaffold.get("character_voices"):
            char_name = character_info.get("name", list(detailed_scaffold.get("character_voices", {}).keys())[0] if detailed_scaffold.get("character_voices") else "character")
            
            # Add voice markers from character quirks and contradictions
            if char_name in detailed_scaffold["character_voices"]:
                voice_profile = detailed_scaffold["character_voices"][char_name]
                
                # Add quirks as voice markers
                quirks = character_info.get("quirks", [])
                if quirks and not isinstance(quirks, list):
                    quirks = [quirks]
                
                if quirks:
                    existing_markers = voice_profile.get("voice_markers", [])
                    for quirk in quirks[:3]:  # Limit to top 3
                        marker = f"Quirk manifests in voice: {quirk}"
                        if marker not in existing_markers:
                            existing_markers.append(marker)
                    voice_profile["voice_markers"] = existing_markers
                
                # Add contradictions as distinctive traits
                contradictions = character_info.get("contradictions", "")
                if contradictions:
                    existing_traits = voice_profile.get("distinctive_traits", [])
                    trait = f"Voice reflects contradiction: {contradictions[:50]}"
                    if trait not in existing_traits:
                        existing_traits.append(trait)
                    voice_profile["distinctive_traits"] = existing_traits
        
        # Extract metadata fields using helper functions
        metadata = extract_scaffold_metadata(detailed_scaffold, constraints)
        
        # Build complete scaffold structure
        scaffold_data = {
            "outline": outline,
            "genre": genre,
            "constraints": constraints,
            "framework": genre_config.get("framework", "narrative_arc"),
            # Detailed voice development
            "narrative_voice": detailed_scaffold.get("narrative_voice", {}),
            "character_voices": detailed_scaffold.get("character_voices", {}),
            "tone_detail": detailed_scaffold.get("tone", {}),  # Full tone dict
            "conflicts": detailed_scaffold.get("conflicts", {}),
            "sensory_specificity": detailed_scaffold.get("sensory_specificity", {}),
            "style_guidelines": detailed_scaffold.get("style_guidelines", {}),
            # Use StoryMetadata for validated metadata fields
            "metadata": metadata,
            # Backward compatibility fields (extracted from metadata for compatibility)
            "pov": metadata.pov,
            "tone": metadata.tone,
            "pace": metadata.pace,
            "voice": "developed",  # Indicates voice has been developed
            "sensory_focus": extract_sensory_focus(detailed_scaffold, constraints),
            # Explicit reminder: distinctiveness is non-negotiable
            "distinctiveness_required": True,
            "anti_generic_enforced": True,
        }
        
        self._scaffold_data = scaffold_data
        return scaffold_data
    
    def draft(self, scaffold=None, use_llm=True):
        """
        Stage 4: Generate prose narrative with precise, memorable language.
        
        Uses LLM for generation if use_llm=True, otherwise falls back to template-based.
        
        Args:
            scaffold: Scaffold object (uses self._scaffold_data if None)
            use_llm: If True, use LLM for generation (default: True)
        
        Returns:
            Draft object with prose narrative
        """
        if scaffold is None:
            scaffold = self._scaffold_data
        
        if scaffold is None:
            raise ValueError("Cannot draft without scaffold. Call scaffold() first.")
        if self.outline is None:
            raise ValueError("Cannot draft without outline. Call generate_outline() first.")
        if self.premise is None:
            raise ValueError("Cannot draft without premise. Call capture_premise() first.")
        
        # Extract elements from premise, outline, and scaffold
        premise = self.premise
        outline = self.outline
        
        # Extract from premise using type converter
        idea, character, theme = extract_premise_fields(premise)
        
        if not idea:
            raise ValueError("Cannot draft without a story idea in premise.")
        
        # Convert character to dict format
        character_dict = character_to_dict(character) or {}
        theme_str = theme or ""
        
        # Try LLM generation if enabled
        if use_llm:
            try:
                # Convert outline to dict if it's an OutlineModel
                outline_dict = outline_to_dict(outline)
                
                story_text = generate_story_draft(
                    idea=idea,
                    character=character_dict,
                    theme=theme_str,
                    outline=outline_dict,
                    scaffold=scaffold,
                    genre_config=self.genre_config or {},
                    max_words=self.word_validator.max_words,
                )
            except Exception as e:
                # Fall back to template if LLM fails
                # Consistently log full error details including traceback at WARNING level
                logger.warning(
                    f"LLM generation failed for story idea '{idea[:50]}...', using template fallback. "
                    f"Error type: {type(e).__name__}, Error message: {str(e)}",
                    exc_info=True  # This logs the full traceback at WARNING level
                )
                story_text = self._generate_template_draft(
                    idea, character_dict, theme_str, outline, scaffold
                )
        else:
            story_text = self._generate_template_draft(
                idea, character_dict, theme_str, outline, scaffold
            )
        
        # Validate word count
        word_count = self.word_validator.count_words(story_text)
        
        # If over limit, trim intelligently
        if word_count > self.word_validator.max_words:
            words = story_text.split()
            max_words = self.word_validator.max_words
            if max_words > 0:
                story_text = " ".join(words[:max_words]) + "..."
                word_count = self.word_validator.count_words(story_text)
            else:
                story_text = "..."
                word_count = 0
        
        draft_data = {
            "scaffold": scaffold,
            "word_count": word_count,
            "text": story_text,
        }
        self._draft_data = draft_data
        return draft_data
    
    def _generate_template_draft(self, idea, character, theme, outline, scaffold):
        """
        Fallback template-based draft generation.
        
        Generates a basic story structure when LLM is unavailable.
        Uses template-based approach with genre-specific elements.
        
        Args:
            idea: The story idea/premise
            character: Character description (dict or string)
            theme: The story's theme
            outline: Outline structure with acts
            scaffold: Scaffold data with POV, tone, etc.
        
        Returns:
            str: Generated story text following the template structure
        """
        return generate_template_draft(
            idea=idea,
            character=character,
            theme=theme,
            outline=outline,
            scaffold=scaffold,
            word_validator=self.word_validator,
        )
    
    def revise(self, draft=None, use_llm=True):
        """
        Stage 5: Sharpen language, deepen character distinctiveness.
        
        Uses LLM for revision if use_llm=True, otherwise uses rule-based replacements.
        
        Args:
            draft: Draft object (uses self._draft_data if None)
            use_llm: If True, use LLM for revision (default: True)
        
        Returns:
            Revised draft object
        """
        if draft is None:
            draft = self._draft_data
        
        if draft is None:
            raise ValueError("Cannot revise without draft. Call draft() first.")
        if not isinstance(draft, dict):
            raise ValueError(f"Draft must be a dict, got {type(draft).__name__}")
        if not draft.get("text"):
            raise ValueError("Cannot revise draft with empty text")
        
        text = draft["text"]
        if not isinstance(text, str):
            raise ValueError(f"Draft text must be a string, got {type(text).__name__}")
        
        # Check for clichés and generic language using comprehensive detection
        from .cliche_detector import get_cliche_detector
        from .memorability_scorer import get_memorability_scorer
        
        cliche_detector = get_cliche_detector()
        
        # Extract character for cliche detection using type converter
        _, character_raw, _ = extract_premise_fields(self.premise)
        character_for_detection = character_to_dict(character_raw)
        
        # Convert outline to dict for functions that expect dict
        outline_for_detection = outline_to_dict(self.outline)
        # Merge in detailed outline data if available
        if hasattr(self, '_outline_details'):
            outline_for_detection.update(self._outline_details)
        
        comprehensive_check = cliche_detector.detect_all_cliches(
            text=text,
            character=character_for_detection,
            outline=outline_for_detection
        )
        
        # Also get distinctiveness check for backward compatibility
        distinctiveness_check = check_distinctiveness(text)
        
        # Get memorability score
        memorability_scorer = get_memorability_scorer()
        memorability_score = memorability_scorer.score_story(
            text=text,
            character=character_for_detection,
            outline=outline_for_detection,
            premise=premise_to_dict(self.premise)
        )
        
        # Analyze character voices
        character_info = character_for_detection
        voice_analysis = validate_story_voices(text, character_info)
        
        # Try LLM revision if enabled
        if use_llm:
            try:
                # Build revision notes from distinctiveness check
                revision_notes = []
                if distinctiveness_check.get("has_cliches", False):
                    cliches = distinctiveness_check.get("found_cliches", [])
                    revision_notes.append(f"Replace clichés: {', '.join(cliches[:3])}")
                if distinctiveness_check.get("generic_patterns"):
                    patterns = distinctiveness_check.get("generic_patterns", [])
                    revision_notes.append(f"Improve generic language patterns ({len(patterns)} found)")
                
                # Get current word count
                current_words = self.word_validator.count_words(text)
                
                revised_text = revise_story_text(
                    text=text,
                    revision_notes=revision_notes,
                    current_words=current_words,
                    max_words=self.word_validator.max_words,
                )
            except Exception as e:
                # Fall back to rule-based if LLM fails
                # Consistently log full error details including traceback at WARNING level
                logger.warning(
                    f"LLM revision failed, using rule-based fallback. "
                    f"Error type: {type(e).__name__}, Error message: {str(e)}",
                    exc_info=True  # This logs the full traceback at WARNING level
                )
                revised_text = self._apply_rule_based_revisions(text, distinctiveness_check)
        else:
            revised_text = self._apply_rule_based_revisions(text, distinctiveness_check)
        
        # Validate word count after revision
        word_count, is_valid = self.word_validator.validate(
            revised_text, raise_error=False
        )
        
        if not is_valid:
            # Trim if still over limit
            words = revised_text.split()
            max_words = self.word_validator.max_words
            revised_text = " ".join(words[:max_words]) + "..."
            word_count = self.word_validator.count_words(revised_text)
        
        # Analyze voices in revised text as well
        revised_voice_analysis = validate_story_voices(revised_text, character_info)
        
        # Check voice consistency across draft stages
        from .voice_analyzer import check_voice_consistency_across_stages
        voice_consistency_check = check_voice_consistency_across_stages(
            draft_analysis=voice_analysis,
            revised_analysis=revised_voice_analysis,
            character_info=character_info
        )
        
        revised_draft_data = {
            "draft": draft,
            "word_count": word_count,
            "text": revised_text,
            "revisions": {
                "cliche_count": distinctiveness_check.get("cliche_count", 0),
                "distinctiveness_score": distinctiveness_check.get("distinctiveness_score", 1.0),
                "comprehensive_cliche_analysis": comprehensive_check,  # Full cliché detection results
                "total_issues": comprehensive_check.get("total_issues", 0),
                "suggestions": comprehensive_check.get("suggestions", []),
                "voice_analysis": voice_analysis,  # Character voice analysis from original draft
                "revised_voice_analysis": revised_voice_analysis,  # Character voice analysis from revised draft
                "voice_consistency_check": voice_consistency_check,  # Consistency check across draft stages
                "memorability": memorability_score,  # Multi-dimensional memorability scoring
            }
        }
        self._revised_draft_data = revised_draft_data
        return revised_draft_data
    
    def _apply_rule_based_revisions(self, text, distinctiveness_check):
        """
        Apply rule-based text revisions (fallback when LLM unavailable).
        
        Delegates to the rule_based_revisions module for actual processing.
        
        Args:
            text: Text to revise
            distinctiveness_check: Results from check_distinctiveness 
                (currently unused but kept for API compatibility)
        
        Returns:
            Revised text with clichés replaced and vague language removed
        """
        return apply_rule_based_revisions(text, distinctiveness_check)
    
    def run_full_pipeline(self, idea, character, theme, genre=None):
        """
        Run all pipeline stages sequentially.
        
        Args:
            idea: Initial concept
            character: Character sketch
            theme: Central theme
            genre: Genre name (optional)
        
        Returns:
            Final revised draft
        """
        self.genre = genre
        if genre:
            self.genre_config = get_genre_config(genre)
        
        self.capture_premise(idea, character, theme)
        self.generate_outline(genre=genre)
        self.scaffold(genre=genre)
        self.draft()
        return self.revise()

