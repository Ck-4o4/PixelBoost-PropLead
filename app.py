import io
import json
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Query, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

from database import db, clean_phone
from scraper import scraper_instance

app = FastAPI(title="Real Estate Lead Scraper & Calling CRM", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
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

# Endpoints
@app.get("/api/stats")
def get_stats():
    return db.get_stats()

@app.get("/api/areas")
def get_areas():
    return {"areas": db.get_unique_areas()}

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
    offset: int = Query(0, description="Offset for pagination")
):
    leads = db.get_leads(
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
def get_lead(lead_id: int):
    lead = db.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@app.patch("/api/leads/{lead_id}")
def update_lead(lead_id: int, payload: LeadUpdate):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        return {"success": True, "message": "No updates provided"}
    success = db.update_lead(lead_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found or update failed")
    return {"success": True, "lead": db.get_lead_by_id(lead_id)}

@app.delete("/api/leads/{lead_id}")
def delete_lead(lead_id: int):
    success = db.delete_lead(lead_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True, "message": "Lead deleted"}

@app.post("/api/leads/bulk-delete")
def bulk_delete_leads(payload: BulkDeleteRequest):
    deleted_count = db.bulk_delete(payload.ids)
    return {"success": True, "deleted_count": deleted_count}

@app.post("/api/leads/bulk-status")
def bulk_update_status(payload: BulkStatusRequest):
    count = 0
    for lead_id in payload.ids:
        if db.update_lead(lead_id, {"call_status": payload.call_status}):
            count += 1
    return {"success": True, "updated_count": count}

@app.post("/api/scrape/stop")
def stop_scraping():
    scraper_instance.cancel()
    return {"success": True, "message": "Scrape cancellation requested."}

@app.get("/api/scrape/stream")
async def stream_scrape(
    query: str = Query(..., description="Search keywords"),
    city: str = Query("", description="Target city/area"),
    category: str = Query("Real Estate", description="Business category"),
    max_results: int = Query(30, description="Max leads to fetch")
):
    """
    SSE stream for live scraping progress and newly extracted leads.
    """
    async def event_generator():
        try:
            async for event in scraper_instance.scrape(
                query=query,
                max_results=max_results,
                city=city,
                category=category
            ):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            scraper_instance.cancel()
            yield f"data: {json.dumps({'type': 'log', 'message': 'Client disconnected / cancelled'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/export/csv")
def export_csv(
    status: str = Query(""),
    city: str = Query(""),
    has_phone: Optional[bool] = Query(None),
    search: str = Query("")
):
    leads = db.get_leads(search=search, status=status, city=city, has_phone=has_phone, limit=50000)
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
    
    filename = f"real_estate_calling_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
    search: str = Query("")
):
    leads = db.get_leads(search=search, status=status, city=city, has_phone=has_phone, limit=50000)
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
        df.to_excel(writer, index=False, sheet_name="Real Estate Calling List")
    stream.seek(0)

    filename = f"real_estate_calling_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/api/import/csv")
async def import_csv(file: UploadFile = File(...)):
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
        is_new, _ = db.insert_or_update_lead(lead_data)
        imported_count += 1
        if is_new:
            new_count += 1

    return {"success": True, "total_processed": imported_count, "new_leads_added": new_count}

# Mount frontend static directory
app.mount("/", StaticFiles(directory="static", html=True), name="static")
