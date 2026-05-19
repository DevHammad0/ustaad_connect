import pytest
import json
import asyncio
from fastapi.testclient import TestClient
from sqlmodel import select

from src.api.models import BookingStatus, CancelledBy, Provider, Customer, Booking
from src.api.database import get_booking_with_relations

# Import decorated tools from agent
from src.api.agent import (
    check_customer_exists as _check_customer_exists_tool,
    register_customer as _register_customer_tool,
    fetch_available_providers as _fetch_available_providers_tool,
    initiate_provider_booking as _initiate_provider_booking_tool,
    check_booking_status as _check_booking_status_tool,
    cancel_booking as _cancel_booking_tool,
    request_location as _request_location_tool,
    confirm_booking as _confirm_booking_tool,
)

# Helper to unwrap OpenAI Agents SDK FunctionTool into its callable Python core
def _unwrap_tool(tool_obj):
    invoker = tool_obj.on_invoke_tool
    impl = invoker._invoke_tool_impl
    for cell in impl.__closure__:
        if callable(cell.cell_contents) and cell.cell_contents.__name__ == tool_obj.name:
            return cell.cell_contents
    raise ValueError(f"Could not extract raw function for tool {tool_obj.name}")

# Expose callable core functions for tests
check_customer_exists = _unwrap_tool(_check_customer_exists_tool)
register_customer = _unwrap_tool(_register_customer_tool)
fetch_available_providers = _unwrap_tool(_fetch_available_providers_tool)
initiate_provider_booking = _unwrap_tool(_initiate_provider_booking_tool)
check_booking_status = _unwrap_tool(_check_booking_status_tool)
cancel_booking = _unwrap_tool(_cancel_booking_tool)
request_location = _unwrap_tool(_request_location_tool)
confirm_booking = _unwrap_tool(_confirm_booking_tool)

# Mark all tests in this file as async for pytest-asyncio
pytestmark = pytest.mark.asyncio

# Headers with X-App-Secret for authenticated endpoints
HEADERS = {"X-App-Secret": "test_app_secret"}

# ===========================================================================
# 1. System Endpoints
# ===========================================================================

