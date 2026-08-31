-- models/staging_house_prices.sql
-- DuckDB Staging schema for raw residential property listings
CREATE TABLE IF NOT EXISTS staging_house_prices (
    property_id VARCHAR PRIMARY KEY,
    area_sqft DOUBLE NOT NULL,
    price_inr DOUBLE NOT NULL,
    location VARCHAR NOT NULL,
    bhk_count INTEGER,
    listing_date DATE,
    is_active BOOLEAN DEFAULT TRUE
);
