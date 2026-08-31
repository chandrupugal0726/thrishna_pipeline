-- models/cleaned_properties.sql
-- DuckDB Analytical model for normalized property metrics and categorizations
CREATE TABLE IF NOT EXISTS cleaned_properties (
    property_id VARCHAR PRIMARY KEY,
    standardized_location VARCHAR,
    price_per_sqft DOUBLE,
    net_price_inr DOUBLE,
    price_category VARCHAR,
    validated_at TIMESTAMP
);
