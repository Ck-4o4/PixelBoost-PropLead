import os
import tempfile
from fastapi.testclient import TestClient
from database import Database, db, clean_phone
from app import app

client = TestClient(app)

def test_clean_phone():
    assert clean_phone("+1 (305) 555-0199") == "+13055550199"
    assert clean_phone("022-2640-1234") == "02226401234"
    assert clean_phone(None) == ""

def test_database_crud_and_deduplication():
    # Use temporary DB
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db_path = tmp.name

    try:
        test_db = Database(db_path=temp_db_path)
        
        # Insert first lead
        lead1 = {
            "name": "Apex Prime Real Estate",
            "phone": "+1 305 555 1234",
            "address": "100 Brickell Ave, Miami, FL",
            "city": "Miami",
            "category": "Real Estate",
            "rating": 4.8,
            "reviews_count": 42,
            "website": "https://apexprime.example.com",
            "maps_url": "https://maps.google.com/?q=apex",
            "query": "Real estate agents in Miami"
        }
        is_new, lead_id1 = test_db.insert_or_update_lead(lead1)
        assert is_new is True
        assert lead_id1 > 0

        # Duplicate phone check
        is_new2, lead_id2 = test_db.insert_or_update_lead({
            "name": "Apex Prime Properties",
            "phone": "+1 (305) 555-1234", # Same phone formatted differently
            "address": "100 Brickell Ave, Miami",
            "rating": 4.9
        })
        assert is_new2 is False
        assert lead_id2 == lead_id1

        # Fetch leads
        leads = test_db.get_leads(search="Apex")
        assert len(leads) == 1
        assert leads[0]["name"] == "Apex Prime Real Estate"
        assert leads[0]["rating"] == 4.9 # updated rating

        # Update call status and notes
        test_db.update_lead(lead_id1, {"call_status": "Interested", "call_notes": "Client requested portfolio"})
        updated = test_db.get_lead_by_id(lead_id1)
        assert updated["call_status"] == "Interested"
        assert updated["call_notes"] == "Client requested portfolio"

        # Stats
        stats = test_db.get_stats()
        assert stats["total_leads"] == 1
        assert stats["with_phone"] == 1
        assert stats["status_counts"]["Interested"] == 1

        # Delete
        assert test_db.delete_lead(lead_id1) is True
        assert test_db.get_lead_by_id(lead_id1) is None

    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)

def test_api_endpoints():
    # Test stats
    res = client.get("/api/stats")
    assert res.status_code == 200
    assert "total_leads" in res.json()

    # Test leads listing
    res = client.get("/api/leads")
    assert res.status_code == 200
    assert "leads" in res.json()

    # Test export CSV
    res = client.get("/api/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]

    # Test export Excel
    res = client.get("/api/export/excel")
    assert res.status_code == 200
    assert "openxmlformats-officedocument" in res.headers["content-type"]

def test_auth_and_phonepe_flow():
    # 1. Register a new user
    import time
    test_email = f"leaduser_{int(time.time())}@example.com"
    res = client.post("/api/auth/register", json={
        "name": "Test Real Estate Agent",
        "company": "Skyline Realty",
        "email": test_email,
        "password": "Password123!"
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert "access_token" in data
    token = data["access_token"]
    user = data["user"]
    assert user["email"] == test_email
    initial_credits = user["credits_limit"]

    # 2. Test PhonePe payment initiate validation
    headers = {"Authorization": f"Bearer {token}"}
    res_init = client.post("/api/payment/phonepe/initiate", json={
        "plan_name": "Starter",
        "leads_count": 10,
        "amount_inr": 79.0
    }, headers=headers)
    # Status code will either be 200 (if PhonePe responds) or 502 (if offline PhonePe mock)
    assert res_init.status_code in [200, 502]

    # 3. Test Database credit top-up directly
    assert db.add_user_credits(user["id"], 50) is True
    updated_user = db.get_user_by_id(user["id"])
    assert updated_user["credits_limit"] == initial_credits + 50

if __name__ == "__main__":
    test_clean_phone()
    test_database_crud_and_deduplication()
    test_api_endpoints()
    test_auth_and_phonepe_flow()
    print("All tests passed successfully!")
