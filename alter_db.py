import asyncio
from src.api.database import engine
from sqlalchemy import text

async def alter_db():
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        try:
            await conn.execute(text("ALTER TYPE servicetype ADD VALUE 'handyman';"))
            print("Added handyman to ServiceType")
        except Exception as e:
            print(f"Error adding handyman: {e}")

    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE providers ADD COLUMN visit_fee INTEGER DEFAULT 500 NOT NULL;"))
            print("Added visit_fee")
        except Exception as e:
            print(f"Error adding visit_fee: {e}")

asyncio.run(alter_db())
