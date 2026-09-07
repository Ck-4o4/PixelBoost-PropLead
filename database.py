import sqlite3
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from auth import hash_password

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

            # 1. Users table (for Multi-Tenant SaaS & Master Admin)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    name TEXT NOT NULL,
                    company TEXT DEFAULT '',
                    role TEXT DEFAULT 'client',
                    status TEXT DEFAULT 'active',
                    credits_limit INTEGER DEFAULT 1000,
                    credits_used INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_role ON users(role)")

            # 2. Leads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
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
            # Migrations for existing DBs
            try:
                cursor.execute("ALTER TABLE leads ADD COLUMN instagram TEXT DEFAULT ''")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE leads ADD COLUMN user_id INTEGER DEFAULT 1")
            except Exception:
                pass

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_phone ON leads(clean_phone)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON leads(call_status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_query ON leads(query)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON leads(user_id)")

            # Seed default Master Super-Admin if not exists
            cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
            admin_user = cursor.fetchone()
            if not admin_user:
                admin_pass_hash = hash_password("Admin@PixelBoost2026!")
                cursor.execute("""
                    INSERT INTO users (email, password_hash, name, company, role, status, credits_limit, credits_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "admin@pixelboost.in",
                    admin_pass_hash,
                    "CK Admin",
                    "PixelBoost Agency",
                    "admin",
                    "active",
                    999999,
                    0
                ))
            conn.commit()

    # =========================================================================
    # User Management (Multi-Tenancy & Auth)
    # =========================================================================
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_user(
        self,
        email: str,
        password: str,
        name: str,
        company: str = "",
        role: str = "client",
        credits_limit: int = 1000
    ) -> tuple[bool, str, Optional[int]]:
        """Create a new customer or admin user. Returns (success, message, user_id)."""
        clean_email = email.strip().lower()
        if not clean_email or "@" not in clean_email:
            return False, "Invalid email address format", None
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters", None

        existing = self.get_user_by_email(clean_email)
        if existing:
            return False, f"User with email '{clean_email}' already exists", None

        p_hash = hash_password(password)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (email, password_hash, name, company, role, status, credits_limit, credits_used)
                VALUES (?, ?, ?, ?, ?, 'active', ?, 0)
            """, (clean_email, p_hash, name.strip(), company.strip(), role, credits_limit))
            conn.commit()
            return True, "User created successfully", cursor.lastrowid

    def get_all_users(self) -> List[Dict[str, Any]]:
        """List all users for Master Admin dashboard with their lead counts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    u.id, u.email, u.name, u.company, u.role, u.status,
                    u.credits_limit, u.credits_used, u.created_at, u.updated_at,
                    COUNT(l.id) as actual_leads_count
                FROM users u
                LEFT JOIN leads l ON u.id = l.user_id
                GROUP BY u.id
                ORDER BY u.created_at DESC
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_user(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user profile, status, credits quota, or password."""
        allowed = {"name", "company", "status", "credits_limit", "role"}
        fields = [f"{k} = ?" for k in updates if k in allowed]
        values = [updates[k] for k in updates if k in allowed]

        if "password" in updates and updates["password"]:
            fields.append("password_hash = ?")
            values.append(hash_password(updates["password"]))

        if not fields:
            return False

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(user_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()
            return cursor.rowcount > 0

    def increment_user_credits(self, user_id: int, count: int = 1) -> bool:
        """Increment user credits used counter."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET credits_used = credits_used + ? WHERE id = ?", (count, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_user(self, user_id: int) -> bool:
        """Delete customer and their isolated leads."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM leads WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_admin_stats(self) -> Dict[str, Any]:
        """Aggregate global stats across all clients for Master Admin."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total_users FROM users WHERE role = 'client'")
            total_clients = cursor.fetchone()["total_users"]

            cursor.execute("SELECT COUNT(*) as active_users FROM users WHERE role = 'client' AND status = 'active'")
            active_clients = cursor.fetchone()["active_users"]

            cursor.execute("SELECT COUNT(*) as total_leads FROM leads")
            total_leads = cursor.fetchone()["total_leads"]

            cursor.execute("SELECT SUM(credits_used) as total_credits_consumed FROM users")
            consumed_row = cursor.fetchone()
            total_credits_consumed = consumed_row["total_credits_consumed"] if consumed_row["total_credits_consumed"] else 0

            return {
                "total_clients": total_clients,
                "active_clients": active_clients,
                "total_leads": total_leads,
                "total_credits_consumed": total_credits_consumed
            }

    # =========================================================================
    # Multi-Tenant Leads Management
    # =========================================================================
    def insert_or_update_lead(self, lead_data: Dict[str, Any], user_id: int = 1) -> tuple[bool, int]:
        """
        Inserts a lead or skips/updates if clean_phone already exists for this tenant.
        Returns (is_new: bool, lead_id: int).
        """
        phone = lead_data.get("phone", "")
        cleaned_phone = clean_phone(phone)
        name = lead_data.get("name", "Unknown").strip()

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if exists for this tenant
            existing = None
            if cleaned_phone:
                cursor.execute("SELECT id FROM leads WHERE clean_phone = ? AND user_id = ?", (cleaned_phone, user_id))
                existing = cursor.fetchone()
            
            if not existing and name and lead_data.get("address"):
                cursor.execute(
                    "SELECT id FROM leads WHERE LOWER(name) = LOWER(?) AND LOWER(address) = LOWER(?) AND user_id = ?",
                    (name, lead_data.get("address", "").strip(), user_id)
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
                        user_id, name, phone, clean_phone, address, city, category,
                        rating, reviews_count, website, instagram, maps_url, query,
                        call_status, call_notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    user_id,
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
                # Deduct / increment user credits if authenticated user
                if user_id and user_id > 0:
                    self.increment_user_credits(user_id, 1)
                return True, cursor.lastrowid

    def get_leads(
        self,
        user_id: Optional[int] = None,
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

            if user_id is not None:
                query += " AND user_id = ?"
                params.append(user_id)

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

    def get_lead_by_id(self, lead_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if user_id is not None:
                cursor.execute("SELECT * FROM leads WHERE id = ? AND user_id = ?", (lead_id, user_id))
            else:
                cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_lead(self, lead_id: int, updates: Dict[str, Any], user_id: Optional[int] = None) -> bool:
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
        where_clause = "WHERE id = ?"
        if user_id is not None:
            where_clause += " AND user_id = ?"
            values.append(user_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE leads SET {', '.join(fields)} {where_clause}", values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_lead(self, lead_id: int, user_id: Optional[int] = None) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if user_id is not None:
                cursor.execute("DELETE FROM leads WHERE id = ? AND user_id = ?", (lead_id, user_id))
            else:
                cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            conn.commit()
            return cursor.rowcount > 0

    def bulk_delete(self, lead_ids: List[int], user_id: Optional[int] = None) -> int:
        if not lead_ids:
            return 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in lead_ids)
            if user_id is not None:
                cursor.execute(f"DELETE FROM leads WHERE id IN ({placeholders}) AND user_id = ?", lead_ids + [user_id])
            else:
                cursor.execute(f"DELETE FROM leads WHERE id IN ({placeholders})", lead_ids)
            conn.commit()
            return cursor.rowcount

    def clear_all_leads(self, user_id: Optional[int] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if user_id is not None:
                cursor.execute("DELETE FROM leads WHERE user_id = ?", (user_id,))
            else:
                cursor.execute("DELETE FROM leads")
            conn.commit()
            return cursor.rowcount

    def get_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            where_clause = ""
            params = []
            if user_id is not None:
                where_clause = "WHERE user_id = ?"
                params = [user_id]

            cursor.execute(f"SELECT COUNT(*) as total FROM leads {where_clause}", params)
            total = cursor.fetchone()["total"]

            phone_where = "WHERE clean_phone != '' AND clean_phone IS NOT NULL"
            if user_id is not None:
                phone_where += " AND user_id = ?"
            cursor.execute(f"SELECT COUNT(*) as with_phone FROM leads {phone_where}", params)
            with_phone = cursor.fetchone()["with_phone"]

            status_where = ""
            if user_id is not None:
                status_where = "WHERE user_id = ?"
            cursor.execute(f"SELECT call_status, COUNT(*) as count FROM leads {status_where} GROUP BY call_status", params)
            status_counts = {row["call_status"]: row["count"] for row in cursor.fetchall()}

            search_where = "WHERE query != ''"
            if user_id is not None:
                search_where += " AND user_id = ?"
            cursor.execute(f"SELECT COUNT(DISTINCT query) as total_searches FROM leads {search_where}", params)
            total_searches = cursor.fetchone()["total_searches"]

            return {
                "total_leads": total,
                "with_phone": with_phone,
                "without_phone": total - with_phone,
                "status_counts": status_counts,
                "total_searches": total_searches
            }

    def get_unique_areas(self, user_id: Optional[int] = None) -> List[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            where_clause = "WHERE city != '' AND city IS NOT NULL"
            params = []
            if user_id is not None:
                where_clause += " AND user_id = ?"
                params = [user_id]
            cursor.execute(f"SELECT DISTINCT city FROM leads {where_clause} ORDER BY city ASC", params)
            cities = [row["city"] for row in cursor.fetchall()]
            return cities

db = Database()
