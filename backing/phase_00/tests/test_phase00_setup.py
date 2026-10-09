"""
Phase 0 Smoke & Verification Test Suite
Tests environment dependencies, raw data file existence, and notebook validity.
"""

import os
import glob
import json
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

def test_environment_packages():
    """Verify core packages required for audit are installed."""
    for pkg in ['pandas', 'numpy', 'scipy', 'sklearn', 'nbformat']:
        mod = __import__(pkg)
        assert mod is not None, f"Package {pkg} failed to import"

def test_raw_dataset_files():
    """Verify that all 5 raw CSV files exist and have non-zero size."""
    raw_dir = os.path.join(ROOT_DIR, "data", "raw")
    assert os.path.exists(raw_dir), f"Directory {raw_dir} does not exist"
    
    expected_files = ["Gaziabaad.csv", "Jhansi.csv", "Kanpur.csv", "Lukhnow.csv", "Unnao.csv"]
    found_files = [os.path.basename(f) for f in glob.glob(os.path.join(raw_dir, "*.csv"))]
    
    for ef in expected_files:
        assert ef in found_files, f"Expected raw file {ef} missing from {raw_dir}"
        file_path = os.path.join(raw_dir, ef)
        assert os.path.getsize(file_path) > 1024 * 1024, f"File {ef} is smaller than 1 MB"

def test_notebook_structure():
    """Verify that mandi_mathematical_audit.ipynb is valid JSON and contains cells."""
    nb_path = os.path.join(ROOT_DIR, "notebooks", "mandi_mathematical_audit.ipynb")
    assert os.path.exists(nb_path), f"Notebook missing at {nb_path}"
    
    with open(nb_path, "r", encoding="utf-8") as f:
        nb_json = json.load(f)
    
    assert "cells" in nb_json, "Notebook missing 'cells' attribute"
    assert len(nb_json["cells"]) >= 8, f"Notebook has fewer cells than expected: {len(nb_json['cells'])}"
    assert nb_json["metadata"]["kernelspec"]["name"] == "python3"

def test_phase0_evidence_files():
    """Verify that all Phase 0 evidence files exist in backing archive."""
    evidence_dir = os.path.join(ROOT_DIR, "backing", "phase_00", "evidence")
    assert os.path.exists(os.path.join(evidence_dir, "environment_check.txt"))
    assert os.path.exists(os.path.join(evidence_dir, "repository_inventory.md"))
    assert os.path.exists(os.path.join(evidence_dir, "unresolved_questions.md"))
    
    output_dir = os.path.join(ROOT_DIR, "backing", "phase_00", "outputs")
    assert os.path.exists(os.path.join(output_dir, "mandi-math-audit-p0.log"))

if __name__ == "__main__":
    test_environment_packages()
    test_raw_dataset_files()
    test_notebook_structure()
    test_phase0_evidence_files()
    print("All Phase 0 verification tests passed successfully!")
