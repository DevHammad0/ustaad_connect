# Environment Variables Setup Guide

This guide explains how to obtain every value needed in your `.env` file.
Copy `.env.example` to `.env` and fill in each value using the instructions below.

```bash
cp .env.example .env
```

---

## 1. `OPENAI_API_KEY`

**What it is:** Your OpenAI secret key. Used by the Ustaad Agent to run GPT-4o-mini.

**How to get it:**
1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click **"Create new secret key"**
3. Give it a name (e.g. `ustaad-connect`)
4. Copy the key — it starts with `sk-`

> ⚠️ You can only see the key once. Copy it immediately.

**Format:** `sk-proj-...` or `sk-...`

---

## 2. `DATABASE_URL`

**What it is:** PostgreSQL connection string for your Supabase database.

**How to get it:**
1. Go to [https://supabase.com](https://supabase.com) and open your project
2. Click **Project Settings** (gear icon, left sidebar)
3. Go to **Database** → scroll to **Connection string**
4. Select the **URI** tab
5. Switch the connection type to **Session mode** (port `5432`) — NOT Transaction mode
6. Copy the URI

**Format:**
```
postgresql+asyncpg://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres
```

> ⚠️ The URL from Supabase starts with `postgresql://` — **change it to `postgresql+asyncpg://`** so the async driver works.

> ⚠️ Replace `[YOUR-PASSWORD]` in the URL with your actual database password set during project creation.

---

## 3. `UPSTASH_REDIS_URL`

**What it is:** Redis connection string for Upstash. Used for AI agent session memory and geocoding cache.

**How to get it:**
1. Go to [https://console.upstash.com](https://console.upstash.com)
2. Create a new **Redis** database (choose the region closest to your Supabase region)
3. After creation, go to the database page
4. Under **Connect** → find the **Redis URL**
5. Copy the URL that starts with `rediss://`

**Format:**
```
rediss://default:AxxxxxxxxxxxxxxxxxxxxxxxxxxxQ@xxxx.upstash.io:6379
```

> ℹ️ The `rediss://` (with double `s`) means TLS-encrypted — Upstash requires this.

---

## 4. `META_WHATSAPP_TOKEN`

**What it is:** Bearer token used to call the Meta WhatsApp Cloud API to send messages to customers.

**How to get it:**
1. Go to [https://developers.facebook.com](https://developers.facebook.com)
2. Create or open your **Meta App** (type: Business)
3. Add the **WhatsApp** product to your app
4. Go to **WhatsApp → API Setup**
5. Under **Temporary access token** — copy the token shown

> ⚠️ The temporary token expires in 24 hours. For production, generate a **Permanent Token**:
> - Go to **Business Settings → System Users**
> - Create a system user with Admin role
> - Generate a token with `whatsapp_business_messaging` permission

**Format:** `EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## 5. `META_PHONE_NUMBER_ID`

**What it is:** The numeric ID of your WhatsApp Business phone number registered with Meta.

**How to get it:**
1. In the Meta Developer Console, go to **WhatsApp → API Setup**
2. Under **From** (the phone number section) — you'll see a number like `123456789012345`
3. This is your **Phone Number ID** (not the actual phone number itself)

**Format:** A long numeric string, e.g. `123456789012345`

> ℹ️ For testing, Meta gives you a free sandbox number. For production, you register your own business phone number.

---

## 6. `APP_SECRET`

**What it is:** A secret string that protects all API endpoints. Every request must include `X-App-Secret: <value>` in the header.

**How to generate it:**
```bash
# Option 1 — Python
python -c "import secrets; print(secrets.token_hex(32))"

# Option 2 — PowerShell
[System.Web.Security.Membership]::GeneratePassword(32, 0)

# Option 3 — Just type any random string (min 32 chars recommended)
```

**Format:** Any random string, e.g. `a3f8c2d1e9b47f6a1c2d3e4f5a6b7c8d`

> ⚠️ Keep this secret. Anyone with this value can call your API.

---

## Final `.env` Example (with real values filled in)

```env
OPENAI_API_KEY=sk-proj-abc123...

DATABASE_URL=postgresql+asyncpg://postgres.xyzabc:mypassword@aws-0-eu-central-1.pooler.supabase.com:5432/postgres

UPSTASH_REDIS_URL=rediss://default:AbCdEf123@innocent-cat-12345.upstash.io:6379

META_WHATSAPP_TOKEN=EAABwzLixnjYBOxxxxxxxxxxxxxxxx

META_PHONE_NUMBER_ID=123456789012345

APP_SECRET=a3f8c2d1e9b47f6a1c2d3e4f5a6b7c8d
```

---

## Quick Verification

Once your `.env` is filled, you can verify connectivity before starting the server:

```bash
# Check DB connection
uv run python -c "
import asyncio, os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine(os.environ['DATABASE_URL'])
async def test():
    async with engine.begin() as conn:
        result = await conn.execute(__import__('sqlalchemy').text('SELECT 1'))
        print('✅ DB connected:', result.scalar())
asyncio.run(test())
"

# Check Redis connection
uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv()
from upstash_redis import Redis
r = Redis.from_url(os.environ['UPSTASH_REDIS_URL'])
r.set('ping', 'pong')
print('✅ Redis connected:', r.get('ping'))
"
```
