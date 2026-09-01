"""Generate synthetic data for customers and orders tables using Faker for SQL Server."""

import random
import sys
import time
from pathlib import Path

from faker import Faker

from db_connection import get_connection, ensure_database_exists, execute_script

fake = Faker()

BATCH_SIZE = 5000
CUSTOMER_COUNT = 100_000
ORDERS_PER_CUSTOMER_MIN = 1
ORDERS_PER_CUSTOMER_MAX = 10

STATUSES = ["active", "inactive", "suspended"]
ORDER_STATUSES = ["pending", "completed", "cancelled", "refunded"]
PRODUCT_CATEGORIES = [
    "Electronics", "Clothing", "Home & Garden", "Books", "Sports",
    "Toys", "Food & Beverage", "Health", "Automotive", "Jewelry",
]


def init_tables_if_needed():
    """Ensure database and tables are created before generating data."""
    ensure_database_exists()
    schema_file = Path(__file__).parent.parent / "init-scripts" / "01_schema.sql"
    if schema_file.exists():
        with open(schema_file, "r") as f:
            script = f.read()
        execute_script(script)


def generate_customers(conn, count: int) -> list[int]:
    """Generate and insert customers in batches. Returns list of customer IDs."""
    print(f"Generating {count:,} customers...")
    customer_ids = []
    inserted = 0

    while inserted < count:
        batch_size = min(BATCH_SIZE, count - inserted)
        rows = []
        for _ in range(batch_size):
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 9999)}@{fake.free_email_domain()}"
            phone = fake.phone_number()[:50]
            city = fake.city()
            country = fake.country()
            status = random.choices(STATUSES, weights=[80, 15, 5])[0]
            created_at = fake.date_time_between(start_date="-2y", end_date="now")
            rows.append((first_name, last_name, email, phone, city, country, created_at, status))

        with conn.cursor() as cur:
            query = """
                INSERT INTO customers (first_name, last_name, email, phone, city, country, created_at, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.executemany(query, rows)
        conn.commit()

        inserted += batch_size
        print(f"  Customers inserted: {inserted:,}/{count:,}")

    # Fetch customer IDs
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM customers")
        rows = cur.fetchall()
        customer_ids = [r[0] if isinstance(r, (tuple, list)) else r["id"] for r in rows]

    return customer_ids


def generate_orders(conn, customer_ids: list[int]) -> None:
    """Generate and insert orders for each customer in batches."""
    total_customers = len(customer_ids)
    print(f"Generating orders for {total_customers:,} customers...")
    inserted = 0
    batch = []

    for i, customer_id in enumerate(customer_ids):
        order_count = random.randint(ORDERS_PER_CUSTOMER_MIN, ORDERS_PER_CUSTOMER_MAX)
        for _ in range(order_count):
            order_date = fake.date_time_between(start_date="-1y", end_date="now")
            total_amount = round(random.uniform(5.0, 5000.0), 2)
            status = random.choices(ORDER_STATUSES, weights=[10, 70, 10, 10])[0]
            category = random.choice(PRODUCT_CATEGORIES)
            address = fake.address().replace("\n", ", ")
            batch.append((customer_id, order_date, total_amount, status, category, address))

        if len(batch) >= BATCH_SIZE:
            _insert_order_batch(conn, batch)
            inserted += len(batch)
            print(f"  Orders inserted: {inserted:,}")
            batch = []

    if batch:
        _insert_order_batch(conn, batch)
        inserted += len(batch)
        print(f"  Orders inserted: {inserted:,}")

    print(f"Total orders inserted: {inserted:,}")


def _insert_order_batch(conn, rows: list[tuple]) -> None:
    """Insert a batch of order rows."""
    with conn.cursor() as cur:
        query = """
            INSERT INTO orders (customer_id, order_date, total_amount, status, product_category, shipping_address)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cur.executemany(query, rows)
    conn.commit()


def main():
    """Main entry point for data generation."""
    print("=" * 60)
    print("VortexDBA - SQL Server Synthetic Data Generator")
    print("=" * 60)

    start = time.time()
    init_tables_if_needed()
    conn = get_connection()

    try:
        customer_ids = generate_customers(conn, CUSTOMER_COUNT)
        generate_orders(conn, customer_ids)
    finally:
        conn.close()

    elapsed = time.time() - start
    print(f"\nData generation completed in {elapsed:.1f} seconds.")
    print("=" * 60)


if __name__ == "__main__":
    main()