@pytest.mark.asyncio
async def test_health_check(client: TestClient):
    """Test 1: GET /health returns 200 and system details without auth."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ustaad-connect"}


@pytest.mark.asyncio
async def test_unauthenticated_requests(client: TestClient):
    """Test 2: All api routes must block requests without correct X-App-Secret."""
    response = client.get("/api/provider/1/active-job")
    assert response.status_code == 401
    assert "Invalid or missing X-App-Secret header" in response.json()["detail"]


# ===========================================================================
# 2. Database & Core Query Helper Tools (Direct Invocation)
# ===========================================================================

@pytest.mark.asyncio
async def test_tool_check_customer_not_found(session):
    """Test 3: check_customer_exists tool returns found=False for unregistered phone."""
    result_str = await check_customer_exists(phone="923000000000")
    result = json.loads(result_str)
    assert result == {"found": False}


@pytest.mark.asyncio
async def test_tool_register_customer(session):
    """Test 4: register_customer tool correctly inserts customer into database."""
    result_str = await register_customer(phone="923001234567", name="Ahmad Khan")
    result = json.loads(result_str)
    assert result["registered"] is True
    assert result["name"] == "Ahmad Khan"
    assert result["phone"] == "923001234567"

    # Verify db record
    db_result = await session.execute(select(Customer).where(Customer.phone == "923001234567"))
    customer = db_result.scalars().first()
    assert customer is not None
    assert customer.name == "Ahmad Khan"


@pytest.mark.asyncio
async def test_tool_check_customer_found(session):
    """Test 5: check_customer_exists tool returns customer details after registration."""
    # First register
    await register_customer(phone="923001234567", name="Ahmad Khan")
    
    # Then check
    result_str = await check_customer_exists(phone="923001234567")
    result = json.loads(result_str)
    assert result["found"] is True
    assert result["name"] == "Ahmad Khan"


@pytest.mark.asyncio
async def test_tool_fetch_available_providers(session):
    """Test 6: fetch_available_providers returns seeded providers in the resolved city."""
    # Seeded Islamabad lat/lng coords should resolve Islamabad providers
    result_str = await fetch_available_providers(
        service_type="ac_repair",
        lat=33.6938,
        lng=73.0512
    )
    providers = json.loads(result_str)
    assert len(providers) > 0
    assert all(p["service_type"] == "ac_repair" for p in providers)
    assert providers[0]["name"] == "Ustad Riaz Ahmed"  # Handled nearest first


@pytest.mark.asyncio
async def test_tool_initiate_provider_booking(session):
    """Test 7: initiate_provider_booking creates a booking in pending status."""
    # Register customer
    await register_customer(phone="923001234567", name="Ahmad Khan")
    
    # Find a provider ID
    providers_str = await fetch_available_providers("ac_repair", 33.6938, 73.0512)
    provider_id = json.loads(providers_str)[0]["id"]

    # Book provider
    booking_str = await initiate_provider_booking(
        customer_phone="923001234567",
        provider_id=provider_id,
        issue="AC not cooling",
        lat=33.6938,
        lng=73.0512,
        service_type="ac_repair"
    )
    booking_res = json.loads(booking_str)
    
    assert "booking_id" in booking_res
    assert booking_res["status"] == "pending"
    
    # Check status tool
    status_str = await check_booking_status(customer_phone="923001234567")
    status_res = json.loads(status_str)
    assert status_res["status"] == "pending"
    assert "intezaar" in status_res["status_label"]


# ===========================================================================
# 3. End-to-End API Booking & Status Lifecycles
# ===========================================================================

@pytest.mark.asyncio
async def test_full_booking_lifecycle_api(client: TestClient):
    """Test 8-12: Complete sequential API lifecycle from empty active state to completion & rating."""
    # Step A: Confirm active job returns 404 for provider at start
    response = client.get("/api/provider/1/active-job", headers=HEADERS)
    assert response.status_code == 404

    # Step B: Register a customer via chat endpoint
    phone = "923007777777"
    name = "Muhammad Ali"
    client.post(
        "/api/customer/chat",
        headers=HEADERS,
        json={"phone": phone, "message": "Hi"}
    )
    
    # Step C: Complete registration and booking directly using tools
    cust = await register_customer(phone, name)
    provs_str = await fetch_available_providers("plumber", 33.6938, 73.0512)
    prov_id = json.loads(provs_str)[0]["id"]
    booking_str = await initiate_provider_booking(
        customer_phone=phone,
        provider_id=prov_id,
        issue="Water pipe leakage",
        lat=33.6938,
        lng=73.0512,
        service_type="plumber"
    )
    booking_data = json.loads(booking_str)
    booking_id = booking_data["booking_id"]
    provider_id = booking_data["provider"]["id"]

    # Step D: Provider checks active job -> Should return 200 with the active booking details
    response = client.get(f"/api/provider/{provider_id}/active-job", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["booking_id"] == booking_id
    assert response.json()["status"] == "pending"
    assert response.json()["customer_name"] == name

    # Step E: Provider accepts booking, setting a cost estimate range of PKR 500-800
    response = client.post(
        f"/api/provider/bookings/{booking_id}/accept",
        headers=HEADERS,
        json={"estimated_cost_min": 500, "estimated_cost_max": 800}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert response.json()["estimated_cost_min"] == 500
    assert response.json()["estimated_cost_max"] == 800

    # Step F: Provider confirms the booking to start the job
    response = client.post(
        f"/api/provider/bookings/{booking_id}/confirm",
        headers=HEADERS
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"

    # Step G: Provider sets status to 'en_route' (on the way)
    response = client.post(
        f"/api/provider/bookings/{booking_id}/status",
        headers=HEADERS,
        json={"status": "en_route"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "en_route"

    # Step H: Provider sets status to 'arrived' at the customer's house
    response = client.post(
        f"/api/provider/bookings/{booking_id}/status",
        headers=HEADERS,
        json={"status": "arrived"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "arrived"

    # Step I: Provider marks work completed with a final cost of PKR 750
    response = client.post(
        f"/api/provider/bookings/{booking_id}/complete",
        headers=HEADERS,
        json={"final_cost": 750}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["final_cost"] == 750

    # Step J: Active job for provider should return 404 now that it's completed
    response = client.get(f"/api/provider/{provider_id}/active-job", headers=HEADERS)
    assert response.status_code == 404

    # Step K: Customer rates the completed booking 5 stars with a nice review
    response = client.post(
        f"/api/customer/bookings/{booking_id}/rate",
        headers=HEADERS,
        json={"rating": 5, "review": "Bohot acha kaam kiya, highly recommended!"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_rating_validations_and_double_rating(client: TestClient):
    """Test 13: Customer cannot rate twice, and cannot rate incomplete bookings."""
    phone = "923008888888"
    name = "Kamran Shah"
    
    # Establish a booking
    cust = await register_customer(phone, name)
    provs_str = await fetch_available_providers("electrician", 33.6938, 73.0512)
    prov_id = json.loads(provs_str)[0]["id"]
    booking_str = await initiate_provider_booking(
        customer_phone=phone,
        provider_id=prov_id,
        issue="Short circuit",
        lat=33.6938,
        lng=73.0512,
        service_type="electrician"
    )
    booking_data = json.loads(booking_str)
    booking_id = booking_data["booking_id"]

    # Try to rate a PENDING booking -> Must fail with 400
    response = client.post(
        f"/api/customer/bookings/{booking_id}/rate",
        headers=HEADERS,
        json={"rating": 5}
    )
    assert response.status_code == 400
    assert "Only completed bookings can be rated" in response.json()["detail"]

    # Advance booking to completed state
    client.post(f"/api/provider/bookings/{booking_id}/accept", headers=HEADERS, json={"estimated_cost_min": 400, "estimated_cost_max": 600})
    client.post(f"/api/provider/bookings/{booking_id}/confirm", headers=HEADERS)
    client.post(f"/api/provider/bookings/{booking_id}/status", headers=HEADERS, json={"status": "en_route"})
    client.post(f"/api/provider/bookings/{booking_id}/status", headers=HEADERS, json={"status": "arrived"})
    client.post(f"/api/provider/bookings/{booking_id}/complete", headers=HEADERS, json={"final_cost": 500})

    # Rate completed booking successfully -> 200
    response = client.post(
        f"/api/customer/bookings/{booking_id}/rate",
        headers=HEADERS,
        json={"rating": 5}
    )
    assert response.status_code == 200

    # Rate again -> Must fail with 400 (prevent double rating)
    response = client.post(
        f"/api/customer/bookings/{booking_id}/rate",
        headers=HEADERS,
        json={"rating": 4}
    )
    assert response.status_code == 400
    assert "already submitted a rating" in response.json()["detail"]


# ===========================================================================
# 4. State Machine Violations & Cancellations
# ===========================================================================

@pytest.mark.asyncio
async def test_invalid_state_transitions(client: TestClient):
    """Test 14: API must block skipping stages or performing illegal state machine actions."""
    phone = "923009999999"
    name = "Haris Ali"
    
    # Establish booking
    cust = await register_customer(phone, name)
    provs_str = await fetch_available_providers("ac_repair", 33.6938, 73.0512)
    prov_id = json.loads(provs_str)[0]["id"]
    booking_str = await initiate_provider_booking(
        customer_phone=phone,
        provider_id=prov_id,
        issue="Compressor replacement",
        lat=33.6938,
        lng=73.0512,
        service_type="ac_repair"
    )
    booking_data = json.loads(booking_str)
    booking_id = booking_data["booking_id"]

    # Try setting en_route status directly on PENDING booking -> Must fail with 400
    response = client.post(
        f"/api/provider/bookings/{booking_id}/status",
        headers=HEADERS,
        json={"status": "en_route"}
    )
    assert response.status_code == 400
    assert "Invalid transition" in response.json()["detail"]

    # Try confirming job directly on PENDING booking (skipping accept stage) -> Must fail with 400
    response = client.post(
        f"/api/provider/bookings/{booking_id}/confirm",
        headers=HEADERS
    )
    assert response.status_code == 400
    assert "requires booking status 'accepted'" in response.json()["detail"]


@pytest.mark.asyncio
async def test_customer_booking_cancellation(session):
    """Test 15: Customers can cancel an active booking before job completes."""
    # Setup customer + booking
    await register_customer("923005555555", "Sarmad Bhatti")
    provs = json.loads(await fetch_available_providers("plumber", 33.6938, 73.0512))
    booking = json.loads(await initiate_provider_booking("923005555555", provs[0]["id"], "Leaky pipe", 33.6938, 73.0512, "plumber"))
    booking_id = booking["booking_id"]

    # Cancel booking
    cancel_res_str = await cancel_booking(booking_id=booking_id, customer_phone="923005555555")
    cancel_res = json.loads(cancel_res_str)
    
    assert cancel_res["status"] == "cancelled"
    assert "cancelled successfully" in cancel_res["message"]

    # Check status is now cancelled in db
    db_result = await session.execute(select(Booking).where(Booking.id == booking_id))
    db_booking = db_result.scalars().first()
    assert db_booking.status == BookingStatus.cancelled


@pytest.mark.asyncio
async def test_tool_request_location(session):
    """Test 16: request_location tool correctly dispatches the WhatsApp location request payload."""
    result_str = await request_location(phone="923001234567")
    result = json.loads(result_str)
    
    assert result["success"] is True
    assert result["action"] == "request_location"
    assert "sent successfully" in result["message"]


@pytest.mark.asyncio
async def test_webhook_verification(client):
    """Test 17: Webhook verification GET handshake reacts correctly to verify tokens."""
    # Valid token match
    response = client.get("/webhook?hub.mode=subscribe&hub.verify_token=ustaad_verify_token&hub.challenge=testchallenge")
    assert response.status_code == 200
    assert response.text == "testchallenge"

    # Invalid token mismatch
    response = client.get("/webhook?hub.mode=subscribe&hub.verify_token=wrong_token&hub.challenge=testchallenge")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_incoming_text(db_setup, monkeypatch):
    """Test 18: POST /webhook handles incoming WhatsApp text events and forwards to Agent."""
    # Mock Runner.run to prevent real LLM lookups in this specific request
    class MockResult:
        final_output = "Hello! Main aapki AC ki marammat mein madad kar sakta hoon."

    async def mock_runner_run(*args, **kwargs):
        return MockResult()

    monkeypatch.setattr("src.api.routes.webhook.Runner.run", mock_runner_run)

    # WhatsApp payload
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [
                                {
                                    "profile": {"name": "Hammad"},
                                    "wa_id": "923001234567"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "923001234567",
                                    "id": "wamid.HBgLOTIzMDAxMjM0NTY3",
                                    "timestamp": "1715971200",
                                    "text": {"body": "Mujhe AC theek karwana hai"},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    from httpx import AsyncClient, ASGITransport
    from src.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.text == "OK"


@pytest.mark.asyncio
async def test_webhook_incoming_location(db_setup, monkeypatch):
    """Test 19: POST /webhook successfully parses incoming native GPS location shares."""
    # Mock Runner.run to verify system prompt prepends coordinate details
    captured_input = []

    async def mock_runner_run(agent, input, session, context):
        captured_input.append(input)
        class MockResult:
            final_output = "Shukriya! Location mil gayi hai."
        return MockResult()

    monkeypatch.setattr("src.api.routes.webhook.Runner.run", mock_runner_run)

    # WhatsApp payload with location
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [
                                {
                                    "profile": {"name": "Hammad"},
                                    "wa_id": "923001234567"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "923001234567",
                                    "id": "wamid.HBgLOTIzMDAxMjM0NTY3TG9j",
                                    "timestamp": "1715971200",
                                    "location": {
                                        "latitude": 33.6844,
                                        "longitude": 73.0479
                                    },
                                    "type": "location"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    from httpx import AsyncClient, ASGITransport
    from src.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.text == "OK"

    # Wait briefly for background asyncio task execution
    await asyncio.sleep(0.2)

    assert len(captured_input) == 1
    assert "Lat: 33.6844" in captured_input[0]
    assert "Lng: 73.0479" in captured_input[0]


# ===========================================================================
# 6. Brand New Provider Endpoint Tests & AI Agent Interactive Confirmation Flow
# ===========================================================================


@pytest.mark.asyncio
async def test_provider_auth_flow(client: TestClient):
    """Test 20: Provider register and passwordless login endpoints."""
    # 1. Register a new provider
    reg_payload = {
        "name": "Ustad Farooq",
        "phone": "923058888888",
        "service_type": "plumber",
        "city": "lahore",
        "area": "Gulberg",
        "visit_fee": 600,
        "years_experience": 10,
        "lat": 31.5204,
        "lng": 74.3587,
        "cnic": "35201-1111111-1",
        "bio": "Expert plumbing services.",
        "profile_pic_url": "https://example.com/farooq.jpg"
    }
    response = client.post("/api/provider/register", json=reg_payload, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Ustad Farooq"
    assert data["phone"] == "923058888888"
    assert data["visit_fee"] == 600
    assert data["years_experience"] == 10
    assert data["is_verified"] is False
    assert "id" in data

    # Registering same phone number should raise 400
    response_dup = client.post("/api/provider/register", json=reg_payload, headers=HEADERS)
    assert response_dup.status_code == 400
    assert "already registered" in response_dup.json()["detail"]

    # 2. Login as the newly registered provider
    login_payload = {
        "phone": "923058888888"
    }
    response_login = client.post("/api/provider/login", json=login_payload, headers=HEADERS)
    assert response_login.status_code == 200
    login_data = response_login.json()
    assert login_data["id"] == data["id"]
    assert login_data["phone"] == "923058888888"

    # Login with non-existing provider should raise 404
    bad_login = {"phone": "923999999999"}
    response_bad = client.post("/api/provider/login", json=bad_login, headers=HEADERS)
    assert response_bad.status_code == 404
    assert "No provider profile matches" in response_bad.json()["detail"]


@pytest.mark.asyncio
async def test_provider_profile_get_and_update(client: TestClient):
    """Test 21: GET /profile and PUT /profile endpoints for providers."""
    # Register provider first
    reg_payload = {
        "name": "Ustad Hamid",
        "phone": "923057777777",
        "service_type": "electrician",
        "city": "islamabad",
        "area": "G-11",
        "visit_fee": 500,
        "years_experience": 5,
        "lat": 33.7102,
        "lng": 73.0389,
        "cnic": "37405-2222222-2"
    }
    resp = client.post("/api/provider/register", json=reg_payload, headers=HEADERS)
    prov_id = resp.json()["id"]

    # Get profile
    response = client.get(f"/api/provider/{prov_id}/profile", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Ustad Hamid"
    assert data["visit_fee"] == 500

    # Get non-existing profile
    response_bad = client.get("/api/provider/9999/profile", headers=HEADERS)
    assert response_bad.status_code == 404

    # Update profile (is_active, bio, visit_fee, area)
    update_payload = {
        "is_active": False,
        "bio": "Now available only on weekends.",
        "visit_fee": 750,
        "area": "G-13"
    }
    response_update = client.put(f"/api/provider/{prov_id}/profile", json=update_payload, headers=HEADERS)
    assert response_update.status_code == 200
    updated_data = response_update.json()
    assert updated_data["is_active"] is False
    assert updated_data["bio"] == "Now available only on weekends."
    assert updated_data["visit_fee"] == 750
    assert updated_data["area"] == "G-13"


@pytest.mark.asyncio
async def test_provider_location_update(client: TestClient, session):
    """Test 22: Background coordinate tracking updates via POST /location."""
    # Seed or get a provider (ID 1 exists from seed data in db_setup)
    loc_payload = {
        "lat": 33.6666,
        "lng": 73.1111
    }
    response = client.post("/api/provider/1/location", json=loc_payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Location updated successfully."}

    # Verify db was updated
    db_result = await session.execute(select(Provider).where(Provider.id == 1))
    provider = db_result.scalars().first()
    assert provider.lat == 33.6666
    assert provider.lng == 73.1111


@pytest.mark.asyncio
async def test_provider_bookings_history(client: TestClient):
    """Test 23: History of booking records via GET /bookings."""
    # Provider 1 exists. Let's fetch history (initially empty)
    response = client.get("/api/provider/1/bookings", headers=HEADERS)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_confirm_booking_tool_flow(db_setup):
    """Test 24: Direct invocation of confirm_booking tool transitions state from accepted to confirmed."""
    # Register customer
    await register_customer(phone="923038571702", name="Hammad")
    
    # Provider 1 is seeded. Create a booking.
    from src.api.database import create_booking as db_create_booking, update_booking, engine
    from src.api.models import BookingStatus
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async with AsyncSession(engine) as init_session:
        booking = await db_create_booking(
            init_session,
            customer_id=1,
            provider_id=1,
            issue="AC gas leakage",
            lat=33.6938,
            lng=73.0512,
            city="islamabad",
            service_type="ac_repair",
            idempotency_key="idemp-confirm-123"
        )
        booking_id = booking.id
    
    # Directly confirming pending booking should fail (must be accepted first)
    res_str_bad = await confirm_booking(customer_phone="923038571702", booking_id=booking_id)
    assert "Booking cannot be confirmed" in res_str_bad
    
    # Accept booking (mimics provider app input) and commit it
    async with AsyncSession(engine) as update_session:
        await update_booking(
            update_session,
            booking_id,
            status=BookingStatus.accepted,
            estimated_cost_min=1000,
            estimated_cost_max=1500
        )
    
    # Verify confirm_booking tool successfully transitions booking to confirmed
    res_str = await confirm_booking(customer_phone="923038571702", booking_id=booking_id)
    res = json.loads(res_str)
    assert res["status"] == "confirmed"
    assert "is on their way" in res["message"]
    
    # Verify db status is confirmed
    async with AsyncSession(engine) as verify_session:
        db_result = await verify_session.execute(select(Booking).where(Booking.id == booking_id))
        booking_db = db_result.scalars().first()
        assert booking_db.status == BookingStatus.confirmed


@pytest.mark.asyncio
async def test_webhook_interactive_button_reply(db_setup, monkeypatch):
    """Test 25: Webhook handles button_reply and routes it to agent."""
    captured_input = []

    async def mock_runner_run(agent, input, session, context):
        captured_input.append(input)
        class MockResult:
            final_output = "Mocked confirm response!"
        return MockResult()

    monkeypatch.setattr("src.api.routes.webhook.Runner.run", mock_runner_run)

    # Webhook payload for interactive button click
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [{"profile": {"name": "Hammad"}, "wa_id": "923038571702"}],
                            "messages": [
                                {
                                    "from": "923038571702",
                                    "id": "wamid.interactive123",
                                    "timestamp": "1715971200",
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {
                                            "id": "confirm_booking",
                                            "title": "Confirm Booking"
                                        }
                                    }
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    from httpx import AsyncClient, ASGITransport
    from src.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.text == "OK"

    await asyncio.sleep(0.1)
    assert len(captured_input) == 1
    assert "Confirm Booking" in captured_input[0]
    assert "Customer Phone is 923038571702" in captured_input[0]


@pytest.mark.asyncio
async def test_accept_booking_interactive_whatsapp_dispatch(client: TestClient, monkeypatch):
    """Test 26: Provider accept endpoint sends WhatsApp interactive reply buttons instead of plaintext."""
    captured_dispatches = []

    async def mock_send_interactive(to_phone, body_text, buttons, header_text, footer_text):
        captured_dispatches.append({
            "to_phone": to_phone,
            "body_text": body_text,
            "buttons": buttons,
            "header_text": header_text,
            "footer_text": footer_text
        })
        return True

    monkeypatch.setattr(
        "src.api.routes.provider.send_whatsapp_interactive_buttons",
        mock_send_interactive
    )

    # Provider 1 is G-13 AC Repair. Create a booking.
    from src.api.database import create_booking as db_create_booking
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import engine

    # Register customer outside session block (it manages its own connection)
    await register_customer(phone="923038571702", name="Hammad")

    async with AsyncSession(engine) as session:
        booking = await db_create_booking(
            session,
            customer_id=1,
            provider_id=1,
            issue="AC gas leak",
            lat=33.6938,
            lng=73.0512,
            city="islamabad",
            service_type="ac_repair",
            idempotency_key="idemp-accept-buttons-1"
        )
        booking_id = booking.id

    # Call Accept Booking Endpoint
    accept_payload = {
        "estimated_cost_min": 1200,
        "estimated_cost_max": 1800
    }
    response = client.post(
        f"/api/provider/bookings/{booking_id}/accept",
        json=accept_payload,
        headers=HEADERS
    )
    assert response.status_code == 200
    assert response.json()["whatsapp_sent"] is True

    # Check mocked send_whatsapp_interactive_buttons invocation
    assert len(captured_dispatches) == 1
    dispatch = captured_dispatches[0]
    assert dispatch["to_phone"] == "923038571702"
    assert "Estimated Repair Cost" in dispatch["body_text"]
    assert "PKR 1200" in dispatch["body_text"]
    assert "1800" in dispatch["body_text"]
    assert "PKR 500" in dispatch["body_text"]
    assert len(dispatch["buttons"]) == 2
    assert dispatch["buttons"][0] == {"id": "confirm_booking", "title": "Confirm Booking"}
    assert dispatch["buttons"][1] == {"id": "cancel_booking", "title": "Cancel Booking"}
