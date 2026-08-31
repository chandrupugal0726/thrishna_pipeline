"""
DuckDB Data Quality & Regression Assertion Test Suite.
Validates constraints against DuckDB tables and checks parser logic.
"""

import os
import pytest
import duckdb
from etl_pipeline import ThrishnaETLPipeline
from extractors.property_parser import PropertyParser


@pytest.fixture
def memory_pipeline():
    """In-memory DuckDB testing pipeline fixture."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "sample_listings.csv")
    pipeline = ThrishnaETLPipeline(":memory:")
    pipeline.run_full_pipeline(csv_path)
    yield pipeline
    pipeline.close()


def test_staging_row_count_threshold(memory_pipeline):
    """DuckDB Quality Check: Verify at least 10 rows loaded into staging."""
    count = memory_pipeline.conn.execute("SELECT COUNT(*) FROM staging_house_prices;").fetchone()[0]
    assert count >= 10, f"Expected at least 10 staging rows, found {count}"


def test_primary_key_and_location_not_null(memory_pipeline):
    """DuckDB Quality Check: Zero NULLs in primary key and location."""
    nulls = memory_pipeline.conn.execute("""
        SELECT COUNT(*) 
        FROM staging_house_prices 
        WHERE property_id IS NULL OR location IS NULL;
    """).fetchone()[0]
    assert nulls == 0, f"Found {nulls} NULL keys or locations"


def test_domain_positive_price_and_area(memory_pipeline):
    """DuckDB Quality Check: Price and Area must strictly be > 0."""
    violations = memory_pipeline.conn.execute("""
        SELECT COUNT(*) 
        FROM staging_house_prices 
        WHERE price_inr <= 0 OR area_sqft <= 0;
    """).fetchone()[0]
    assert violations == 0, f"Found {violations} non-positive prices or areas"


def test_cleaned_price_per_sqft_accuracy(memory_pipeline):
    """DuckDB Quality Check: price_per_sqft calculation must be positive and non-zero."""
    invalid = memory_pipeline.conn.execute("""
        SELECT COUNT(*) 
        FROM cleaned_properties 
        WHERE price_per_sqft <= 0 OR standardized_location IS NULL;
    """).fetchone()[0]
    assert invalid == 0, f"Found {invalid} invalid price_per_sqft values"


def test_property_parser_regex():
    """Unstructured Text Quality Check: Verify parser extracts price and area."""
    parser = PropertyParser()
    sample = "Premium 3 BHK flat INR 95.0 Lakhs for 1500 sq ft in Indiranagar near metro station. Offer: 5% discount"
    res = parser.extract_metadata(sample)

    assert res["is_valid"] is True
    assert "95.0 Lakhs" in res["price_str"]
    assert res["area_sqft"] == 1500
    assert "Indiranagar" in res["location"]
    assert res["discount_pct"] == 5.0
