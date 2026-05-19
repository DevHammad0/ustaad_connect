import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.database import engine
from src.api.models import Provider, ServiceType

real_data = [
    {
        "name": "Maqsood & Sons AC Repair",
        "phone": "923111000103",
        "cnic": "37405-1111111-1",
        "profile_pic_url": "https://example.com/profiles/maqsood.jpg",
        "bio": "Expert inverter, split, and window AC repair, installation, and gas refilling.",
        "service_type": "ac_repair",
        "area": "G-13",
        "lat": 33.6938,
        "lng": 73.0512,
        "visit_fee": 600,
        "is_active": True,
        "is_verified": True,
        "rating_total": 48.0,
        "rating_count": 10,
        "years_experience": 15,
        "total_jobs_done": 120
    },
    {
        "name": "AC Doctor Islamabad",
        "phone": "923335383666",
        "cnic": "37405-2222222-2",
        "profile_pic_url": "https://example.com/profiles/acdoctor.jpg",
        "bio": "HVAC maintenance, AC repair, and inverter service across E-11.",
        "service_type": "ac_repair",
        "area": "E-11",
        "lat": 33.7050,
        "lng": 73.0234,
        "visit_fee": 550,
        "is_active": True,
        "is_verified": True,
        "rating_total": 49.0,
        "rating_count": 10,
        "years_experience": 12,
        "total_jobs_done": 95
    },
    {
        "name": "Kareegar Electricals",
        "phone": "923424405239",
        "cnic": "37405-3333333-3",
        "profile_pic_url": "https://example.com/profiles/kareegar.jpg",
        "bio": "Specialized AC repair and electrical services in Islamabad.",
        "service_type": "electrician",
        "area": "F-11",
        "lat": 33.6981,
        "lng": 73.0601,
        "visit_fee": 450,
        "is_active": True,
        "is_verified": True,
        "rating_total": 45.0,
        "rating_count": 10,
        "years_experience": 8,
        "total_jobs_done": 60
    },
    {
        "name": "Mahir Company Plumbing",
        "phone": "923001112223",
        "cnic": "37405-4444444-4",
        "profile_pic_url": "https://example.com/profiles/mahir.jpg",
        "bio": "Professional plumbing services provided by Mahir Company.",
        "service_type": "plumber",
        "area": "G-11",
        "lat": 33.7102,
        "lng": 73.0389,
        "visit_fee": 700,
        "is_active": True,
        "is_verified": True,
        "rating_total": 47.0,
        "rating_count": 10,
        "years_experience": 5,
        "total_jobs_done": 80
    },
    {
        "name": "Hassan & Hussain Enterprises",
        "phone": "923009998887",
        "cnic": "37405-5555555-5",
        "profile_pic_url": "https://example.com/profiles/hassan.jpg",
        "bio": "Reliable AC service, plumbing, and gas filling in F-8.",
        "service_type": "plumber",
        "area": "F-8",
        "lat": 33.7215,
        "lng": 73.0267,
        "visit_fee": 500,
        "is_active": True,
        "is_verified": True,
        "rating_total": 46.0,
        "rating_count": 10,
        "years_experience": 20,
        "total_jobs_done": 200
    }
]

async def update_isb():
    async with AsyncSession(engine, expire_on_commit=False) as session:
        result = await session.execute(select(Provider).where(Provider.city == "islamabad").order_by(Provider.id))
        providers = result.scalars().all()
        
        for idx, p in enumerate(providers):
            if idx < len(real_data):
                data = real_data[idx]
                p.name = data["name"]
                p.phone = data["phone"]
                p.cnic = data["cnic"]
                p.profile_pic_url = data["profile_pic_url"]
                p.bio = data["bio"]
                p.service_type = ServiceType(data["service_type"])
                p.area = data["area"]
                p.lat = data["lat"]
                p.lng = data["lng"]
                p.visit_fee = data["visit_fee"]
                p.is_active = data["is_active"]
                p.is_verified = data["is_verified"]
                p.rating_total = data["rating_total"]
                p.rating_count = data["rating_count"]
                p.years_experience = data["years_experience"]
                p.total_jobs_done = data["total_jobs_done"]
                session.add(p)
        
        await session.commit()
        print("Updated Islamabad providers with real data.")

if __name__ == "__main__":
    asyncio.run(update_isb())
