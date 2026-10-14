"""Add missing file_hash column to documents table.

Run: python scripts/add_file_hash_column.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from src.db.database import engine

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_hash VARCHAR"))
    conn.commit()
    print("Done: file_hash column added (or already exists)")
