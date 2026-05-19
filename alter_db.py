import asyncio
from src.api.database import engine
from sqlalchemy import text

async def alter_db():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE bookings ADD COLUMN language VARCHAR(20) DEFAULT 'roman_urdu' NOT NULL;"))
            print("Added language column to bookings table successfully!")
        except Exception as e:
            print(f"Error adding language column: {e}")

if __name__ == "__main__":
    asyncio.run(alter_db())
