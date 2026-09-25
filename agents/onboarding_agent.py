"""
NexusHR - Onboarding Orchestrator Agent
Handles autonomous end-to-end employee onboarding pipelines, role-specific checklists,
AI offer letter drafting, and IT/HR integration provisioning.
"""

from datetime import datetime
from database import get_db
from agents.ai_connector import generate_llm_offer_letter, is_ai_connected

ROLE_SPECIFIC_TASKS = {
    "Engineering": {
        "Pre-Joining": [
            ("Offer letter generated & sent", 1, 1, "AI drafted · Sent via Gmail"),
            ("Background verification initiated", 1, 1, "3rd party API triggered"),
            ("Signed NDA received", 1, 0, "Completed via DocuSign"),
            ("Bank account & tax details collected", 1, 0, "Submitted via secure portal"),
        ],
        "Day 1 Setup": [
            ("Laptop provisioned & shipped (M3 Pro)", 1, 1, "IT ticket #IT-4891 auto-raised"),
            ("Email & Slack account provisioned", 1, 1, "GSuite + Slack API active"),
            ("GitHub & AWS dev credentials assigned", 0, 1, "Pending 2FA enrollment"),
            ("Orientation invite sent", 1, 1, "Calendar event auto-scheduled"),
        ],
        "First Week": [
            ("Technical mentor assigned & synced", 0, 0, "Assigned to Senior Architect"),
            ("Engineering architecture walkthrough", 0, 0, "Scheduled Day 3"),
            ("Security & compliance training completed", 0, 1, "LMS auto-enrolled"),
        ]
    },
    "Design": {
        "Pre-Joining": [
            ("Offer letter generated & sent", 1, 1, "AI drafted · Sent via Gmail"),
            ("Background verification initiated", 1, 1, "3rd party API triggered"),
            ("Signed NDA received", 0, 0, "Awaiting candidate signature"),
            ("Bank account details collected", 0, 0, "Automated reminder scheduled"),
        ],
        "Day 1 Setup": [
            ("Design workstation provisioned", 1, 1, "IT hardware dispatched"),
            ("Figma Enterprise & Adobe CC licenses assigned", 0, 1, "Scheduled for Day 1"),
            ("Slack & Google Workspace access created", 0, 1, "Pending activation"),
            ("Team welcome & orientation invite sent", 0, 1, "Auto-calendar sync"),
        ],
        "First Week": [
            ("Design buddy assigned", 0, 0, "Lead Designer paired"),
            ("Design system & component library review", 0, 0, "Not started"),
            ("First sprint design sync", 0, 0, "Not started"),
        ]
    },
    "Sales": {
        "Pre-Joining": [
            ("Offer letter generated & sent", 1, 1, "AI drafted · Sent via Gmail"),
            ("Background verification initiated", 0, 1, "Initiating verification..."),
            ("Signed NDA received", 0, 0, "Not started"),
            ("Bank account details collected", 0, 0, "Not started"),
        ],
        "Day 1 Setup": [
            ("Corporate phone & laptop shipped", 0, 1, "Logistics queued"),
            ("Salesforce / HubSpot CRM account created", 0, 1, "Auto-provisioning scheduled"),
            ("Corporate email & Slack active", 0, 1, "Pending"),
            ("Orientation invite sent", 0, 1, "Pending"),
        ],
        "First Week": [
            ("Sales quota & territory briefing", 0, 0, "Scheduled with VP Sales"),
            ("Product pitch demo walkthrough", 0, 0, "Not started"),
            ("CRM pipeline workflow training", 0, 0, "Not started"),
        ]
    },
    "Default": {
        "Pre-Joining": [
            ("Offer letter generated & sent", 1, 1, "AI drafted · Sent via Gmail"),
            ("Background verification initiated", 1, 1, "3rd party API triggered"),
            ("Signed NDA received", 0, 0, "Pending candidate submission"),
            ("Bank account details collected", 0, 0, "Pending"),
        ],
        "Day 1 Setup": [
            ("Hardware provisioned & shipped", 0, 1, "IT ticket created"),
            ("Corporate email & Slack created", 0, 1, "Identity management triggered"),
            ("Orientation invite sent", 0, 1, "Calendar event scheduled"),
        ],
        "First Week": [
            ("Onboarding buddy assigned", 0, 0, "Action required"),
            ("Team welcome lunch scheduled", 0, 0, "Action required"),
            ("Compliance & security modules completed", 0, 1, "LMS auto-enrolled"),
        ]
    }
}

