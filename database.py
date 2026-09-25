"""
NexusHR - Enterprise Autonomous HR Agent Platform
Database module for SQLite storage and persistence.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nexushr.db')

def get_db():
    """Get a database connection with dict-like row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables and indexes."""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Employees / New Hires Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT NOT NULL,
        start_date TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        manager TEXT NOT NULL,
        progress INTEGER DEFAULT 0,
        color TEXT DEFAULT '#6366F1',
        initial TEXT,
        ctc TEXT DEFAULT '₹18,50,000',
        status TEXT DEFAULT 'Onboarding',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 2. Onboarding Tasks Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS onboarding_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        section TEXT NOT NULL,
        name TEXT NOT NULL,
        done INTEGER DEFAULT 0,
        is_auto INTEGER DEFAULT 0,
        meta TEXT,
        sort_order INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
    )
    ''')

    # 3. Policy Documents Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS policy_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        doc_code TEXT NOT NULL,
        category TEXT NOT NULL,
        pages INTEGER DEFAULT 1,
        summary TEXT,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 4. Policy Q&A Logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS policy_query_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        answer TEXT NOT NULL,
        sources_json TEXT,
        confidence REAL DEFAULT 0.95,
        response_time_ms INTEGER DEFAULT 120,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 5. Attrition Risk Records
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attrition_risks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_name TEXT NOT NULL,
        department TEXT NOT NULL,
        tenure_years REAL NOT NULL,
        risk_score INTEGER NOT NULL,
        risk_level TEXT NOT NULL,
        top_signal TEXT NOT NULL,
        recommended_action TEXT NOT NULL,
        action_status TEXT DEFAULT 'Pending',
        last_action_note TEXT,
        estimated_replacement_cost INTEGER DEFAULT 450000,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 6. Retention Actions History
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS retention_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        risk_id INTEGER,
        employee_name TEXT NOT NULL,
        action_type TEXT NOT NULL,
        details TEXT,
        triggered_by TEXT DEFAULT 'HR Admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 7. Integrations Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS integrations (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        status TEXT NOT NULL,
        last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 8. Platform Config Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS platform_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully at:", DB_PATH)
