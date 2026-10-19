import asyncio
from sqlalchemy import text
from app.core.database import engine, Base
import app.models  # ensure models are imported

async def inspect_and_sync():
    async with engine.begin() as conn:
        # Check existing tables
        tables_res = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        existing_tables = [row[0] for row in tables_res.fetchall()]
        print(f"Existing tables in public schema: {existing_tables}")

        for tname in ["jobs", "job_attempts", "job_events", "job_outbox"]:
            if tname in existing_tables:
                cols_res = await conn.execute(text(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = '{tname}'
                    ORDER BY ordinal_position;
                """))
                cols = cols_res.fetchall()
                print(f"\n--- Columns in {tname} ---")
                for c in cols:
                    print(f"  {c[0]}: {c[1]} (nullable={c[2]}, default={c[3]})")
            else:
                print(f"\n--- Table {tname} does NOT exist ---")

asyncio.run(inspect_and_sync())
