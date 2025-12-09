"""
AEGIS v3.0 - Pipeline Module
Orchestrates Fetching → Pre-processing → Brain → Validation → Execution
"""
from pipeline.intraday_pipeline import intraday_pipeline

__all__ = ["intraday_pipeline"]
