import asyncio
from sqlmodel import select
from src.api.database import engine
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.models import Provider, ServiceType

providers_to_add = [
    {
        "name": "Khyber AC Techs",
        "service_type": "ac_repair",
        "visit_fee": 500,
        "rating_total": 48.0,
        "rating_count": 10,
        "lat": 33.9917,
        "lng": 71.4753,
        "city": "peshawar",
        "area": "University Road",
        "phone": "923000000101",
        "years_experience": 5,
        "is_active": True,
        "is_verified": True,
        "total_jobs_done": 10
    },
    {
        "name": "Hayatabad Smart Electricians",
        "service_type": "electrician",
        "visit_fee": 400,
        "rating_total": 49.0,
        "rating_count": 10,
        "lat": 33.9848,
        "lng": 71.4542,
        "city": "peshawar",
        "area": "Hayatabad",
        "phone": "923000000102",
        "years_experience": 8,
        "is_active": True,
        "is_verified": True,
        "total_jobs_done": 10
    },
    {
        "name": "Cantt Plumbing Experts",
        "service_type": "plumber",
        "visit_fee": 600,
        "rating_total": 45.0,
        "rating_count": 10,
        "lat": 34.0096,
        "lng": 71.5609,
        "city": "peshawar",
        "area": "Peshawar Cantt",
        "phone": "923000000103",
        "years_experience": 10,
        "is_active": True,
        "is_verified": True,
        "total_jobs_done": 10
    },
    {
        "name": "Town Handyman Services",
        "service_type": "handyman",
        "visit_fee": 350,
        "rating_total": 47.0,
        "rating_count": 10,
        "lat": 34.0025,
        "lng": 71.4807,
        "city": "peshawar",
        "area": "Peshawar Town",
        "phone": "923000000104",
        "years_experience": 6,
        "is_active": True,
        "is_verified": True,
        "total_jobs_done": 10
    }
]

async def seed():
    async with AsyncSession(engine, expire_on_commit=False) as session:
        for p in providers_to_add:
            provider = Provider(
                name=p["name"],
                phone=p["phone"],
                service_type=ServiceType(p["service_type"]),
                city=p["city"],
                area=p["area"],
                lat=p["lat"],
                lng=p["lng"],
                visit_fee=p["visit_fee"],
                years_experience=p["years_experience"],
                is_active=p["is_active"],
                is_verified=p["is_verified"],
                rating_total=p["rating_total"],
                rating_count=p["rating_count"],
                total_jobs_done=p["total_jobs_done"],
            )
            session.add(provider)
        await session.commit()
        print("Inserted mock data for Peshawar.")

asyncio.run(seed())
