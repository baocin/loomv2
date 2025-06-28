"""Audit Logger - Privacy operation auditing and compliance logging."""

import json
import time
from typing import Any, Dict, List, Optional

import structlog

from ..models import PIIEntity, AuditLogEntry

logger = structlog.get_logger(__name__)


class AuditLogger:
    """Audit logging service for privacy operations."""
    
    def __init__(self):
        self.audit_entries = []  # In production, this would be a database
        self.max_entries = 10000  # Rotate after this many entries
    
    async def initialize(self):
        """Initialize the audit logger."""
        logger.info("Initializing Audit Logger")
        # In production, this would connect to a secure audit database
        logger.info("Audit Logger initialized")
    
    async def log_detection(
        self,
        original_text: str,
        entities: List[PIIEntity],
        context: Optional[Dict[str, Any]] = None
    ):
        """Log PII detection operation."""
        entry = AuditLogEntry(
            operation="pii_detection",
            timestamp=time.time(),
            entities_processed=len(entities),
            data_size=len(original_text),
            context={
                "entity_types": [e.entity_type for e in entities],
                "confidence_scores": [e.confidence for e in entities],
                **(context or {})
            },
            user_id=context.get("user_id") if context else None
        )
        
        await self._store_audit_entry(entry)
        
        logger.info(
            "Audit: PII detection",
            entities_found=len(entities),
            data_size=len(original_text),
            context=context
        )
    
    async def log_filtering(
        self,
        original_data: Dict[str, Any],
        filtered_data: Dict[str, Any],
        entities: List[PIIEntity],
        context: Optional[Dict[str, Any]] = None
    ):
        """Log data filtering operation."""
        entry = AuditLogEntry(
            operation="data_filtering",
            timestamp=time.time(),
            entities_processed=len(entities),
            data_size=len(json.dumps(original_data)),
            context={
                "entities_filtered": [e.entity_type for e in entities],
                "data_keys": list(original_data.keys()),
                **(context or {})
            },
            user_id=context.get("user_id") if context else None
        )
        
        await self._store_audit_entry(entry)
        
        logger.info(
            "Audit: Data filtering",
            entities_filtered=len(entities),
            data_keys=list(original_data.keys()),
            context=context
        )
    
    async def log_anonymization(
        self,
        original_data_size: int,
        anonymization_map: Dict[str, str],
        context: Optional[Dict[str, Any]] = None
    ):
        """Log data anonymization operation."""
        entry = AuditLogEntry(
            operation="data_anonymization",
            timestamp=time.time(),
            entities_processed=len(anonymization_map),
            data_size=original_data_size,
            context={
                "anonymizations_count": len(anonymization_map),
                # Don't log actual mapping for privacy
                **(context or {})
            },
            user_id=context.get("user_id") if context else None
        )
        
        await self._store_audit_entry(entry)
        
        logger.info(
            "Audit: Data anonymization",
            anonymizations=len(anonymization_map),
            data_size=original_data_size,
            context=context
        )
    
    async def _store_audit_entry(self, entry: AuditLogEntry):
        """Store audit entry (in production, this would be secure storage)."""
        self.audit_entries.append(entry)
        
        # Rotate entries if we have too many
        if len(self.audit_entries) > self.max_entries:
            # In production, this would archive to secure storage
            self.audit_entries = self.audit_entries[-self.max_entries//2:]
            logger.info("Rotated audit log entries")
    
    async def get_audit_trail(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        operation: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """Retrieve audit trail with filtering."""
        filtered_entries = []
        
        for entry in self.audit_entries:
            # Apply filters
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue
            if operation and entry.operation != operation:
                continue
            if user_id and entry.user_id != user_id:
                continue
            
            filtered_entries.append(entry)
            
            if len(filtered_entries) >= limit:
                break
        
        # Sort by timestamp (newest first)
        filtered_entries.sort(key=lambda e: e.timestamp, reverse=True)
        
        logger.info(
            "Retrieved audit trail",
            entries_returned=len(filtered_entries),
            filters={
                "start_time": start_time,
                "end_time": end_time,
                "operation": operation,
                "user_id": user_id
            }
        )
        
        return filtered_entries
    
    async def get_audit_stats(self) -> Dict[str, Any]:
        """Get audit trail statistics."""
        if not self.audit_entries:
            return {
                "total_entries": 0,
                "operations": {},
                "oldest_entry": None,
                "newest_entry": None
            }
        
        operations = {}
        for entry in self.audit_entries:
            operations[entry.operation] = operations.get(entry.operation, 0) + 1
        
        timestamps = [e.timestamp for e in self.audit_entries]
        
        return {
            "total_entries": len(self.audit_entries),
            "operations": operations,
            "oldest_entry": min(timestamps),
            "newest_entry": max(timestamps),
            "total_entities_processed": sum(e.entities_processed for e in self.audit_entries),
            "total_data_processed": sum(e.data_size for e in self.audit_entries)
        }
    
    async def clear_audit_trail(self, before_timestamp: Optional[float] = None):
        """Clear audit trail (admin operation)."""
        if before_timestamp:
            # Keep entries after the timestamp
            self.audit_entries = [
                e for e in self.audit_entries 
                if e.timestamp >= before_timestamp
            ]
            logger.warning(
                "Partial audit trail cleared",
                before_timestamp=before_timestamp,
                remaining_entries=len(self.audit_entries)
            )
        else:
            # Clear all entries
            entries_cleared = len(self.audit_entries)
            self.audit_entries = []
            logger.warning(
                "Complete audit trail cleared",
                entries_cleared=entries_cleared
            )
    
    async def export_audit_trail(
        self,
        format: str = "json",
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> str:
        """Export audit trail for compliance reporting."""
        entries = await self.get_audit_trail(
            start_time=start_time,
            end_time=end_time,
            limit=len(self.audit_entries)  # Get all matching entries
        )
        
        if format == "json":
            export_data = {
                "export_timestamp": time.time(),
                "entries_count": len(entries),
                "time_range": {
                    "start": start_time,
                    "end": end_time
                },
                "entries": [entry.dict() for entry in entries]
            }
            return json.dumps(export_data, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")