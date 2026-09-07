import sqlite3
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads.db")

def clean_phone(phone: Optional[str]) -> str:
    """Normalize phone numbers for deduplication."""
    if not phone:
        return ""
    # Remove everything except digits and plus sign
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    return cleaned

class Database:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT,
                    clean_phone TEXT,
                    address TEXT,
                    city TEXT,
                    category TEXT,
                    rating REAL DEFAULT 0.0,
                    reviews_count INTEGER DEFAULT 0,
                    website TEXT,
                    instagram TEXT DEFAULT '',
                    maps_url TEXT,
                    query TEXT,
                    call_status TEXT DEFAULT 'New',
                    call_notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_phone ON leads(clean_phone)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON leads(call_status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_query ON leads(query)")
            
            # Migration: add instagram column if upgrading existing DB
            try:
                cursor.execute("ALTER TABLE leads ADD COLUMN instagram TEXT DEFAULT ''")
            except Exception:
                pass
            conn.commit()

    def insert_or_update_lead(self, lead_data: Dict[str, Any]) -> tuple[bool, int]:
        """
        Inserts a lead or skips/updates if clean_phone already exists.
        Returns (is_new: bool, lead_id: int).
        """
        phone = lead_data.get("phone", "")
        cleaned_phone = clean_phone(phone)
        name = lead_data.get("name", "Unknown").strip()

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if exists by phone if phone is available, or by name + address
            existing = None
            if cleaned_phone:
                cursor.execute("SELECT id FROM leads WHERE clean_phone = ?", (cleaned_phone,))
                existing = cursor.fetchone()
            
            if not existing and name and lead_data.get("address"):
                cursor.execute(
                    "SELECT id FROM leads WHERE LOWER(name) = LOWER(?) AND LOWER(address) = LOWER(?)",
                    (name, lead_data.get("address", "").strip())
                )
                existing = cursor.fetchone()

            if existing:
                # Update details if richer info is available
                lead_id = existing["id"]
                cursor.execute("""
                    UPDATE leads SET
                        rating = COALESCE(NULLIF(?, 0.0), rating),
                        reviews_count = COALESCE(NULLIF(?, 0), reviews_count),
                        website = COALESCE(NULLIF(?, ''), website),
                        instagram = COALESCE(NULLIF(?, ''), instagram),
                        maps_url = COALESCE(NULLIF(?, ''), maps_url),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    lead_data.get("rating", 0.0),
                    lead_data.get("reviews_count", 0),
                    lead_data.get("website", ""),
                    lead_data.get("instagram", ""),
                    lead_data.get("maps_url", ""),
                    lead_id
                ))
                conn.commit()
                return False, lead_id
            else:
                cursor.execute("""
                    INSERT INTO leads (
                        name, phone, clean_phone, address, city, category,
                        rating, reviews_count, website, instagram, maps_url, query,
                        call_status, call_notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    name,
                    phone,
                    cleaned_phone,
                    lead_data.get("address", ""),
                    lead_data.get("city", ""),
                    lead_data.get("category", "Real Estate"),
                    lead_data.get("rating", 0.0),
                    lead_data.get("reviews_count", 0),
                    lead_data.get("website", ""),
                    lead_data.get("instagram", ""),
                    lead_data.get("maps_url", ""),
                    lead_data.get("query", ""),
                    lead_data.get("call_status", "New"),
                    lead_data.get("call_notes", "")
                ))
                conn.commit()
                return True, cursor.lastrowid

    def get_leads(
        self,
        search: str = "",
        status: str = "",
        category: str = "",
        city: str = "",
        has_phone: Optional[bool] = None,
        min_rating: float = 0.0,
        sort_by: str = "id",
        order: str = "DESC",
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM leads WHERE 1=1"
            params: List[Any] = []

            if search:
                query += " AND (name LIKE ? OR phone LIKE ? OR address LIKE ? OR city LIKE ? OR call_notes LIKE ?)"
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param, search_param, search_param])

            if status:
                query += " AND call_status = ?"
                params.append(status)

            if category:
                query += " AND category LIKE ?"
                params.append(f"%{category}%")

            if city:
                query += " AND (city LIKE ? OR address LIKE ?)"
                params.extend([f"%{city}%", f"%{city}%"])

            if has_phone is True:
                query += " AND clean_phone != '' AND clean_phone IS NOT NULL"
            elif has_phone is False:
                query += " AND (clean_phone = '' OR clean_phone IS NULL)"

            if min_rating > 0.0:
                query += " AND rating >= ?"
                params.append(min_rating)

            valid_sorts = {"id", "name", "rating", "reviews_count", "call_status", "created_at", "updated_at"}
            sort_field = sort_by if sort_by in valid_sorts else "id"
            order_dir = "ASC" if order.upper() == "ASC" else "DESC"

            query += f" ORDER BY {sort_field} {order_dir} LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_lead_by_id(self, lead_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_lead(self, lead_id: int, updates: Dict[str, Any]) -> bool:
        allowed = {"name", "phone", "address", "city", "category", "website", "instagram", "call_status", "call_notes"}
        fields = [f"{k} = ?" for k in updates if k in allowed]
        if not fields:
            return False

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values = [updates[k] for k in updates if k in allowed]

        if "phone" in updates:
            fields.append("clean_phone = ?")
            values.append(clean_phone(updates["phone"]))

        values.append(lead_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE leads SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_lead(self, lead_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            conn.commit()
            return cursor.rowcount > 0

    def bulk_delete(self, lead_ids: List[int]) -> int:
        if not lead_ids:
            return 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in lead_ids)
            cursor.execute(f"DELETE FROM leads WHERE id IN ({placeholders})", lead_ids)
            conn.commit()
            return cursor.rowcount

    def clear_all_leads(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM leads")
            conn.commit()
            return cursor.rowcount

    def get_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM leads")
            total = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) as with_phone FROM leads WHERE clean_phone != '' AND clean_phone IS NOT NULL")
            with_phone = cursor.fetchone()["with_phone"]

            cursor.execute("SELECT call_status, COUNT(*) as count FROM leads GROUP BY call_status")
            status_counts = {row["call_status"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("SELECT COUNT(DISTINCT query) as total_searches FROM leads WHERE query != ''")
            total_searches = cursor.fetchone()["total_searches"]

            return {
                "total_leads": total,
                "with_phone": with_phone,
                "without_phone": total - with_phone,
                "status_counts": status_counts,
                "total_searches": total_searches
            }

    def get_unique_areas(self) -> List[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT city FROM leads WHERE city != '' AND city IS NOT NULL ORDER BY city ASC")
            cities = [row["city"] for row in cursor.fetchall()]
            return cities

db = Database()
