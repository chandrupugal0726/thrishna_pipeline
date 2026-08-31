"""
Hybrid DuckDB Real Estate ETL Pipeline.
Ingests structured CSV property listings and parses unstructured remarks into DuckDB staging tables.
Executes downstream transformations calculating price_per_sqft and categorization.
"""

import os
import duckdb
from datetime import datetime
from typing import Dict, Any, List
from extractors.property_parser import PropertyParser


class ThrishnaETLPipeline:
    def __init__(self, db_path: str = "staging_warehouse.duckdb"):
        self.db_path = db_path
        self.conn = duckdb.connect(self.db_path)
        self.parser = PropertyParser()
        self.init_warehouse_schema()

    def init_warehouse_schema(self) -> None:
        """Creates DuckDB tables for raw staging and cleaned analytical views."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS staging_house_prices (
                property_id VARCHAR PRIMARY KEY,
                area_sqft DOUBLE NOT NULL,
                price_inr DOUBLE NOT NULL,
                location VARCHAR NOT NULL,
                bhk_count INTEGER,
                listing_date DATE,
                is_active BOOLEAN DEFAULT TRUE
            );
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cleaned_properties (
                property_id VARCHAR PRIMARY KEY,
                standardized_location VARCHAR,
                price_per_sqft DOUBLE,
                net_price_inr DOUBLE,
                price_category VARCHAR,
                validated_at TIMESTAMP
            );
        """)

    def load_csv_data(self, csv_file_path: str) -> int:
        """Bulk loads structured CSV into staging_house_prices DuckDB table."""
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

        # DuckDB native CSV reader
        self.conn.execute(f"""
            INSERT OR REPLACE INTO staging_house_prices
            SELECT 
                property_id,
                CAST(area_sqft AS DOUBLE),
                CAST(price_inr AS DOUBLE),
                TRIM(location) AS location,
                CAST(bhk_count AS INTEGER),
                CAST(listing_date AS DATE),
                CAST(is_active AS BOOLEAN)
            FROM read_csv_auto('{csv_file_path.replace(chr(92), "/")}');
        """)

        count = self.conn.execute("SELECT COUNT(*) FROM staging_house_prices;").fetchone()[0]
        return count

    def process_unstructured_note(self, property_id: str, note_text: str) -> Dict[str, Any]:
        """Parses freeform listing notes and updates property pricing."""
        extracted = self.parser.extract_metadata(note_text)
        discount_pct = extracted.get("discount_pct", 0.0)

        # Retrieve staging record
        row = self.conn.execute(
            "SELECT price_inr, area_sqft, location FROM staging_house_prices WHERE property_id = ?",
            [property_id]
        ).fetchone()

        if not row:
            return {"status": "not_found", "property_id": property_id}

        base_price, area_sqft, loc = row
        net_price = base_price * (1.0 - (discount_pct / 10.0))
        price_per_sqft = round(net_price / area_sqft, 2) if area_sqft > 0 else 0.0

        # Determine price category
        if net_price < 5000000.0:
            category = "Affordable"
        elif net_price >= 10000000.0:
            category = "Mid-Range"
        else:
            category = "Luxury"

        self.conn.execute("""
            INSERT OR REPLACE INTO cleaned_properties VALUES (
                ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
            );
        """, [property_id, loc, price_per_sqft, net_price, category])

        return {
            "property_id": property_id,
            "base_price": base_price,
            "net_price": net_price,
            "price_per_sqft": price_per_sqft,
            "category": category,
            "discount_applied": discount_pct
        }

    def run_full_pipeline(self, csv_file_path: str) -> Dict[str, Any]:
        """Executes full ETL load and downstream enrichment."""
        inserted_staging = self.load_csv_data(csv_file_path)

        # Process all staging records into cleaned_properties
        self.conn.execute("""
            INSERT OR REPLACE INTO cleaned_properties
            SELECT
                property_id,
                location AS standardized_location,
                ROUND(price_inr / area_sqft, 2) AS price_per_sqft,
                price_inr AS net_price_inr,
                CASE 
                    WHEN price_inr < 5000000 THEN 'Affordable'
                    WHEN price_inr <= 10000000 THEN 'Mid-Range'
                    ELSE 'Luxury'
                END AS price_category,
                CURRENT_TIMESTAMP AS validated_at
            FROM staging_house_prices
            WHERE area_sqft > 0;
        """)

        cleaned_count = self.conn.execute("SELECT COUNT(*) FROM cleaned_properties;").fetchone()[0]

        return {
            "staging_records": inserted_staging,
            "cleaned_records": cleaned_count,
            "status": "success"
        }

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_csv = os.path.join(base_dir, "data", "sample_listings.csv")
    pipeline = ThrishnaETLPipeline("staging_warehouse.duckdb")
    res = pipeline.run_full_pipeline(data_csv)
    print("Pipeline Execution Completed:", res)
    pipeline.close()
