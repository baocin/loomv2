"""Privacy Engine - Core PII detection and filtering logic."""

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import structlog
from faker import Faker

from ..models import EntityType, PIIEntity, ReplacementStrategy, PrivacyStats

logger = structlog.get_logger(__name__)


class PrivacyEngine:
    """Core privacy processing engine with PII detection and filtering."""
    
    def __init__(self):
        self.faker = Faker()
        self.stats = {
            'total_requests': 0,
            'pii_detections': 0,
            'entities_by_type': {},
            'start_time': time.time()
        }
        self._patterns = self._compile_patterns()
    
    async def initialize(self):
        """Initialize the privacy engine."""
        logger.info("Initializing Privacy Engine")
        # In a real implementation, this would load ML models
        # For now, we use regex patterns for PII detection
        logger.info("Privacy Engine initialized")
    
    async def is_ready(self) -> bool:
        """Check if the engine is ready to process requests."""
        return True
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for PII detection."""
        patterns = {
            EntityType.EMAIL: re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ),
            EntityType.PHONE: re.compile(
                r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
            ),
            EntityType.SSN: re.compile(
                r'\b\d{3}-?\d{2}-?\d{4}\b'
            ),
            EntityType.CREDIT_CARD: re.compile(
                r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'
            ),
            EntityType.IP_ADDRESS: re.compile(
                r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            ),
            EntityType.URL: re.compile(
                r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
            ),
            EntityType.DATE: re.compile(
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
            ),
        }
        return patterns
    
    async def detect_pii(
        self, 
        text: str, 
        entity_types: Optional[List[EntityType]] = None,
        language: str = "en"
    ) -> List[PIIEntity]:
        """Detect PII entities in text."""
        self.stats['total_requests'] += 1
        
        if entity_types is None:
            entity_types = list(EntityType)
        
        entities = []
        
        for entity_type in entity_types:
            if entity_type in self._patterns:
                pattern = self._patterns[entity_type]
                for match in pattern.finditer(text):
                    entity = PIIEntity(
                        entity_type=entity_type.value,
                        start=match.start(),
                        end=match.end(),
                        text=match.group(),
                        confidence=0.85  # Fixed confidence for regex matches
                    )
                    entities.append(entity)
                    
                    # Update stats
                    self.stats['entities_by_type'][entity_type.value] = \
                        self.stats['entities_by_type'].get(entity_type.value, 0) + 1
        
        if entities:
            self.stats['pii_detections'] += 1
        
        # Sort by start position
        entities.sort(key=lambda e: e.start)
        
        logger.info(
            "PII detection completed",
            text_length=len(text),
            entities_found=len(entities),
            entity_types=[e.entity_type for e in entities]
        )
        
        return entities
    
    async def filter_data(
        self,
        data: Dict[str, Any],
        rules: List[EntityType],
        replacement_strategy: ReplacementStrategy
    ) -> Tuple[Dict[str, Any], List[PIIEntity]]:
        """Filter PII from structured data."""
        filtered_data = {}
        all_entities = []
        
        for key, value in data.items():
            if isinstance(value, str):
                entities = await self.detect_pii(value, rules)
                if entities:
                    filtered_value = self._replace_entities(value, entities, replacement_strategy)
                    filtered_data[key] = filtered_value
                    all_entities.extend(entities)
                else:
                    filtered_data[key] = value
            elif isinstance(value, dict):
                # Recursively filter nested dictionaries
                nested_filtered, nested_entities = await self.filter_data(
                    value, rules, replacement_strategy
                )
                filtered_data[key] = nested_filtered
                all_entities.extend(nested_entities)
            elif isinstance(value, list):
                # Handle lists
                filtered_list = []
                for item in value:
                    if isinstance(item, str):
                        entities = await self.detect_pii(item, rules)
                        if entities:
                            filtered_item = self._replace_entities(item, entities, replacement_strategy)
                            filtered_list.append(filtered_item)
                            all_entities.extend(entities)
                        else:
                            filtered_list.append(item)
                    elif isinstance(item, dict):
                        nested_filtered, nested_entities = await self.filter_data(
                            item, rules, replacement_strategy
                        )
                        filtered_list.append(nested_filtered)
                        all_entities.extend(nested_entities)
                    else:
                        filtered_list.append(item)
                filtered_data[key] = filtered_list
            else:
                # Non-string values pass through unchanged
                filtered_data[key] = value
        
        return filtered_data, all_entities
    
    def _replace_entities(
        self,
        text: str,
        entities: List[PIIEntity],
        strategy: ReplacementStrategy
    ) -> str:
        """Replace PII entities in text based on strategy."""
        # Sort entities by start position in reverse order for proper replacement
        entities_sorted = sorted(entities, key=lambda e: e.start, reverse=True)
        
        result = text
        for entity in entities_sorted:
            replacement = self._get_replacement(entity, strategy)
            result = result[:entity.start] + replacement + result[entity.end:]
        
        return result
    
    def _get_replacement(self, entity: PIIEntity, strategy: ReplacementStrategy) -> str:
        """Generate replacement text for a PII entity."""
        if strategy == ReplacementStrategy.REDACT:
            return f"[REDACTED-{entity.entity_type}]"
        elif strategy == ReplacementStrategy.MASK:
            return "*" * len(entity.text)
        elif strategy == ReplacementStrategy.HASH:
            import hashlib
            return f"HASH_{hashlib.md5(entity.text.encode()).hexdigest()[:8]}"
        elif strategy == ReplacementStrategy.FAKE:
            return self._generate_fake_data(entity.entity_type)
        elif strategy == ReplacementStrategy.REMOVE:
            return ""
        else:
            return "[REDACTED]"
    
    def _generate_fake_data(self, entity_type: str) -> str:
        """Generate fake data for a given entity type."""
        if entity_type == EntityType.EMAIL:
            return self.faker.email()
        elif entity_type == EntityType.PHONE:
            return self.faker.phone_number()
        elif entity_type == EntityType.PERSON:
            return self.faker.name()
        elif entity_type == EntityType.LOCATION:
            return self.faker.address()
        elif entity_type == EntityType.DATE:
            return self.faker.date()
        elif entity_type == EntityType.URL:
            return self.faker.url()
        elif entity_type == EntityType.IP_ADDRESS:
            return self.faker.ipv4()
        else:
            return "[FAKE-DATA]"
    
    async def anonymize_data(
        self,
        data: Dict[str, Any],
        entity_types: Optional[List[EntityType]] = None,
        preserve_format: bool = True,
        seed: Optional[int] = None
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Anonymize data with consistent fake values."""
        if seed:
            self.faker.seed_instance(seed)
        
        anonymization_map = {}
        anonymized_data = {}
        
        if entity_types is None:
            entity_types = list(EntityType)
        
        for key, value in data.items():
            if isinstance(value, str):
                entities = await self.detect_pii(value, entity_types)
                if entities:
                    anonymized_value = value
                    for entity in sorted(entities, key=lambda e: e.start, reverse=True):
                        # Generate consistent fake data for the same original value
                        if entity.text not in anonymization_map:
                            fake_value = self._generate_fake_data(entity.entity_type)
                            anonymization_map[entity.text] = fake_value
                        
                        replacement = anonymization_map[entity.text]
                        anonymized_value = (
                            anonymized_value[:entity.start] + 
                            replacement + 
                            anonymized_value[entity.end:]
                        )
                    
                    anonymized_data[key] = anonymized_value
                else:
                    anonymized_data[key] = value
            elif isinstance(value, dict):
                # Recursively anonymize nested dictionaries
                nested_anonymized, nested_map = await self.anonymize_data(
                    value, entity_types, preserve_format, seed
                )
                anonymized_data[key] = nested_anonymized
                anonymization_map.update(nested_map)
            else:
                anonymized_data[key] = value
        
        return anonymized_data, anonymization_map
    
    async def get_stats(self) -> PrivacyStats:
        """Get service statistics."""
        avg_processing_time = 0.05  # Mock value
        uptime = time.time() - self.stats['start_time']
        
        return PrivacyStats(
            total_requests=self.stats['total_requests'],
            pii_detections=self.stats['pii_detections'],
            entities_by_type=self.stats['entities_by_type'].copy(),
            avg_processing_time=avg_processing_time,
            uptime_seconds=uptime
        )
    
    async def get_supported_entities(self) -> List[str]:
        """Get list of supported entity types."""
        return [entity.value for entity in EntityType]