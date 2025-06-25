"""Structured output schemas for MiniCPM-Vision using outlines."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class StructuredSceneAnalysis(BaseModel):
    """Structured output schema for scene analysis."""

    description: str = Field(..., description="Detailed scene description")
    categories: List[str] = Field(..., description="Scene categories", max_items=10)
    objects: List[Dict[str, float]] = Field(
        ..., description="Detected objects with confidence scores"
    )
    text_content: Optional[str] = Field(None, description="Any text visible in image")
    activities: Optional[List[str]] = Field(
        None, description="Activities or actions detected"
    )


class StructuredOCRAnalysis(BaseModel):
    """Structured output schema for OCR analysis."""

    text_blocks: List[Dict[str, str]] = Field(
        ..., description="Text blocks with their content"
    )
    full_text: str = Field(..., description="Full concatenated text")
    document_type: Optional[str] = Field(
        None, description="Type of document if applicable"
    )
    language: Optional[str] = Field(None, description="Detected language")


class StructuredVisualQA(BaseModel):
    """Structured output schema for visual question answering."""

    question: str = Field(..., description="The visual question asked")
    answer: str = Field(..., description="The answer based on image content")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Answer confidence")
    evidence: Optional[str] = Field(
        None, description="Visual evidence supporting the answer"
    )


# Prompts for structured generation
SCENE_ANALYSIS_PROMPT = """Analyze this image and provide a detailed analysis including:
1. A comprehensive scene description
2. Categories that best describe the scene
3. All objects visible with confidence scores
4. Any text content visible
5. Activities or actions taking place

Respond in the exact JSON format specified."""

OCR_ANALYSIS_PROMPT = """Extract and analyze all text content from this image:
1. Identify all text blocks
2. Provide the full concatenated text
3. Determine the document type if applicable
4. Detect the language

Focus on accurate text extraction. Respond in the exact JSON format specified."""

VISUAL_QA_PROMPT = """Answer the following question about this image: {question}

Provide:
1. The question being asked
2. A clear, accurate answer based on what you see
3. Your confidence level (0-1)
4. Visual evidence supporting your answer

Respond in the exact JSON format specified."""
