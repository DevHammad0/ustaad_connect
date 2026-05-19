import asyncio
from sqlmodel import select, text
from src.api.database import engine
from sqlalchemy.ext.asyncio import AsyncSession

async def main():
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(text("SELECT customer_review FROM bookings LIMIT 1"))
            print("customer_review column exists!")
    except Exception as e:
        print("ERROR:", e)

asyncio.run(main())
