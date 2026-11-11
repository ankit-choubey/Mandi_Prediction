"""
Unit tests for Agmarknet Arrivals Ingestion Engine
"""

import os
import tempfile
import pandas as pd
import pytest
from src.ingest_agmarknet_arrivals import audit_arrivals_folder, COLUMN_ALIASES


def test_audit_empty_folder():
    with tempfile.TemporaryDirectory() as tmpdir:
        summary = audit_arrivals_folder(tmpdir)
        assert summary["status"] == "EMPTY"
        assert summary["files_count"] == 0
        assert summary["total_records"] == 0
        assert summary["districts_covered"] == []
        assert summary["commodities_covered"] == []


def test_audit_populated_folder():
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_df = pd.DataFrame({
            "State": ["Uttar Pradesh", "Uttar Pradesh"],
            "District Name": ["Kanpur", "Lucknow"],
            "Market Name": ["Kanpur Grain", "Lucknow Subzi"],
            "Commodity": ["Potato", "Wheat"],
            "Variety": ["Desi", "Dara"],
            "Grade": ["FAQ", "FAQ"],
            "Arrival Date": ["2024-01-10", "2024-01-11"],
            "Arrivals (Tonnes)": [50.0, 120.5],
            "Min Price (Rs./Quintal)": [1000, 2200],
            "Max Price (Rs./Quintal)": [1200, 2350],
            "Modal Price (Rs./Quintal)": [1150, 2275],
        })
        file_path = os.path.join(tmpdir, "Kanpur_Potato_Sample.csv")
        dummy_df.to_csv(file_path, index=False)

        summary = audit_arrivals_folder(tmpdir)
        assert summary["status"] == "POPULATED"
        assert summary["files_count"] == 1
        assert summary["total_records"] == 2
        assert "Kanpur" in summary["districts_covered"]
        assert "Lucknow" in summary["districts_covered"]
        assert "Potato" in summary["commodities_covered"]
        assert "Wheat" in summary["commodities_covered"]
        assert summary["date_min"] == "2024-01-10"
        assert summary["date_max"] == "2024-01-11"
