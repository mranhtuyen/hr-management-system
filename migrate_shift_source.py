"""
Migration: Them cot shift_source va draft_status vao bang schedule_shifts
"""
import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'hr_system.db')

    if not os.path.exists(db_path):
        print(f"Database khong ton tai: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Kiem tra va them cot shift_source
    cursor.execute("PRAGMA table_info(schedule_shifts)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'shift_source' not in columns:
        print("Them cot shift_source...")
        cursor.execute("ALTER TABLE schedule_shifts ADD COLUMN shift_source VARCHAR(20) DEFAULT 'employee'")
        print("  -> Da them shift_source")
    else:
        print("Cot shift_source da ton tai")

    if 'draft_status' not in columns:
        print("Them cot draft_status...")
        cursor.execute("ALTER TABLE schedule_shifts ADD COLUMN draft_status VARCHAR(20) DEFAULT 'final'")
        print("  -> Da them draft_status")
    else:
        print("Cot draft_status da ton tai")

    conn.commit()
    conn.close()
    print("Migration hoan thanh!")

if __name__ == '__main__':
    migrate()
