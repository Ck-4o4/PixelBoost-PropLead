import io
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Query, Header, HTTPException, UploadFile, File, Depends, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import pandas as pd

from database import db, clean_phone
from scraper import scraper_instance
import phonepe_gateway
from auth import (
    create_access_token,
    decode_access_token,
    verify_password,
    hash_password
)

app = FastAPI(title="PixelBoost PropLeadAi SaaS Engine", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Pricing Plans Matrix (INR)
# =============================================================================
OFFICIAL_PLANS = [
    {
        "id": "free",
        "name": "Free Trial",
        "badge": "🆓 Free",
        "leads": 5,
        "price": 0,
        "price_display": "₹0",
        "price_per_lead": "Free",
        "description": "5 free demo leads without signup to test real-time phone & Instagram extraction.",
        "features": [
            "5 Verified Real Estate Leads",
            "Direct Phone & WhatsApp Actions",
            "Instagram Profile Links",
            "Live Google Maps Stream",
            "Instant Test (No Signup)"
        ],
        "popular": False,
        "button_text": "Current Trial (5 Leads)",
        "is_free": True
    },
    {
        "id": "starter",
        "name": "Starter",
        "badge": "🚀 Starter",
        "leads": 5,
        "price": 79,
        "price_display": "₹79",
        "price_per_lead": "₹15.80 / lead",
        "description": "Quick verified pack for individual brokers and local real estate consultants.",
        "features": [
            "5 Verified Direct Contacts",
            "Automatic Phone Deduplication",
            "Direct Dial & 1-Click WhatsApp",
            "Instagram Handle Discovery",
            "Saved in Calling CRM Table"
        ],
        "popular": False,
        "button_text": "Buy Starter (₹79)",
        "is_free": False
    },
    {
        "id": "growth",
        "name": "Growth",
        "badge": "📈 Growth",
        "leads": 40,
        "price": 499,
        "price_display": "₹499",
        "price_per_lead": "₹12.48 / lead",
        "description": "Perfect for active real estate telecallers covering specific micro-markets.",
        "features": [
            "40 High-Intent Verified Leads",
            "All Indian Cities & Localities",
            "Excel & CSV Telecalling Sheets",
            "Calling Pipeline Status Tracking",
            "Inline Notes Auto-Saving"
        ],
        "popular": False,
        "button_text": "Buy Growth (₹499)",
        "is_free": False
    },
    {
        "id": "professional",
        "name": "Professional",
        "badge": "⭐ Professional",
        "leads": 100,
        "price": 999,
        "price_display": "₹999",
        "price_per_lead": "₹9.99 / lead",
        "description": "Our most popular package for growing property agencies and channel partners.",
        "features": [
            "100 Premium Verified Leads",
            "All 25+ Indian Business Categories",
            "Priority Headless Scraping Speed",
            "Formatted Calling Sheet Downloads",
            "Full Multi-Tenant CRM Workspace",
            "Priority WhatsApp Support"
        ],
        "popular": True,
        "button_text": "Buy Professional (₹999)",
        "is_free": False
    },
    {
        "id": "agency",
        "name": "Agency",
        "badge": "🏢 Agency",
        "leads": "250+",
        "price": "Custom",
        "price_display": "Custom",
        "price_per_lead": "Best Volume Rates",
        "description": "High-volume bulk data and multi-caller setups for marketing agencies and developers.",
        "features": [
            "250+ to 10,000+ Verified Leads",
            "Custom City Expansion on Demand",
            "Multi-Agent CRM Team Logins",
            "Dedicated Account Manager",
            "Custom API & CRM Integration"
        ],
        "popular": False,
        "button_text": "Contact Sales",
        "is_free": False
    }
]

# =============================================================================
# Request & Response Models
# =============================================================================
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    company: Optional[str] = ""

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class CreateUserRequest(BaseModel):
    email: str
    password: str
    name: str
    company: Optional[str] = ""
    role: Optional[str] = "client"
    credits_limit: Optional[int] = 1000

class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    status: Optional[str] = None
    credits_limit: Optional[int] = None
    password: Optional[str] = None
    role: Optional[str] = None

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    category: Optional[str] = None
    website: Optional[str] = None
    instagram: Optional[str] = None
    call_status: Optional[str] = None
    call_notes: Optional[str] = None

class BulkDeleteRequest(BaseModel):
    ids: List[int]

class BulkStatusRequest(BaseModel):
    ids: List[int]
    call_status: str

# =============================================================================
# Authentication Dependencies
# =============================================================================
def get_optional_user(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> Optional[Dict[str, Any]]:
    """
    Extracts user if valid JWT is present, or returns None (Guest mode).
    """
    jwt_token = None
    if authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            jwt_token = parts[1]
    elif token:
        jwt_token = token

    if not jwt_token:
        return None

    payload = decode_access_token(jwt_token)
    if not payload or "sub" not in payload:
        return None

    user_id = payload.get("sub")
    try:
        user = db.get_user_by_id(int(user_id))
        if user and user["status"] != "suspended":
            return user
    except Exception:
        pass
    return None

def get_current_user(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Strict auth requirement for private endpoints.
    """
    user = get_optional_user(authorization=authorization, token=token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def require_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Ensures current authenticated user is Master Admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: Master Admin privileges required."
        )
    return current_user

# =============================================================================
# Plans & Pricing API
# =============================================================================
@app.get("/api/plans")
def get_plans():
    """Returns official pricing matrix."""
    return {"plans": OFFICIAL_PLANS}

# =============================================================================
# Auth Endpoints
# =============================================================================
@app.post("/api/auth/register")
def register(payload: RegisterRequest):
    success, msg, user_id = db.create_user(
        email=payload.email,
        password=payload.password,
        name=payload.name,
        company=payload.company or "",
        role="client",
        credits_limit=5
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)

    user = db.get_user_by_id(user_id)
    access_token = create_access_token(
        data={"sub": str(user["id"]), "email": user["email"], "role": user["role"]},
        expires_delta=timedelta(days=30)
    )
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "company": user["company"],
            "role": user["role"],
            "credits_limit": user["credits_limit"],
            "credits_used": user["credits_used"],
            "credits_remaining": max(0, user["credits_limit"] - user["credits_used"])
        }
    }

@app.post("/api/auth/login")
def login(payload: LoginRequest):
    user = db.get_user_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password.")

    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid email or password.")

    if user["status"] == "suspended":
        raise HTTPException(status_code=403, detail="Your account is suspended. Contact PixelBoost support.")

    access_token = create_access_token(
        data={"sub": str(user["id"]), "email": user["email"], "role": user["role"]},
        expires_delta=timedelta(days=30)
    )

    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "company": user["company"],
            "role": user["role"],
            "credits_limit": user["credits_limit"],
            "credits_used": user["credits_used"],
            "credits_remaining": max(0, user["credits_limit"] - user["credits_used"])
        }
    }

@app.get("/api/auth/me")
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "company": current_user["company"],
        "role": current_user["role"],
        "credits_limit": current_user["credits_limit"],
        "credits_used": current_user["credits_used"],
        "credits_remaining": max(0, current_user["credits_limit"] - current_user["credits_used"])
    }

@app.post("/api/auth/change-password")
def change_password(payload: ChangePasswordRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not verify_password(payload.old_password, current_user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters.")

    success = db.update_user(current_user["id"], {"password": payload.new_password})
    return {"success": success, "message": "Password changed successfully."}

# =============================================================================
# Master Admin Endpoints (For CK / PixelBoost Admin)
# =============================================================================
@app.get("/api/admin/users")
def list_clients(admin_user: Dict[str, Any] = Depends(require_admin_user)):
    users = db.get_all_users()
    sanitized = []
    for u in users:
        d = dict(u)
        d.pop("password_hash", None)
        d["credits_remaining"] = max(0, d.get("credits_limit", 0) - d.get("credits_used", 0))
        sanitized.append(d)
    return {"users": sanitized, "count": len(sanitized)}

@app.post("/api/admin/users")
def create_client(payload: CreateUserRequest, admin_user: Dict[str, Any] = Depends(require_admin_user)):
    success, msg, new_id = db.create_user(
        email=payload.email,
        password=payload.password,
        name=payload.name,
        company=payload.company or "",
        role=payload.role or "client",
        credits_limit=payload.credits_limit or 1000
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg, "user_id": new_id}

@app.patch("/api/admin/users/{user_id}")
def update_client(user_id: int, payload: UpdateUserRequest, admin_user: Dict[str, Any] = Depends(require_admin_user)):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        return {"success": True, "message": "No updates provided."}
    success = db.update_user(user_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="User not found or update failed.")
    return {"success": True, "message": "User updated successfully."}

@app.delete("/api/admin/users/{user_id}")
def delete_client(user_id: int, admin_user: Dict[str, Any] = Depends(require_admin_user)):
    if user_id == admin_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own master admin account.")
    success = db.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"success": True, "message": "User and their data deleted successfully."}

@app.get("/api/admin/stats")
def get_master_admin_stats(admin_user: Dict[str, Any] = Depends(require_admin_user)):
    stats = db.get_admin_stats()
    return stats

# =============================================================================
# Multi-Tenant Leads & CRM Endpoints
# =============================================================================
@app.get("/api/stats")
def get_stats(user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    if not user:
        # Fresh guest visitor starts with 0 leads
        return {
            "total_leads": 0,
            "with_phone": 0,
            "without_phone": 0,
            "status_counts": {},
            "total_searches": 0,
            "user_credits": {
                "limit": 5,
                "used": 0,
                "remaining": 5,
                "is_guest": True
            }
        }

    user_id = None if user["role"] == "admin" else user["id"]
    stats = db.get_stats(user_id=user_id)
    stats["user_credits"] = {
        "limit": user["credits_limit"],
        "used": user["credits_used"],
        "remaining": max(0, user["credits_limit"] - user["credits_used"])
    }
    return stats

@app.get("/api/areas")
def get_areas(user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    user_id = None
    if user:
        user_id = None if user["role"] == "admin" else user["id"]
    return {"areas": db.get_unique_areas(user_id=user_id)}

@app.get("/api/leads")
def get_leads(
    search: str = Query("", description="Search term across name, phone, address, notes"),
    status: str = Query("", description="Filter by call status"),
    category: str = Query("", description="Filter by category"),
    city: str = Query("", description="Filter by city/area"),
    has_phone: Optional[bool] = Query(None, description="Filter by presence of phone number"),
    min_rating: float = Query(0.0, description="Filter by minimum rating"),
    sort_by: str = Query("id", description="Field to sort by"),
    order: str = Query("DESC", description="ASC or DESC"),
    limit: int = Query(200, description="Number of results"),
    offset: int = Query(0, description="Offset for pagination"),
    client_id: Optional[int] = Query(None, description="Master Admin filter for specific tenant"),
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    if not user:
        # Unauthenticated guest visitor starts fresh with 0 leads until they generate
        return {"leads": [], "count": 0, "is_guest": True}

    target_user_id = user["id"]
    if user["role"] == "admin":
        target_user_id = client_id

    leads = db.get_leads(
        user_id=target_user_id,
        search=search,
        status=status,
        category=category,
        city=city,
        has_phone=has_phone,
        min_rating=min_rating,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset
    )
    return {"leads": leads, "count": len(leads), "is_guest": False}

@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: int, user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    user_id = None
    if user:
        user_id = None if user["role"] == "admin" else user["id"]
    else:
        user_id = 0
    lead = db.get_lead_by_id(lead_id, user_id=user_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@app.patch("/api/leads/{lead_id}")
def update_lead(lead_id: int, payload: LeadUpdate, user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        return {"success": True, "message": "No updates provided"}
    user_id = None
    if user:
        user_id = None if user["role"] == "admin" else user["id"]
    else:
        user_id = 0
    success = db.update_lead(lead_id, updates, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found or update failed")
    return {"success": True, "lead": db.get_lead_by_id(lead_id, user_id=user_id)}

@app.delete("/api/leads/{lead_id}")
def delete_lead(lead_id: int, user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    user_id = None
    if user:
        user_id = None if user["role"] == "admin" else user["id"]
    else:
        user_id = 0
    success = db.delete_lead(lead_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True, "message": "Lead deleted"}

@app.post("/api/leads/bulk-delete")
def bulk_delete_leads(payload: BulkDeleteRequest, user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    user_id = None
    if user:
        user_id = None if user["role"] == "admin" else user["id"]
    else:
        user_id = 0
    deleted_count = db.bulk_delete(payload.ids, user_id=user_id)
    return {"success": True, "deleted_count": deleted_count}

@app.post("/api/leads/bulk-status")
def bulk_update_status(payload: BulkStatusRequest, user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    user_id = None
    if user:
        user_id = None if user["role"] == "admin" else user["id"]
    else:
        user_id = 0
    count = 0
    for lead_id in payload.ids:
        if db.update_lead(lead_id, {"call_status": payload.call_status}, user_id=user_id):
            count += 1
    return {"success": True, "updated_count": count}

# =============================================================================
# Scraping Engine SSE Stream (Supports 5 Free Leads Without Signup)
# =============================================================================
@app.post("/api/scrape/stop")
def stop_scraping(user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    scraper_instance.cancel()
    return {"success": True, "message": "Scrape cancellation requested."}

@app.get("/api/scrape/stream")
async def stream_scrape(
    query: str = Query(..., description="Search keywords"),
    city: str = Query("", description="Target city/area"),
    category: str = Query("Real Estate", description="Business category"),
    max_results: int = Query(30, description="Max leads to fetch"),
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    SSE stream for live scraping progress and newly extracted leads.
    - If user is logged in: validates credits quota and scopes leads to user.
    - If guest (no signup): permits up to 5 free test leads.
    """
    if user:
        tenant_id = user["id"]
    else:
        # 5 Free leads trial without signup
        tenant_id = 0
        max_results = min(max_results, 5)

    async def event_generator():
        try:
            if not user:
                yield f"data: {json.dumps({'type': 'log', 'message': '🎁 Free Trial Active: Extracting up to 5 free verified leads without signup...'})}\n\n"
            
            async for event in scraper_instance.scrape(
                query=query,
                max_results=max_results,
                city=city,
                category=category,
                user_id=tenant_id
            ):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.01)

            if not user:
                yield f"data: {json.dumps({'type': 'trial_completed', 'message': 'You have extracted 5 free leads! Upgrade to unlock unlimited lead generation.'})}\n\n"

        except asyncio.CancelledError:
            scraper_instance.cancel()
            yield f"data: {json.dumps({'type': 'log', 'message': 'Client disconnected / cancelled'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# =============================================================================
# Export & Import (Supports Free Guest Export & Tenant Isolation)
# =============================================================================
@app.get("/api/export/csv")
def export_csv(
    status: str = Query(""),
    city: str = Query(""),
    has_phone: Optional[bool] = Query(None),
    search: str = Query(""),
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    user_id = None
    limit = 50000
    if user:
        user_id = None if user["role"] == "admin" else user["id"]
    else:
        # Guest export of their 5 free leads
        user_id = 0
        limit = 5

    leads = db.get_leads(user_id=user_id, search=search, status=status, city=city, has_phone=has_phone, limit=limit)
    if not leads:
        df = pd.DataFrame(columns=[
            "ID", "Business Name", "Phone Number", "Address", "City", "Category",
            "Rating", "Reviews Count", "Website", "Instagram Profile", "Google Maps URL", "Call Status", "Call Notes", "Created Date"
        ])
    else:
        df = pd.DataFrame(leads)
        rename_map = {
            "id": "ID",
            "name": "Business Name",
            "phone": "Phone Number",
            "address": "Address",
            "city": "City",
            "category": "Category",
            "rating": "Rating",
            "reviews_count": "Reviews Count",
            "website": "Website",
            "instagram": "Instagram Profile",
            "maps_url": "Google Maps URL",
            "call_status": "Call Status",
            "call_notes": "Call Notes",
            "created_at": "Created Date"
        }
        cols_to_keep = [col for col in rename_map.keys() if col in df.columns]
        df = df[cols_to_keep].rename(columns=rename_map)

    stream = io.StringIO()
    df.to_csv(stream, index=False)
    stream.seek(0)
    
    filename = f"pixelboost_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/export/excel")
def export_excel(
    status: str = Query(""),
    city: str = Query(""),
    has_phone: Optional[bool] = Query(None),
    search: str = Query(""),
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    user_id = None
    limit = 50000
    if user:
        user_id = None if user["role"] == "admin" else user["id"]
    else:
        # Guest export of their 5 free leads
        user_id = 0
        limit = 5

    leads = db.get_leads(user_id=user_id, search=search, status=status, city=city, has_phone=has_phone, limit=limit)
    if not leads:
        df = pd.DataFrame(columns=[
            "ID", "Business Name", "Phone Number", "Address", "City", "Category",
            "Rating", "Reviews Count", "Website", "Instagram Profile", "Google Maps URL", "Call Status", "Call Notes", "Created Date"
        ])
    else:
        df = pd.DataFrame(leads)
        rename_map = {
            "id": "ID",
            "name": "Business Name",
            "phone": "Phone Number",
            "address": "Address",
            "city": "City",
            "category": "Category",
            "rating": "Rating",
            "reviews_count": "Reviews Count",
            "website": "Website",
            "instagram": "Instagram Profile",
            "maps_url": "Google Maps URL",
            "call_status": "Call Status",
            "call_notes": "Call Notes",
            "created_at": "Created Date"
        }
        cols_to_keep = [col for col in rename_map.keys() if col in df.columns]
        df = df[cols_to_keep].rename(columns=rename_map)

    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Calling List")
    stream.seek(0)

    filename = f"pixelboost_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/api/import/csv")
async def import_csv(file: UploadFile = File(...), current_user: Dict[str, Any] = Depends(get_current_user)):
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {str(e)}")

    name_col = next((c for c in df.columns if c.lower() in ["name", "business name", "title", "company"]), None)
    phone_col = next((c for c in df.columns if "phone" in c.lower() or "mobile" in c.lower() or "contact" in c.lower()), None)
    address_col = next((c for c in df.columns if "address" in c.lower() or "location" in c.lower()), None)
    city_col = next((c for c in df.columns if "city" in c.lower()), None)

    if not name_col:
        raise HTTPException(status_code=400, detail="CSV must contain a 'Name' or 'Business Name' column.")

    imported_count = 0
    new_count = 0
    tenant_id = current_user["id"]

    for _, row in df.iterrows():
        lead_data = {
            "name": str(row[name_col]) if pd.notna(row[name_col]) else "Unknown",
            "phone": str(row[phone_col]) if phone_col and pd.notna(row[phone_col]) else "",
            "address": str(row[address_col]) if address_col and pd.notna(row[address_col]) else "",
            "city": str(row[city_col]) if city_col and pd.notna(row[city_col]) else "",
            "category": "Imported CSV",
            "rating": 0.0,
            "reviews_count": 0,
            "website": "",
            "maps_url": "",
            "query": "CSV Import",
            "call_status": "New",
            "call_notes": ""
        }
        is_new, _ = db.insert_or_update_lead(lead_data, user_id=tenant_id)
        imported_count += 1
        if is_new:
            new_count += 1

    return {"success": True, "total_processed": imported_count, "new_leads_added": new_count}

# =============================================================================
# PhonePe Payment Gateway Integration
# =============================================================================
class PhonePeInitiateRequest(BaseModel):
    plan_name: str
    leads_count: int
    amount_inr: float
    mobile: Optional[str] = None

@app.post("/api/payment/phonepe/initiate")
async def initiate_payment(
    payload: PhonePeInitiateRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Creates a pending order and initiates PhonePe hosted checkout.
    Returns PhonePe payment redirect URL for frontend.
    """
    if payload.amount_inr <= 0:
        raise HTTPException(status_code=400, detail="Invalid plan amount.")

    # Determine base url
    base_url = str(request.base_url).rstrip("/")
    # If request came through a proxy or local port
    host_header = request.headers.get("x-forwarded-host") or request.headers.get("host")
    proto_header = request.headers.get("x-forwarded-proto", "http")
    if host_header:
        base_url = f"{proto_header}://{host_header}"

    result = await phonepe_gateway.initiate_phonepe_payment(
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_email=current_user["email"],
        plan_name=payload.plan_name,
        leads_count=payload.leads_count,
        amount_inr=payload.amount_inr,
        callback_base_url=base_url,
        mobile=payload.mobile
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.get("error", "Failed to initiate transaction with PhonePe.")
        )

    # Record order in local DB
    db.create_payment_order(
        user_id=current_user["id"],
        plan_name=payload.plan_name,
        leads_count=payload.leads_count,
        amount_inr=payload.amount_inr,
        transaction_id=result["merchant_txn_id"],
        provider="phonepe"
    )

    return {
        "success": True,
        "merchant_txn_id": result["merchant_txn_id"],
        "redirect_url": result["redirect_url"],
        "plan_name": payload.plan_name,
        "amount_inr": payload.amount_inr,
        "leads_count": payload.leads_count
    }

@app.api_route("/api/payment/phonepe/callback", methods=["GET", "POST"])
async def phonepe_callback(request: Request, txnId: Optional[str] = Query(None)):
    """
    PhonePe user redirect callback after payment attempt.
    Verifies transaction status directly with PhonePe Hermes API,
    credits the customer quota, and redirects to dashboard with status.
    """
    txn_id = txnId
    if not txn_id:
        # Check form data
        try:
            form = await request.form()
            txn_id = form.get("transactionId") or form.get("merchantTransactionId")
        except Exception:
            pass

    if not txn_id:
        return RedirectResponse(url="/?payment=failed&reason=missing_txn", status_code=303)

    payment = db.get_payment_by_txn_id(txn_id)
    if not payment:
        return RedirectResponse(url="/?payment=failed&reason=order_not_found", status_code=303)

    # Verify status from PhonePe API
    status_res = await phonepe_gateway.check_phonepe_order_status(txn_id)
    
    if status_res.get("success"):
        # Payment successful
        payment_data = status_res.get("data", {})
        pay_mode = payment_data.get("paymentInstrument", {}).get("type", "PHONEPE_UPI")
        
        # Only credit if not already marked SUCCESS
        if payment["status"] != "SUCCESS":
            db.update_payment_status(txn_id, "SUCCESS", phonepe_response_code="PAYMENT_SUCCESS", payment_mode=pay_mode)
            db.add_user_credits(payment["user_id"], payment["leads_count"])

        return RedirectResponse(
            url=f"/?payment=success&plan={payment['plan_name']}&leads={payment['leads_count']}&amount={payment['amount_inr']}&txn={txn_id}",
            status_code=303
        )
    else:
        # Payment failed or cancelled
        fail_code = status_res.get("code", "FAILED")
        db.update_payment_status(txn_id, "FAILED", phonepe_response_code=fail_code)
        return RedirectResponse(
            url=f"/?payment=failed&plan={payment['plan_name']}&reason={fail_code}&txn={txn_id}",
            status_code=303
        )

@app.post("/api/payment/phonepe/webhook")
async def phonepe_webhook(request: Request):
    """
    Server-to-Server asynchronous webhook notification from PhonePe.
    """
    try:
        data = await request.json()
        resp_b64 = data.get("response")
        if resp_b64:
            decoded = json.loads(base64.b64decode(resp_b64).decode("utf-8"))
            txn_id = decoded.get("data", {}).get("merchantTransactionId")
            code = decoded.get("code")
            if txn_id:
                payment = db.get_payment_by_txn_id(txn_id)
                if payment and code == "PAYMENT_SUCCESS" and payment["status"] != "SUCCESS":
                    db.update_payment_status(txn_id, "SUCCESS", phonepe_response_code=code)
                    db.add_user_credits(payment["user_id"], payment["leads_count"])
    except Exception:
        pass
    return {"status": "ok"}

@app.get("/api/admin/payments")
def get_admin_payments(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Master Admin: View full history of PhonePe transactions and revenue."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required.")
    payments = db.get_all_payments(limit=100)
    return {"payments": payments, "total": len(payments)}

# Mount frontend static directory
app.mount("/", StaticFiles(directory="static", html=True), name="static")
