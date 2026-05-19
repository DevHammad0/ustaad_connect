import asyncio
import os
import random
from sqlmodel import select
from src.api.database import engine
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.models import Provider

async def update_profile_pics():
    async with AsyncSession(engine, expire_on_commit=False) as session:
        result = await session.execute(select(Provider))
        providers = result.scalars().all()
        for provider in providers:
            random_id = random.randint(1, 99)
            provider.profile_pic_url = f"https://randomuser.me/api/portraits/men/{random_id}.jpg"
            session.add(provider)
            print(f"Updated {provider.name} with profile pic {provider.profile_pic_url}")
        await session.commit()
        print(f"Successfully updated {len(providers)} providers.")

if __name__ == "__main__":
    asyncio.run(update_profile_pics())
