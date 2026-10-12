-- Gold star schema (sample sales domain), loaded from Silver lakehouse via cross-database query.
IF SCHEMA_ID('gold') IS NULL EXEC('CREATE SCHEMA gold');
GO

CREATE TABLE gold.dim_customer (
    customer_key BIGINT NOT NULL,        -- surrogate key, generated in load proc
    customer_id  INT NOT NULL,           -- business key
    email        VARCHAR(256) NULL,
    country      VARCHAR(50) NULL,
    updated_at   DATETIME2(3) NULL
);
GO

CREATE TABLE gold.dim_product (
    product_key  BIGINT NOT NULL,
    product_id   INT NOT NULL,
    title        VARCHAR(256) NULL,
    category     VARCHAR(100) NULL,
    price        DECIMAL(18,2) NULL
);
GO

CREATE TABLE gold.fact_orders (
    order_id     INT NOT NULL,
    customer_key BIGINT NULL,
    order_date   DATE NULL,
    total_amount DECIMAL(18,2) NULL
);
GO
