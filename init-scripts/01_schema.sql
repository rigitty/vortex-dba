-- VortexDBA SQL Server Schema Initialization
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'vortex_db')
BEGIN
    CREATE DATABASE vortex_db;
END
GO

USE vortex_db;
GO

-- Customers table
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'customers')
BEGIN
    CREATE TABLE customers (
        id INT IDENTITY(1,1) PRIMARY KEY,
        first_name NVARCHAR(100) NOT NULL,
        last_name NVARCHAR(100) NOT NULL,
        email NVARCHAR(255) NOT NULL,
        phone NVARCHAR(50),
        city NVARCHAR(100),
        country NVARCHAR(100),
        created_at DATETIME2 DEFAULT GETDATE(),
        status NVARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended'))
    );
END
GO

-- Orders table
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'orders')
BEGIN
    CREATE TABLE orders (
        id INT IDENTITY(1,1) PRIMARY KEY,
        customer_id INT NOT NULL REFERENCES customers(id),
        order_date DATETIME2 DEFAULT GETDATE(),
        total_amount DECIMAL(12, 2) NOT NULL,
        status NVARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'cancelled', 'refunded')),
        product_category NVARCHAR(100),
        shipping_address NVARCHAR(MAX)
    );
END
GO

-- Default Indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_orders_customer_id' AND object_id = OBJECT_ID('orders'))
BEGIN
    CREATE NONCLUSTERED INDEX idx_orders_customer_id ON orders(customer_id);
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_customers_email' AND object_id = OBJECT_ID('customers'))
BEGIN
    CREATE NONCLUSTERED INDEX idx_customers_email ON customers(email);
END
GO