def generate_onboarding_pipeline(employee_id, role, department):
    """Generate default tasks for a newly added hire based on department/role."""
    template = ROLE_SPECIFIC_TASKS.get(department, ROLE_SPECIFIC_TASKS["Default"])
    conn = get_db()
    cursor = conn.cursor()

    order = 0
    total_tasks = 0
    done_tasks = 0

    for section, tasks in template.items():
        for task_name, done, is_auto, meta in tasks:
            cursor.execute('''
                INSERT INTO onboarding_tasks (employee_id, section, name, done, is_auto, meta, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (employee_id, section, task_name, done, is_auto, meta, order))
            order += 1
            total_tasks += 1
            if done:
                done_tasks += 1

    initial_progress = int((done_tasks / total_tasks * 100)) if total_tasks > 0 else 0
    cursor.execute('UPDATE employees SET progress = ? WHERE id = ?', (initial_progress, employee_id))

    conn.commit()
    conn.close()

def get_employee_with_tasks(employee_id):
    """Retrieve full employee details and hierarchical task list."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM employees WHERE id = ?', (employee_id,))
    emp_row = cursor.fetchone()
    if not emp_row:
        conn.close()
        return None

    emp = dict(emp_row)

    cursor.execute('''
        SELECT * FROM onboarding_tasks 
        WHERE employee_id = ? 
        ORDER BY sort_order ASC
    ''', (employee_id,))
    task_rows = cursor.fetchall()

    tasks_by_section = {}
    for row in task_rows:
        t = dict(row)
        sec = t['section']
        if sec not in tasks_by_section:
            tasks_by_section[sec] = []
        tasks_by_section[sec].append({
            'id': t['id'],
            'name': t['name'],
            'done': bool(t['done']),
            'auto': bool(t['is_auto']),
            'meta': t['meta']
        })

    emp['tasks'] = tasks_by_section
    conn.close()
    return emp

def get_all_employees():
    """Retrieve all employees with their task hierarchies."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM employees ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()

    employees = []
    for row in rows:
        emp_detail = get_employee_with_tasks(row['id'])
        if emp_detail:
            employees.append(emp_detail)
    return employees

def toggle_task_status(task_id):
    """Toggle a task done status and recalculate employee overall progress."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM onboarding_tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    if not task:
        conn.close()
        return None, "Task not found"

    new_done = 0 if task['done'] else 1
    cursor.execute('UPDATE onboarding_tasks SET done = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_done, task_id))

    employee_id = task['employee_id']
    cursor.execute('SELECT COUNT(*) as total, SUM(done) as completed FROM onboarding_tasks WHERE employee_id = ?', (employee_id,))
    counts = cursor.fetchone()
    total = counts['total'] or 1
    completed = counts['completed'] or 0
    new_progress = int((completed / total) * 100)

    cursor.execute('UPDATE employees SET progress = ? WHERE id = ?', (new_progress, employee_id))
    conn.commit()
    conn.close()

    return get_employee_with_tasks(employee_id), None

def generate_ai_offer_letter(name, role, department, manager, start_date, ctc="₹22,00,000"):
    """Generate dynamic AI Offer Letter text using live LLM or polished built-in engine."""
    if is_ai_connected():
        llm_letter = generate_llm_offer_letter(name, role, department, manager, start_date, ctc)
        if llm_letter:
            return llm_letter

    today_str = datetime.now().strftime("%B %d, %Y")
    return f"""Date: {today_str}

Dear {name},

We are pleased to offer you the position of {role} in the {department} Department at NexusHR Inc., reporting directly to {manager}. Your scheduled start date is {start_date}.

Compensation & Benefits:
Your Total Cost to Company (CTC) will be {ctc} per annum, structured into base salary, performance incentive, and comprehensive health & wellness coverage.

Terms & Conditions:
1. This offer is contingent upon successful completion of background verification and verification of educational & professional credentials.
2. Standard probationary period of 3 months applies from your date of joining.
3. You will be bound by NexusHR's standard Non-Disclosure and IP Assignment Agreements.

Please review, electronically sign, and return this letter by {start_date} to confirm your acceptance.

We look forward to welcoming you to the team!

Warm regards,
Priya Ramesh
Head of People & Culture — NexusHR Inc.
"""
