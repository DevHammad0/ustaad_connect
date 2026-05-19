import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.database import engine, submit_rating

async def main():
    try:
        async with AsyncSession(engine) as session:
            # use a known booking id, e.g. 2
            await submit_rating(session, 2, 5, "bohat achi service ti")
            print("Successfully submitted rating!")
    except Exception as e:
        print("ERROR:", str(e))
        import traceback
        traceback.print_exc()

asyncio.run(main())
