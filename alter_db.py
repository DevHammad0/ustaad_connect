import asyncio
from src.api.database import engine
from sqlalchemy import text

async def alter_db():
    async with engine.begin() as conn:
        # Add cnic_front_url
        try:
            await conn.execute(text("ALTER TABLE providers ADD COLUMN cnic_front_url VARCHAR(500);"))
            print("Added cnic_front_url to providers table successfully!")
        except Exception as e:
            print(f"Error adding cnic_front_url: {e}")

        # Add cnic_back_url
        try:
            await conn.execute(text("ALTER TABLE providers ADD COLUMN cnic_back_url VARCHAR(500);"))
            print("Added cnic_back_url to providers table successfully!")
        except Exception as e:
            print(f"Error adding cnic_back_url: {e}")

if __name__ == "__main__":
    asyncio.run(alter_db())
