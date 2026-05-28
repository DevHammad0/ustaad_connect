import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from src.api.database import get_session
from src.api.models import Provider, Booking, BookingStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# GET /admin/api/data
# ---------------------------------------------------------------------------
@router.get("/api/data")
async def get_admin_data(session: AsyncSession = Depends(get_session)):
    """Fetches stats, providers, and bookings for the admin panel."""
    # Fetch Providers
    provider_res = await session.execute(
        select(Provider).order_by(Provider.joined_at.desc())
    )
    providers = provider_res.scalars().all()

    # Fetch Bookings with relations
    booking_res = await session.execute(
        select(Booking)
        .options(
            selectinload(Booking.customer),
            selectinload(Booking.provider),
        )
        .order_by(Booking.created_at.desc())
    )
    bookings = booking_res.scalars().all()

    # Calculate Stats
    total_providers = len(providers)
    verified_providers = sum(1 for p in providers if p.is_verified)
    active_bookings = sum(
        1
        for b in bookings
        if b.status
        in (
            BookingStatus.pending,
            BookingStatus.accepted,
            BookingStatus.confirmed,
            BookingStatus.en_route,
            BookingStatus.arrived,
        )
    )
    completed_bookings = sum(
        1 for b in bookings if b.status == BookingStatus.completed
    )
    total_earnings = sum(b.final_cost or 0 for b in bookings)

    # Serialize
    serialized_providers = []
    for p in providers:
        serialized_providers.append({
            "id": p.id,
            "name": p.name,
            "phone": p.phone,
            "cnic": p.cnic or "N/A",
            "cnic_front_url": p.cnic_front_url,
            "cnic_back_url": p.cnic_back_url,
            "profile_pic_url": p.profile_pic_url,
            "service_type": p.service_type.value,
            "city": p.city,
            "area": p.area or "N/A",
            "visit_fee": p.visit_fee,
            "is_active": p.is_active,
            "is_verified": p.is_verified,
            "average_rating": p.average_rating or 0.0,
            "rating_count": p.rating_count,
            "total_jobs_done": p.total_jobs_done,
        })

    serialized_bookings = []
    for b in bookings:
        serialized_bookings.append({
            "id": b.id,
            "customer_name": b.customer.name if b.customer else "N/A",
            "customer_phone": b.customer.phone if b.customer else "N/A",
            "provider_name": b.provider.name if b.provider else "N/A",
            "status": b.status.value,
            "estimated_cost_min": b.estimated_cost_min,
            "estimated_cost_max": b.estimated_cost_max,
            "final_cost": b.final_cost,
            "rating": b.customer_rating,
            "review": b.customer_review,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    return {
        "stats": {
            "total_providers": total_providers,
            "verified_providers": verified_providers,
            "active_bookings": active_bookings,
            "completed_bookings": completed_bookings,
            "total_earnings": total_earnings,
        },
        "providers": serialized_providers,
        "bookings": serialized_bookings,
    }


# ---------------------------------------------------------------------------
# POST /admin/api/provider/{provider_id}/verify
# ---------------------------------------------------------------------------
@router.post("/api/provider/{provider_id}/verify")
async def verify_provider(
    provider_id: int, session: AsyncSession = Depends(get_session)
):
    """Toggles or sets the is_verified status for a provider."""
    result = await session.execute(
        select(Provider).where(Provider.id == provider_id)
    )
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider.is_verified = not provider.is_verified
    session.add(provider)
    await session.commit()
    await session.refresh(provider)

    return {"success": True, "is_verified": provider.is_verified}


# ---------------------------------------------------------------------------
# POST /admin/api/provider/{provider_id}/toggle-active
# ---------------------------------------------------------------------------
@router.post("/api/provider/{provider_id}/toggle-active")
async def toggle_provider_active(
    provider_id: int, session: AsyncSession = Depends(get_session)
):
    """Toggles the active status of a provider."""
    result = await session.execute(
        select(Provider).where(Provider.id == provider_id)
    )
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider.is_active = not provider.is_active
    session.add(provider)
    await session.commit()
    await session.refresh(provider)

    return {"success": True, "is_active": provider.is_active}


# ---------------------------------------------------------------------------
# GET /admin
# ---------------------------------------------------------------------------
@router.get("", response_class=HTMLResponse)
async def serve_admin_panel():
    """Serves a premium HTML/CSS/JS single page application."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ustaad Connect - Admin Console</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --surface-color: rgba(22, 30, 49, 0.65);
            --border-color: rgba(255, 255, 255, 0.08);
            --primary: #00b4d8;
            --primary-glow: rgba(0, 180, 216, 0.15);
            --primary-gradient: linear-gradient(135deg, #1d3557, #457b9d);
            --teal-brand: #0f4c5c;
            --accent: #ffb703;
            --text-main: #f8f9fa;
            --text-muted: #94a3b8;
            --success: #2ec4b6;
            --error: #e63946;
            --font-display: 'Outfit', sans-serif;
            --font-body: 'Plus Jakarta Sans', sans-serif;
            --radius-lg: 20px;
            --radius-md: 12px;
            --transition-smooth: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: var(--font-body);
            min-height: 100vh;
            overflow-x: hidden;
            background-image: 
                radial-gradient(at 10% 10%, rgba(29, 53, 87, 0.3) 0px, transparent 50%),
                radial-gradient(at 90% 90%, rgba(15, 76, 92, 0.3) 0px, transparent 50%);
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 24px;
        }

        /* --- Header --- */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
        }

        .logo-section h1 {
            font-family: var(--font-display);
            font-size: 32px;
            font-weight: 800;
            background: linear-gradient(135deg, #f8f9fa, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }

        .logo-section p {
            color: var(--text-muted);
            font-size: 14px;
            margin-top: 4px;
        }

        .refresh-btn {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 12px 24px;
            border-radius: var(--radius-md);
            font-family: var(--font-display);
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: var(--transition-smooth);
            backdrop-filter: blur(10px);
        }

        .refresh-btn:hover {
            border-color: var(--primary);
            box-shadow: 0 0 15px var(--primary-glow);
            transform: translateY(-2px);
        }

        /* --- Stats Grid --- */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }

        .stat-card {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 24px;
            backdrop-filter: blur(12px);
            display: flex;
            flex-direction: column;
            gap: 8px;
            position: relative;
            overflow: hidden;
            transition: var(--transition-smooth);
        }

        .stat-card:hover {
            transform: translateY(-4px);
            border-color: rgba(255, 255, 255, 0.15);
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--primary);
            opacity: 0.7;
        }

        .stat-card.stats-earnings::before { background: var(--accent); }
        .stat-card.stats-active::before { background: var(--success); }

        .stat-label {
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
        }

        .stat-value {
            font-family: var(--font-display);
            font-size: 36px;
            font-weight: 800;
            letter-spacing: -0.5px;
        }

        /* --- Tab System --- */
        .tab-nav {
            display: flex;
            gap: 12px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 16px;
            margin-bottom: 30px;
        }

        .tab-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 10px 20px;
            font-family: var(--font-display);
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition-smooth);
            position: relative;
        }

        .tab-btn:hover {
            color: var(--text-main);
        }

        .tab-btn.active {
            color: var(--primary);
        }

        .tab-btn.active::after {
            content: '';
            position: absolute;
            bottom: -17px;
            left: 0;
            width: 100%;
            height: 2px;
            background: var(--primary);
            box-shadow: 0 0 10px var(--primary);
        }

        .tab-content {
            display: none;
            animation: fadeIn 0.4s ease-out;
        }

        .tab-content.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* --- Panel Card & Tables --- */
        .panel-card {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            overflow: hidden;
            backdrop-filter: blur(12px);
        }

        .table-responsive {
            width: 100%;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        th {
            background: rgba(255, 255, 255, 0.02);
            padding: 16px 24px;
            font-family: var(--font-display);
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border-color);
        }

        td {
            padding: 18px 24px;
            border-bottom: 1px solid var(--border-color);
            font-size: 14px;
            color: var(--text-main);
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover td {
            background: rgba(255, 255, 255, 0.01);
        }

        /* --- Components & Badges --- */
        .provider-cell {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .provider-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.05);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            border: 1.5px solid var(--border-color);
            overflow: hidden;
        }

        .provider-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .provider-info .p-name {
            font-weight: 600;
            color: var(--text-main);
        }

        .provider-info .p-phone {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            padding: 6px 12px;
            border-radius: 50px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .badge-verified {
            background: rgba(46, 196, 182, 0.12);
            color: var(--success);
            border: 1px solid rgba(46, 196, 182, 0.2);
        }

        .badge-unverified {
            background: rgba(230, 57, 70, 0.12);
            color: var(--error);
            border: 1px solid rgba(230, 57, 70, 0.2);
        }

        .badge-status {
            background: rgba(255, 255, 255, 0.06);
            color: var(--text-main);
        }

        .badge-status.completed {
            background: rgba(46, 196, 182, 0.12);
            color: var(--success);
        }

        .badge-status.cancelled {
            background: rgba(230, 57, 70, 0.12);
            color: var(--error);
        }

        .badge-status.confirmed, .badge-status.accepted {
            background: rgba(0, 180, 216, 0.12);
            color: var(--primary);
        }

        .badge-status.en_route, .badge-status.arrived {
            background: rgba(255, 183, 3, 0.12);
            color: var(--accent);
        }

        /* --- Toggle Switch --- */
        .switch {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 24px;
        }

        .switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--border-color);
            transition: .3s;
            border-radius: 34px;
        }

        .slider:before {
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
        }

        input:checked + .slider {
            background-color: var(--primary);
        }

        input:checked + .slider:before {
            transform: translateX(20px);
        }

        /* --- Buttons --- */
        .action-btn {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 8px 14px;
            border-radius: var(--radius-md);
            font-size: 12px;
            font-family: var(--font-display);
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition-smooth);
        }

        .action-btn:hover {
            border-color: var(--primary);
            color: var(--primary);
        }

        .action-btn.btn-verify {
            background: var(--primary);
            color: #0b0f19;
            border: none;
        }

        .action-btn.btn-verify:hover {
            background: #0096b2;
            color: #0b0f19;
        }

        .doc-link {
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
            transition: var(--transition-smooth);
            cursor: pointer;
        }

        .doc-link:hover {
            text-decoration: underline;
        }

        /* --- Modal --- */
        .modal {
            display: none;
            position: fixed;
            z-index: 100;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(11, 15, 25, 0.85);
            backdrop-filter: blur(8px);
            align-items: center;
            justify-content: center;
            padding: 24px;
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: #111827;
            border: 1px solid var(--border-color);
            max-width: 700px;
            width: 100%;
            border-radius: var(--radius-lg);
            overflow: hidden;
            position: relative;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            animation: modalScale 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        @keyframes modalScale {
            from { transform: scale(0.9); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }

        .modal-header {
            padding: 20px 24px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modal-title {
            font-family: var(--font-display);
            font-size: 18px;
            font-weight: 700;
        }

        .close-modal {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 24px;
            cursor: pointer;
            transition: var(--transition-smooth);
        }

        .close-modal:hover {
            color: var(--text-main);
        }

        .modal-body {
            padding: 24px;
            text-align: center;
        }

        .modal-body img {
            max-width: 100%;
            max-height: 450px;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-color);
            object-fit: contain;
        }

        /* --- Provider Review Modal Styles --- */
        .provider-review-grid {
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            gap: 30px;
        }
        @media (max-width: 768px) {
            .provider-review-grid {
                grid-template-columns: 1fr;
            }
        }
        .review-avatar-header {
            display: flex;
            align-items: center;
            gap: 16px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
        }
        .review-avatar {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            font-weight: 700;
            overflow: hidden;
        }
        .review-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .detail-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px dashed rgba(255, 255, 255, 0.05);
        }
        .detail-item:last-child {
            border-bottom: none;
        }
        .detail-label {
            color: var(--text-muted);
            font-size: 14px;
        }
        .detail-val {
            color: var(--text-main);
            font-weight: 500;
            font-size: 14px;
        }
        .docs-grid {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .doc-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 12px;
            cursor: pointer;
            transition: var(--transition-smooth);
        }
        .doc-card:hover {
            border-color: var(--primary);
            background: rgba(255, 255, 255, 0.04);
        }
        .doc-card-title {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .doc-preview {
            height: 130px;
            border-radius: 8px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(0, 0, 0, 0.2);
            color: var(--text-muted);
            font-size: 13px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .doc-preview img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div class="logo-section">
                <h1>Ustaad Connect</h1>
                <p>Provider Administration Console</p>
            </div>
            <button class="refresh-btn" onclick="fetchData()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                Refresh Board
            </button>
        </header>

        <!-- Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Providers</div>
                <div id="stat-total-providers" class="stat-value">--</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Verified Providers</div>
                <div id="stat-verified-providers" class="stat-value">--</div>
            </div>
            <div class="stat-card stats-active">
                <div class="stat-label">Active Bookings</div>
                <div id="stat-active-bookings" class="stat-value">--</div>
            </div>
            <div class="stat-card stats-earnings">
                <div class="stat-label">Total Platform Volume</div>
                <div id="stat-earnings" class="stat-value">Rs. --</div>
            </div>
        </div>

        <!-- Navigation -->
        <div class="tab-nav">
            <button class="tab-btn active" onclick="switchTab(event, 'providers-tab')">Providers Management</button>
            <button class="tab-btn" onclick="switchTab(event, 'bookings-tab')">Bookings & Jobs Log</button>
        </div>

        <!-- Providers Tab -->
        <div id="providers-tab" class="tab-content active">
            <div class="panel-card">
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Provider</th>
                                <th>Service Area</th>
                                <th>CNIC / Docs</th>
                                <th>Status</th>
                                <th>Rating / Jobs</th>
                                <th>Active</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody id="providers-table-body">
                            <tr>
                                <td colspan="7" style="text-align: center; color: var(--text-muted);">Loading providers...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Bookings Tab -->
        <div id="bookings-tab" class="tab-content">
            <div class="panel-card">
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Booking ID</th>
                                <th>Customer</th>
                                <th>Assigned Provider</th>
                                <th>Status</th>
                                <th>Final Cost</th>
                                <th>Feedback</th>
                                <th>Created At</th>
                            </tr>
                        </thead>
                        <tbody id="bookings-table-body">
                            <tr>
                                <td colspan="7" style="text-align: center; color: var(--text-muted);">Loading bookings...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- Image Modal -->
    <div id="image-modal" class="modal" onclick="closeModal()">
        <div class="modal-content" onclick="event.stopPropagation()">
            <div class="modal-header">
                <div class="modal-title" id="modal-title">Document View</div>
                <button class="close-modal" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <img id="modal-img" src="" alt="CNIC Document">
            </div>
        </div>
    </div>

    <!-- Provider Review Modal -->
    <div id="provider-modal" class="modal" onclick="closeProviderModal()">
        <div class="modal-content" style="max-width: 900px;" onclick="event.stopPropagation()">
            <div class="modal-header">
                <div class="modal-title">Provider Verification Profile</div>
                <button class="close-modal" onclick="closeProviderModal()">&times;</button>
            </div>
            <div class="modal-body" style="text-align: left; padding: 30px;">
                <div class="provider-review-grid">
                    <!-- Left Column: Info & Details -->
                    <div class="review-info-section">
                        <div class="review-avatar-header">
                            <div class="review-avatar" id="review-avatar"></div>
                            <div>
                                <h3 id="review-name" style="font-family: var(--font-display); font-size: 24px; font-weight: 700; color: var(--text-main);"></h3>
                                <p id="review-service" style="color: var(--primary); font-weight: 600; font-size: 14px; margin-top: 4px;"></p>
                            </div>
                        </div>
                        
                        <div class="details-list" style="margin-top: 24px; display: flex; flex-direction: column; gap: 12px;">
                            <div class="detail-item">
                                <span class="detail-label">Phone:</span>
                                <span class="detail-val" id="review-phone"></span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">CNIC Number:</span>
                                <span class="detail-val" id="review-cnic" style="font-weight: 600; letter-spacing: 0.5px;"></span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">City / Area:</span>
                                <span class="detail-val" id="review-location"></span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Visit Fee:</span>
                                <span class="detail-val" id="review-fee"></span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Verification Status:</span>
                                <span id="review-status"></span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Right Column: Documents -->
                    <div class="review-docs-section">
                        <h4 style="font-family: var(--font-display); margin-bottom: 16px; font-size: 16px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.8px;">Verification Documents</h4>
                        <div class="docs-grid">
                            <div class="doc-card" onclick="zoomDoc('front')">
                                <div class="doc-card-title">CNIC Front Scan</div>
                                <div class="doc-preview" id="doc-front-preview">No Image</div>
                            </div>
                            <div class="doc-card" onclick="zoomDoc('back')">
                                <div class="doc-card-title">CNIC Back Scan</div>
                                <div class="doc-preview" id="doc-back-preview">No Image</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="modal-footer" style="margin-top: 30px; padding-top: 20px; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end; gap: 12px;">
                    <button class="action-btn" onclick="closeProviderModal()">Cancel</button>
                    <button class="action-btn" id="modal-verify-btn" onclick="modalToggleVerify()"></button>
                </div>
            </div>
        </div>
    </div>

    <!-- Scripting -->
    <script>
        let allProviders = [];
        let activeProviderId = null;

        async function fetchData() {
            try {
                const response = await fetch('/admin/api/data');
                const data = await response.json();
                
                allProviders = data.providers;

                // Update Stats
                document.getElementById('stat-total-providers').textContent = data.stats.total_providers;
                document.getElementById('stat-verified-providers').textContent = data.stats.verified_providers;
                document.getElementById('stat-active-bookings').textContent = data.stats.active_bookings;
                document.getElementById('stat-earnings').textContent = 'Rs. ' + data.stats.total_earnings.toLocaleString();

                // Build Providers Table
                const providersBody = document.getElementById('providers-table-body');
                if (data.providers.length === 0) {
                    providersBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No providers registered yet.</td></tr>`;
                } else {
                    providersBody.innerHTML = data.providers.map(p => {
                        const verifyBtnText = p.is_verified ? 'Unverify' : 'Verify';
                        const verifyBtnClass = p.is_verified ? 'action-btn' : 'action-btn btn-verify';
                        const verifyBadge = p.is_verified 
                            ? `<span class="badge badge-verified">Verified</span>`
                            : `<span class="badge badge-unverified">Unverified</span>`;
                        
                        const frontDoc = p.cnic_front_url 
                            ? `<a class="doc-link" onclick="openModal('${p.cnic_front_url}', '${p.name} - CNIC Front')">Front</a>`
                            : `<span style="color: var(--text-muted);">No Front</span>`;
                        
                        const backDoc = p.cnic_back_url 
                            ? `<a class="doc-link" onclick="openModal('${p.cnic_back_url}', '${p.name} - CNIC Back')">Back</a>`
                            : `<span style="color: var(--text-muted);">No Back</span>`;

                        const avatar = p.profile_pic_url 
                            ? `<img src="${p.profile_pic_url}" alt="Profile">`
                            : p.name.charAt(0).toUpperCase();

                        return `
                            <tr>
                                <td>
                                    <div class="provider-cell" style="cursor: pointer;" onclick="openProviderModal(${p.id})">
                                        <div class="provider-avatar">${avatar}</div>
                                        <div class="provider-info">
                                            <div class="p-name" style="text-decoration: underline; text-decoration-color: rgba(255,255,255,0.2);">${p.name}</div>
                                            <div class="p-phone">${p.phone}</div>
                                        </div>
                                    </div>
                                </td>
                                <td>
                                    <div><strong>${p.city.toUpperCase()}</strong></div>
                                    <div style="font-size: 12px; color: var(--text-muted);">${p.area}</div>
                                </td>
                                <td>
                                    <div style="font-weight: 500;">${p.cnic}</div>
                                    <div style="font-size: 12px; margin-top: 4px; display: flex; gap: 8px;">
                                        ${frontDoc} | ${backDoc}
                                    </div>
                                </td>
                                <td>${verifyBadge}</td>
                                <td>
                                    <div>⭐ <strong>${p.average_rating.toFixed(1)}</strong> (${p.rating_count})</div>
                                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">${p.total_jobs_done} jobs completed</div>
                                </td>
                                <td>
                                    <label class="switch">
                                        <input type="checkbox" ${p.is_active ? 'checked' : ''} onchange="toggleActive(${p.id})">
                                        <span class="slider"></span>
                                    </label>
                                </td>
                                <td>
                                    <div style="display: flex; gap: 8px;">
                                        <button class="action-btn" onclick="openProviderModal(${p.id})">Review Docs</button>
                                        <button class="${verifyBtnClass}" onclick="toggleVerify(${p.id})">${verifyBtnText}</button>
                                    </div>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }

                // Build Bookings Table
                const bookingsBody = document.getElementById('bookings-table-body');
                if (data.bookings.length === 0) {
                    bookingsBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No bookings created yet.</td></tr>`;
                } else {
                    bookingsBody.innerHTML = data.bookings.map(b => {
                        const finalCostText = b.final_cost ? 'Rs. ' + b.final_cost.toLocaleString() : '-';
                        const ratingText = b.rating ? '⭐ ' + b.rating : '-';
                        const reviewText = b.review ? `<div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">"${b.review}"</div>` : '';

                        return `
                            <tr>
                                <td><strong>#${b.id}</strong></td>
                                <td>
                                    <div><strong>${b.customer_name}</strong></div>
                                    <div style="font-size: 12px; color: var(--text-muted);">${b.customer_phone}</div>
                                </td>
                                <td><strong>${b.provider_name}</strong></td>
                                <td><span class="badge badge-status ${b.status}">${b.status.replace('_', ' ')}</span></td>
                                <td><strong>${finalCostText}</strong></td>
                                <td>
                                    <div><strong>${ratingText}</strong></div>
                                    ${reviewText}
                                </td>
                                <td style="color: var(--text-muted);">${b.created_at}</td>
                            </tr>
                        `;
                    }).join('');
                }

            } catch (error) {
                console.error("Error fetching data:", error);
            }
        }

        async function toggleVerify(providerId) {
            try {
                const res = await fetch(`/admin/api/provider/${providerId}/verify`, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    fetchData();
                }
            } catch (e) {
                console.error("Error verifying provider:", e);
            }
        }

        async function toggleActive(providerId) {
            try {
                await fetch(`/admin/api/provider/${providerId}/toggle-active`, { method: 'POST' });
            } catch (e) {
                console.error("Error toggling active status:", e);
            }
        }

        function switchTab(evt, tabId) {
            // Hide all contents
            const contents = document.getElementsByClassName('tab-content');
            for (let i = 0; i < contents.length; i++) {
                contents[i].classList.remove('active');
            }

            // Remove active classes on nav
            const btns = document.getElementsByClassName('tab-btn');
            for (let i = 0; i < btns.length; i++) {
                btns[i].classList.remove('active');
            }

            // Set active
            document.getElementById(tabId).classList.add('active');
            evt.currentTarget.classList.add('active');
        }

        function openModal(url, title) {
            document.getElementById('modal-img').src = url;
            document.getElementById('modal-title').textContent = title;
            document.getElementById('image-modal').classList.add('active');
        }

        function closeModal() {
            document.getElementById('image-modal').classList.remove('active');
            document.getElementById('modal-img').src = '';
        }

        function openProviderModal(providerId) {
            const p = allProviders.find(x => x.id === providerId);
            if (!p) return;
            
            activeProviderId = providerId;
            
            // Set name and service
            document.getElementById('review-name').textContent = p.name;
            document.getElementById('review-service').textContent = p.service_type;
            
            // Set avatar
            const avatarContainer = document.getElementById('review-avatar');
            if (p.profile_pic_url) {
                avatarContainer.innerHTML = `<img src="${p.profile_pic_url}" alt="Profile">`;
            } else {
                avatarContainer.textContent = p.name.charAt(0).toUpperCase();
                avatarContainer.innerHTML = p.name.charAt(0).toUpperCase();
            }
            
            // Set details
            document.getElementById('review-phone').textContent = p.phone;
            document.getElementById('review-cnic').textContent = p.cnic;
            document.getElementById('review-location').textContent = `${p.city.toUpperCase()} (${p.area || 'N/A'})`;
            document.getElementById('review-fee').textContent = `Rs. ${p.visit_fee}`;
            
            // Status badge
            const statusContainer = document.getElementById('review-status');
            if (p.is_verified) {
                statusContainer.innerHTML = `<span class="badge badge-verified">Verified</span>`;
            } else {
                statusContainer.innerHTML = `<span class="badge badge-unverified">Unverified</span>`;
            }
            
            // CNIC Front
            const frontContainer = document.getElementById('doc-front-preview');
            if (p.cnic_front_url) {
                frontContainer.innerHTML = `<img src="${p.cnic_front_url}" alt="CNIC Front">`;
                frontContainer.style.cursor = 'pointer';
            } else {
                frontContainer.innerHTML = '<span>No Front Image Uploaded</span>';
                frontContainer.style.cursor = 'default';
            }
            
            // CNIC Back
            const backContainer = document.getElementById('doc-back-preview');
            if (p.cnic_back_url) {
                backContainer.innerHTML = `<img src="${p.cnic_back_url}" alt="CNIC Back">`;
                backContainer.style.cursor = 'pointer';
            } else {
                backContainer.innerHTML = '<span>No Back Image Uploaded</span>';
                backContainer.style.cursor = 'default';
            }
            
            // Verify button in modal
            const verifyBtn = document.getElementById('modal-verify-btn');
            verifyBtn.textContent = p.is_verified ? 'Unverify Provider' : 'Approve & Verify Provider';
            if (p.is_verified) {
                verifyBtn.className = 'action-btn';
            } else {
                verifyBtn.className = 'action-btn btn-verify';
            }
            
            document.getElementById('provider-modal').classList.add('active');
        }
        
        function closeProviderModal() {
            document.getElementById('provider-modal').classList.remove('active');
            activeProviderId = null;
        }
        
        async function modalToggleVerify() {
            if (!activeProviderId) return;
            await toggleVerify(activeProviderId);
            setTimeout(() => {
                openProviderModal(activeProviderId);
            }, 250);
        }
        
        function zoomDoc(side) {
            const p = allProviders.find(x => x.id === activeProviderId);
            if (!p) return;
            if (side === 'front' && p.cnic_front_url) {
                openModal(p.cnic_front_url, `${p.name} - CNIC Front`);
            } else if (side === 'back' && p.cnic_back_url) {
                openModal(p.cnic_back_url, `${p.name} - CNIC Back`);
            }
        }

        // Load initially
        window.addEventListener('DOMContentLoaded', fetchData);
    </script>
</body>
</html>"""
    return html_content
