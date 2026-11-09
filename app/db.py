import os
import asyncpg

try:
    from app.config import DATABASE_URL
except ImportError:
    from config import DATABASE_URL

pool: asyncpg.Pool = None

async def init_db():
    global pool
    db_url = DATABASE_URL
    if db_url and db_url.startswith("postgresql:") and not db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql:", "postgresql://", 1)
        
    try:
        pool = await asyncpg.create_pool(db_url)
        await pool.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                id SERIAL PRIMARY KEY,
                source TEXT,
                destination TEXT,
                departure_date TEXT,
                num_days INT,
                travelers INT,
                itinerary TEXT,
                budget TEXT,
                flights TEXT,
                hotels TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            ALTER TABLE trips ADD COLUMN IF NOT EXISTS source TEXT;
            ALTER TABLE trips ADD COLUMN IF NOT EXISTS departure_date TEXT;
            ALTER TABLE trips ADD COLUMN IF NOT EXISTS num_days INT;
            ALTER TABLE trips ADD COLUMN IF NOT EXISTS travelers INT;
        """)
        print("Database connected and trips table initialized.")
    except Exception as e:
        print(f"Warning: Could not connect to database: {e}")
        pool = None

async def close_db():
    global pool
    if pool:
        await pool.close()
