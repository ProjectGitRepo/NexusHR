"""
NexusHR - Database Seeder Script
Pre-populates SQLite with initial enterprise data for BITSoM Vertex Pitch Fest 2026.
"""

from database import get_db, init_db
from agents.onboarding_agent import ROLE_SPECIFIC_TASKS
from agents.policy_agent import seed_policy_documents
from agents.attrition_agent import seed_attrition_risks

SAMPLE_HIRES = [
    {
        "name": "Aditya Sharma",
        "role": "Backend Engineer",
        "department": "Engineering",
        "start_date": "Nov 18, 2025",
        "email": "aditya@bitsom.io",
        "manager": "Rohit Kumar",
        "color": "#6366F1",
        "initial": "A",
        "ctc": "₹24,00,000",
        "tasks": {
            "Pre-Joining": [
                ("Offer letter generated & sent", 1, 1, "AI drafted · Sent via Gmail"),
                ("Background verification initiated", 1, 1, "3rd party API triggered"),
                ("Signed NDA received", 1, 0, "Completed Nov 14"),
                ("Bank account details collected", 1, 0, "Submitted via secure portal"),
            ],
            "Day 1 Setup": [
                ("Laptop provisioned & shipped", 1, 1, "IT ticket auto-raised"),
                ("Email & Slack account created", 1, 1, "GSuite + Slack API"),
                ("Jira & GitHub access granted", 0, 1, "Pending IT confirmation"),
                ("Orientation invite sent", 1, 1, "Calendar event created"),
            ],
            "First Week": [
                ("Buddy assigned & introduced", 0, 0, "Action required"),
                ("Team lunch scheduled", 0, 0, "Action required"),
                ("Training modules assigned", 0, 1, "LMS auto-enrolled"),
            ]
        }
    },
    {
        "name": "Meghna Iyer",
        "role": "Product Designer",
        "department": "Design",
        "start_date": "Nov 20, 2025",
        "email": "meghna@bitsom.io",
        "manager": "Ananya Singh",
        "color": "#10B981",
        "initial": "M",
        "ctc": "₹21,50,000",
        "tasks": {
            "Pre-Joining": [
                ("Offer letter generated & sent", 1, 1, "AI drafted · Sent via Gmail"),
                ("Background verification initiated", 1, 1, "3rd party API triggered"),
                ("Signed NDA received", 0, 0, "Awaiting candidate response"),
                ("Bank account details collected", 0, 0, "Reminder scheduled"),
            ],
            "Day 1 Setup": [
                ("Laptop provisioned & shipped", 1, 1, "IT ticket auto-raised"),
                ("Email & Slack account created", 0, 1, "Scheduled for Nov 19"),
                ("Figma & Notion access granted", 0, 1, "Pending"),
                ("Orientation invite sent", 0, 1, "Will trigger Nov 19"),
            ],
            "First Week": [
                ("Buddy assigned & introduced", 0, 0, "Not started"),
                ("Portfolio review session set", 0, 0, "Not started"),
                ("Design system walk-through", 0, 0, "Not started"),
            ]
        }
    },
    {
        "name": "Rahul Krishnan",
        "role": "Sales Executive",
        "department": "Sales",
        "start_date": "Dec 01, 2025",
        "email": "rahul@bitsom.io",
        "manager": "Vijay Nair",
        "color": "#F59E0B",
        "initial": "R",
        "ctc": "₹16,00,000",
        "tasks": {
            "Pre-Joining": [
                ("Offer letter generated & sent", 1, 1, "AI drafted · Sent via Gmail"),
                ("Background verification initiated", 0, 1, "Initiating verification..."),
                ("Signed NDA received", 0, 0, "Not started"),
                ("Bank account details collected", 0, 0, "Not started"),
            ],
            "Day 1 Setup": [
                ("Laptop provisioned & shipped", 0, 1, "Will trigger Nov 28"),
                ("Email & CRM account created", 0, 1, "Scheduled for Nov 30"),
                ("Orientation invite sent", 0, 1, "Pending"),
                ("Sales onboarding deck shared", 0, 1, "Not started"),
            ],
            "First Week": [
                ("Buddy assigned & introduced", 0, 0, "Not started"),
                ("Product demo walkthrough", 0, 0, "Not started"),
                ("CRM training scheduled", 0, 0, "Not started"),
            ]
        }
    }
]

SAMPLE_INTEGRATIONS = [
    ("gmail", "Gmail", "Communication", "connected"),
    ("slack", "Slack", "Collaboration", "connected"),
    ("gcal", "Google Calendar", "Scheduling", "connected"),
    ("jira", "Jira", "Ticketing", "pending"),
    ("bamboohr", "BambooHR", "HRIS", "off"),
    ("razorpay", "Razorpay Payroll", "Payroll", "off")
]

SAMPLE_CONFIG = {
    "auto_send_offer": "1",
    "slack_notifications": "1",
    "weekly_attrition_report": "1",
    "auto_assign_buddy": "0",
    "compliance_alerts": "1",
    "ai_model": "Claude Sonnet 4.6 (default)",
    "language": "English",
    "company_name": "BitSom Inc.",
    "total_employees": "147",
    "hr_admin": "Priya R."
}

def seed_all():
    """Run all seed operations."""
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # 1. Seed Employees & Tasks
    for hire in SAMPLE_HIRES:
        cursor.execute('SELECT id FROM employees WHERE email = ?', (hire['email'],))
        row = cursor.fetchone()
        if not row:
            total_tasks = sum(len(t) for t in hire['tasks'].values())
            done_tasks = sum(sum(1 for task in t if task[1] == 1) for t in hire['tasks'].values())
            progress = int((done_tasks / total_tasks * 100)) if total_tasks > 0 else 0

            cursor.execute('''
                INSERT INTO employees (name, role, department, start_date, email, manager, progress, color, initial, ctc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                hire['name'], hire['role'], hire['department'], hire['start_date'],
                hire['email'], hire['manager'], progress, hire['color'], hire['initial'], hire['ctc']
            ))
            emp_id = cursor.lastrowid

            order = 0
            for section, tasks in hire['tasks'].items():
                for name, done, is_auto, meta in tasks:
                    cursor.execute('''
                        INSERT INTO onboarding_tasks (employee_id, section, name, done, is_auto, meta, sort_order)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (emp_id, section, name, done, is_auto, meta, order))
                    order += 1

    # 2. Seed Integrations
    for int_id, name, cat, status in SAMPLE_INTEGRATIONS:
        cursor.execute('SELECT id FROM integrations WHERE id = ?', (int_id,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO integrations (id, name, category, status)
                VALUES (?, ?, ?, ?)
            ''', (int_id, name, cat, status))

    # 3. Seed Config
    for k, v in SAMPLE_CONFIG.items():
        cursor.execute('INSERT OR REPLACE INTO platform_config (key, value) VALUES (?, ?)', (k, v))

    conn.commit()
    conn.close()

    # 4. Seed Policy Docs & Attrition Risks
    seed_policy_documents()
    seed_attrition_risks()

    print("All sample data seeded successfully into SQLite database!")

if __name__ == '__main__':
    seed_all()
