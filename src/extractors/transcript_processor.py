"""Meeting transcript preprocessing and processing."""

from typing import Optional, Any
import re

import structlog

logger = structlog.get_logger(__name__)


class TranscriptProcessor:
    """
    Preprocess and process meeting transcripts before requirement extraction.
    
    Tasks:
    - Clean and normalize transcript text
    - Identify speaker turns
    - Remove filler words and noise
    - Extract key sections
    """

    def __init__(self):
        """Initialize the transcript processor."""
        pass

    def preprocess_transcript(self, transcript: str) -> str:
        """
        Preprocess transcript text for better extraction.
        
        Args:
            transcript: Raw transcript text
            
        Returns:
            Cleaned and normalized transcript
        """
        try:
            # Remove excessive whitespace
            transcript = re.sub(r"\n{3,}", "\n\n", transcript)
            transcript = re.sub(r" +", " ", transcript)
            
            # Normalize speaker indicators (e.g., "John:", "JOHN:", "John -")
            transcript = re.sub(r"(\w+)[:\-]\s+", r"\1: ", transcript)
            
            # Remove timestamps if present (e.g., "[00:12:34]" or "12:34")
            transcript = re.sub(r"\[\d{1,2}:\d{2}:\d{2}\]", "", transcript)
            transcript = re.sub(r"\b\d{1,2}:\d{2}\b", "", transcript)
            
            # Remove common filler words/phrases (optional, can be configurable)
            # Note: Be careful not to remove too much as it might affect context
            
            # Normalize quotes
            transcript = re.sub(r"[""]", '"', transcript)
            transcript = re.sub(r[''], "'", transcript)
            
            # Trim whitespace from lines
            lines = [line.strip() for line in transcript.split("\n")]
            transcript = "\n".join(lines)
            
            # Remove empty lines at start/end
            transcript = transcript.strip()
            
            logger.debug(
                "Transcript preprocessed",
                original_length=len(transcript),
                cleaned_length=len(transcript),
            )
            
            return transcript
            
        except Exception as e:
            logger.error(
                "Error preprocessing transcript",
                error=str(e),
            )
            raise ValueError(f"Failed to preprocess transcript: {str(e)}") from e

    def extract_speaker_turns(self, transcript: str) -> list[dict[str, str]]:
        """
        Extract speaker turns from transcript.
        
        Args:
            transcript: Transcript text
            
        Returns:
            List of dictionaries with 'speaker' and 'text' keys
        """
        try:
            speaker_turns = []
            
            # Pattern to match speaker indicators: "Speaker: text"
            pattern = r"^([^:\n]+):\s+(.+)$"
            
            lines = transcript.split("\n")
            current_speaker = None
            current_text = []
            
            for line in lines:
                match = re.match(pattern, line)
                if match:
                    # Save previous turn if exists
                    if current_speaker and current_text:
                        speaker_turns.append({
                            "speaker": current_speaker.strip(),
                            "text": " ".join(current_text).strip(),
                        })
                    
                    # Start new turn
                    current_speaker = match.group(1)
                    current_text = [match.group(2)]
                else:
                    # Continuation of current turn
                    if line.strip():
                        current_text.append(line.strip())
            
            # Save last turn
            if current_speaker and current_text:
                speaker_turns.append({
                    "speaker": current_speaker.strip(),
                    "text": " ".join(current_text).strip(),
                })
            
            logger.debug(
                "Speaker turns extracted",
                num_turns=len(speaker_turns),
            )
            
            return speaker_turns
            
        except Exception as e:
            logger.error(
                "Error extracting speaker turns",
                error=str(e),
            )
            return []

    def identify_requirements_sections(self, transcript: str) -> list[dict[str, Any]]:
        """
        Identify sections of transcript that likely contain requirements.
        
        Args:
            transcript: Transcript text
            
        Returns:
            List of sections with metadata
        """
        try:
            sections = []
            
            # Look for requirement indicators
            requirement_keywords = [
                "requirement",
                "must",
                "shall",
                "should",
                "need",
                "system",
                "user",
                "feature",
                "functionality",
            ]
            
            lines = transcript.split("\n")
            current_section = None
            current_lines = []
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                
                # Check if line contains requirement keywords
                has_keywords = any(keyword in line_lower for keyword in requirement_keywords)
                
                if has_keywords and not current_section:
                    # Start new section
                    current_section = {
                        "start_line": i,
                        "keywords": [kw for kw in requirement_keywords if kw in line_lower],
                    }
                    current_lines = [line]
                elif current_section:
                    if has_keywords or len(line.strip()) > 0:
                        current_lines.append(line)
                    else:
                        # End section if multiple empty lines
                        if len([l for l in current_lines[-3:] if not l.strip()]) >= 2:
                            current_section["end_line"] = i
                            current_section["text"] = "\n".join(current_lines).strip()
                            sections.append(current_section)
                            current_section = None
                            current_lines = []
            
            # Save last section if exists
            if current_section and current_lines:
                current_section["text"] = "\n".join(current_lines).strip()
                sections.append(current_section)
            
            logger.debug(
                "Requirement sections identified",
                num_sections=len(sections),
            )
            
            return sections
            
        except Exception as e:
            logger.error(
                "Error identifying requirement sections",
                error=str(e),
            )
            return []
