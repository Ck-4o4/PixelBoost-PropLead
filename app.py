import io
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Query, Header, HTTPException, UploadFile, File, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import pandas as pd

from database import db, clean_phone
from scraper import scraper_instance
from auth import (
    create_access_token,
    decode_access_token,
    verify_password,
    hash_password
)

app = FastAPI(title="PixelBoost PropLeadAi SaaS Engine", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Request & Response Models
# =============================================================================
class LoginRequest(BaseModel):
    email: str
    password: str

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
    status: Optional[str] = None # 'active' | 'suspended'
    credits_limit: Optional[int] = None
    password: Optional[str] = None
    role: Optional[str] = None

class ScrapeRequest(BaseModel):
    query: str
    city: Optional[str] = ""
    category: Optional[str] = "Real Estate"
    max_results: Optional[int] = 30

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
# Authentication Dependency
# =============================================================================
def get_current_user(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Extracts and verifies JWT token from Authorization header or ?token= query parameter.
    Returns live user record from DB.
    """
    jwt_token = None
    if authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            jwt_token = parts[1]
    elif token:
        jwt_token = token

    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(jwt_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    user = db.get_user_by_id(int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user["status"] == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Please contact PixelBoost administrator."
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
# Auth Endpoints
# =============================================================================
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
    # Strip sensitive password hashes
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
def get_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = None if current_user["role"] == "admin" else current_user["id"]
    stats = db.get_stats(user_id=user_id)
    stats["user_credits"] = {
        "limit": current_user["credits_limit"],
        "used": current_user["credits_used"],
        "remaining": max(0, current_user["credits_limit"] - current_user["credits_used"])
    }
    return stats

@app.get("/api/areas")
def get_areas(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = None if current_user["role"] == "admin" else current_user["id"]
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
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    target_user_id = current_user["id"]
    if current_user["role"] == "admin":
        target_user_id = client_id # None = all tenants

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
    return {"leads": leads, "count": len(leads)}

@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = None if current_user["role"] == "admin" else current_user["id"]
    lead = db.get_lead_by_id(lead_id, user_id=user_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@app.patch("/api/leads/{lead_id}")
def update_lead(lead_id: int, payload: LeadUpdate, current_user: Dict[str, Any] = Depends(get_current_user)):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        return {"success": True, "message": "No updates provided"}
    user_id = None if current_user["role"] == "admin" else current_user["id"]
    success = db.update_lead(lead_id, updates, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found or update failed")
    return {"success": True, "lead": db.get_lead_by_id(lead_id, user_id=user_id)}

@app.delete("/api/leads/{lead_id}")
def delete_lead(lead_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = None if current_user["role"] == "admin" else current_user["id"]
    success = db.delete_lead(lead_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True, "message": "Lead deleted"}

@app.post("/api/leads/bulk-delete")
def bulk_delete_leads(payload: BulkDeleteRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = None if current_user["role"] == "admin" else current_user["id"]
    deleted_count = db.bulk_delete(payload.ids, user_id=user_id)
    return {"success": True, "deleted_count": deleted_count}

@app.post("/api/leads/bulk-status")
def bulk_update_status(payload: BulkStatusRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = None if current_user["role"] == "admin" else current_user["id"]
    count = 0
    for lead_id in payload.ids:
        if db.update_lead(lead_id, {"call_status": payload.call_status}, user_id=user_id):
            count += 1
    return {"success": True, "updated_count": count}

# =============================================================================
# Scraping Engine SSE Stream (With Credit Enforcing)
# =============================================================================
@app.post("/api/scrape/stop")
def stop_scraping(current_user: Dict[str, Any] = Depends(get_current_user)):
    scraper_instance.cancel()
    return {"success": True, "message": "Scrape cancellation requested."}

@app.get("/api/scrape/stream")
async def stream_scrape(
    query: str = Query(..., description="Search keywords"),
    city: str = Query("", description="Target city/area"),
    category: str = Query("Real Estate", description="Business category"),
    max_results: int = Query(30, description="Max leads to fetch"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    SSE stream for live scraping progress and newly extracted leads.
    Validates tenant remaining credits and scopes leads to current user.
    """
    tenant_id = current_user["id"]

    async def event_generator():
        try:
            async for event in scraper_instance.scrape(
                query=query,
                max_results=max_results,
                city=city,
                category=category,
                user_id=tenant_id
            ):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            scraper_instance.cancel()
            yield f"data: {json.dumps({'type': 'log', 'message': 'Client disconnected / cancelled'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# =============================================================================
# Export & Import (Tenant Isolated)
# =============================================================================
@app.get("/api/export/csv")
def export_csv(
    status: str = Query(""),
    city: str = Query(""),
    has_phone: Optional[bool] = Query(None),
    search: str = Query(""),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = None if current_user["role"] == "admin" else current_user["id"]
    leads = db.get_leads(user_id=user_id, search=search, status=status, city=city, has_phone=has_phone, limit=50000)
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
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = None if current_user["role"] == "admin" else current_user["id"]
    leads = db.get_leads(user_id=user_id, search=search, status=status, city=city, has_phone=has_phone, limit=50000)
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

# Mount frontend static directory
app.mount("/", StaticFiles(directory="static", html=True), name="static")
