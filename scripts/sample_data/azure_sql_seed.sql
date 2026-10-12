-- Sample source schema for Azure SQL (run in your source database).
CREATE TABLE dbo.Customers (
    CustomerID   INT PRIMARY KEY,
    Email        NVARCHAR(256) NOT NULL,
    Country      NVARCHAR(50)  NULL,
    ModifiedDate DATETIME2(3)  NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE TABLE dbo.Orders (
    OrderID      INT PRIMARY KEY,
    CustomerID   INT NOT NULL REFERENCES dbo.Customers(CustomerID),
    OrderDate    DATE NOT NULL,
    TotalAmount  DECIMAL(18,2) NOT NULL,
    ModifiedDate DATETIME2(3)  NOT NULL DEFAULT SYSUTCDATETIME()
);
INSERT dbo.Customers (CustomerID, Email, Country) VALUES
 (1,'ann@example.com','US'),(2,'bo@example.com','UK'),(3,'cy@example.com','DE');
INSERT dbo.Orders (OrderID, CustomerID, OrderDate, TotalAmount) VALUES
 (100,1,'2026-09-01',49.90),(101,2,'2026-09-02',120.00),(102,1,'2026-09-03',15.50),(103,3,'2026-09-04',300.00);
