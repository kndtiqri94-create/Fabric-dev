-- Idempotent loads: re-running yields the same result.
CREATE OR ALTER PROCEDURE gold.usp_load_dim_customer
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE d
       SET d.email = s.Email, d.country = s.Country, d.updated_at = s._silver_updated_at
      FROM gold.dim_customer d
      JOIN lh_silver.dbo.customers s ON s.CustomerID = d.customer_id
     WHERE ISNULL(d.email,'') <> ISNULL(s.Email,'') OR ISNULL(d.country,'') <> ISNULL(s.Country,'');

    INSERT INTO gold.dim_customer (customer_key, customer_id, email, country, updated_at)
    SELECT COALESCE((SELECT MAX(customer_key) FROM gold.dim_customer),0) + ROW_NUMBER() OVER (ORDER BY s.CustomerID),
           s.CustomerID, s.Email, s.Country, s._silver_updated_at
      FROM lh_silver.dbo.customers s
     WHERE NOT EXISTS (SELECT 1 FROM gold.dim_customer d WHERE d.customer_id = s.CustomerID);
END;
GO

CREATE OR ALTER PROCEDURE gold.usp_load_dim_product
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE d
       SET d.title = s.title, d.category = s.category, d.price = s.price
      FROM gold.dim_product d
      JOIN lh_silver.dbo.products s ON s.id = d.product_id;

    INSERT INTO gold.dim_product (product_key, product_id, title, category, price)
    SELECT COALESCE((SELECT MAX(product_key) FROM gold.dim_product),0) + ROW_NUMBER() OVER (ORDER BY s.id),
           s.id, s.title, s.category, s.price
      FROM lh_silver.dbo.products s
     WHERE NOT EXISTS (SELECT 1 FROM gold.dim_product d WHERE d.product_id = s.id);
END;
GO

CREATE OR ALTER PROCEDURE gold.usp_load_fact_orders
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRAN;   -- full refresh in one transaction: readers never see a half-loaded table
        DELETE FROM gold.fact_orders;
        INSERT INTO gold.fact_orders (order_id, customer_key, order_date, total_amount)
        SELECT o.OrderID, c.customer_key, CAST(o.OrderDate AS DATE), o.TotalAmount
          FROM lh_silver.dbo.orders o
          LEFT JOIN gold.dim_customer c ON c.customer_id = o.CustomerID;
    COMMIT;
END;
GO
