"""
enrichment package — metadata joining and validation for the YipitData ETL pipeline.

Modules:
    metadata — Company metadata enrichment, validation, and derived field computation
"""

from .metadata import enrich_with_metadata

__all__ = ["enrich_with_metadata"]
