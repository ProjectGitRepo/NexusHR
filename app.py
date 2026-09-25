"""
NexusHR - Enterprise Autonomous HR Agent Platform
Flask Application Backend & REST API Server
Built for BITSoM Vertex Builders' Pitch Fest 2026
"""

import os
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

from database import init_db, get_db
from agents.onboarding_agent import (
    get_all_employees,
    get_employee_with_tasks,
    generate_onboarding_pipeline,
    toggle_task_status,
    generate_ai_offer_letter
)
from agents.policy_agent import (
    search_policy_knowledge,
    get_policy_stats,
    get_all_policy_docs,
    seed_policy_documents
)
from agents.attrition_agent import (
    get_risk_heatmap,
    get_attrition_metrics,
    record_retention_action,
    trigger_batch_nudges,
    seed_attrition_risks
)
from agents.ai_connector import get_active_ai_provider

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Ensure database is initialized on startup
with app.app_context():
    init_db()
    seed_policy_documents()
    seed_attrition_risks()

# ── FRONTEND ROUTE ──
@app.route('/')
def index():
    """Serve the NexusHR dashboard application."""
    return render_template('index.html')

# ── SYSTEM & DASHBOARD OVERVIEW ──
@app.route('/api/status', methods=['GET'])
def get_system_status():
    """Get active agent and platform telemetry."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as active_hires FROM employees WHERE progress < 100')
    active_hires = cursor.fetchone()['active_hires'] or 0
    cursor.execute("SELECT COUNT(*) as critical_risks FROM attrition_risks WHERE risk_level = 'Critical'")
    critical_risks = cursor.fetchone()['critical_risks'] or 0
    conn.close()

    ai_provider, ai_model, is_live_ai = get_active_ai_provider()

    return jsonify({
        "status": "online",
        "platform": "NexusHR Autonomous HR Platform",
        "incubator": "BITSoM Vertex 2026",
        "active_onboarding_workflows": active_hires,
        "critical_retention_alerts": critical_risks,
        "agents": {
            "onboarding": "Active",
            "policy_copilot": "Active",
            "attrition_guard": "Active"
        },
        "ai_engine": {
            "provider": ai_provider,
            "model": ai_model,
            "is_live": is_live_ai,
            "mode": "Live LLM Cloud / Local" if is_live_ai else "Built-in Autonomous (Offline Zero-Key)"
        }
    })

# ── 1. ONBOARDING AGENT ENDPOINTS ──
@app.route('/api/hires', methods=['GET'])
def list_hires():
    """List all new hires and their onboarding tasks."""
    hires = get_all_employees()
    return jsonify({"success": True, "hires": hires})

@app.route('/api/hires', methods=['POST'])
def add_hire():
    """Create a new employee and autonomously generate role-specific onboarding tasks."""
    data = request.get_json() or {}
    name = data.get('name', 'New Team Member').strip()
    role = data.get('role', 'Software Engineer').strip()
    dept = data.get('department', 'Engineering').strip()
    start_date = data.get('start_date', 'Dec 01, 2025').strip()
    email = data.get('email', f"{name.lower().replace(' ', '.')}@bitsom.io").strip()
    manager = data.get('manager', 'Priya Ramesh (HR)').strip()
    ctc = data.get('ctc', '₹22,00,000')

    colors = ["#6366F1", "#10B981", "#F59E0B", "#38BDF8", "#8B5CF6", "#EC4899"]
    import random
    color = random.choice(colors)
    initial = name[0].upper() if name else 'N'

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM employees WHERE email = ?', (email,))
    existing = cursor.fetchone()
    if existing:
        employee_id = existing['id']
        cursor.execute('''
            UPDATE employees 
            SET name = ?, role = ?, department = ?, start_date = ?, manager = ?, ctc = ?
            WHERE id = ?
        ''', (name, role, dept, start_date, manager, ctc, employee_id))
        cursor.execute('DELETE FROM onboarding_tasks WHERE employee_id = ?', (employee_id,))
        conn.commit()
    else:
        cursor.execute('''
            INSERT INTO employees (name, role, department, start_date, email, manager, progress, color, initial, ctc)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
        ''', (name, role, dept, start_date, email, manager, color, initial, ctc))
        employee_id = cursor.lastrowid
        conn.commit()
    conn.close()

    # Generate specialized onboarding pipeline
    generate_onboarding_pipeline(employee_id, role, dept)
    new_employee = get_employee_with_tasks(employee_id)

    return jsonify({
        "success": True,
        "message": f"Autonomous onboarding pipeline activated for {name}",
        "hire": new_employee
    }), 201

@app.route('/api/hires/<int:employee_id>/tasks/<int:task_id>/toggle', methods=['POST'])
def toggle_task(employee_id, task_id):
    """Toggle a task status and update overall hire progress."""
    updated_emp, err = toggle_task_status(task_id)
    if err:
        return jsonify({"success": False, "error": err}), 404
    return jsonify({"success": True, "hire": updated_emp})

@app.route('/api/hires/<int:employee_id>/offer-letter', methods=['GET'])
def get_offer_letter(employee_id):
    """Get generated AI offer letter text for an employee."""
    emp = get_employee_with_tasks(employee_id)
    if not emp:
        return jsonify({"success": False, "error": "Employee not found"}), 404

    letter_text = generate_ai_offer_letter(
        name=emp['name'],
        role=emp['role'],
        department=emp['department'],
        manager=emp['manager'],
        start_date=emp['start_date'],
        ctc=emp.get('ctc', '₹22,00,000')
    )
    return jsonify({"success": True, "offer_letter": letter_text, "employee": emp})

@app.route('/api/hires/<int:employee_id>/offer-letter/resend', methods=['POST'])
def resend_offer_letter(employee_id):
    """Simulate automated re-dispatch of AI offer letter via Gmail."""
    emp = get_employee_with_tasks(employee_id)
    if not emp:
        return jsonify({"success": False, "error": "Employee not found"}), 404
    return jsonify({
        "success": True,
        "message": f"AI Offer letter successfully resent to {emp['email']} via Gmail integration."
    })

# ── 2. POLICY COPILOT AGENT ENDPOINTS ──
@app.route('/api/policy/ask', methods=['POST'])
def ask_policy():
    """Send question to Policy Copilot and receive authoritative RAG response with citations."""
    data = request.get_json() or {}
    query = data.get('query', '').strip()
    if not query:
        return jsonify({"success": False, "error": "Query cannot be empty"}), 400

    result = search_policy_knowledge(query)
    stats = get_policy_stats()

    return jsonify({
        "success": True,
        "query": query,
        "answer": result['answer'],
        "sources": result['sources'],
        "confidence": result['confidence'],
        "response_time_ms": result['response_time_ms'],
        "stats": stats
    })

@app.route('/api/policy/docs', methods=['GET'])
def list_policy_docs():
    """List all indexed policy documents in the knowledge base."""
    docs = get_all_policy_docs()
    stats = get_policy_stats()
    return jsonify({"success": True, "documents": docs, "stats": stats})

@app.route('/api/policy/stats', methods=['GET'])
def policy_stats():
    """Return live Policy Copilot analytics."""
    stats = get_policy_stats()
    return jsonify({"success": True, "stats": stats})

# ── 3. ATTRITION GUARD AGENT ENDPOINTS ──
@app.route('/api/attrition/heatmap', methods=['GET'])
def get_attrition_heatmap():
    """Retrieve employee flight-risk heatmap and signal analysis."""
    records = get_risk_heatmap()
    metrics = get_attrition_metrics()
    return jsonify({"success": True, "heatmap": records, "metrics": metrics})

@app.route('/api/attrition/metrics', methods=['GET'])
def get_attrition_metrics_endpoint():
    """Retrieve aggregate workforce churn prediction metrics."""
    metrics = get_attrition_metrics()
    return jsonify({"success": True, "metrics": metrics})

@app.route('/api/attrition/action', methods=['POST'])
def take_retention_action():
    """Trigger a retention intervention for an employee."""
    data = request.get_json() or {}
    risk_id = data.get('risk_id')
    action_type = data.get('action_type', 'Nudge Manager')
    note = data.get('note', 'Retention action initiated via dashboard')
    triggered_by = data.get('triggered_by', 'Priya Ramesh (HR)')

    if not risk_id:
        return jsonify({"success": False, "error": "risk_id is required"}), 400

    success, msg = record_retention_action(risk_id, action_type, note, triggered_by)
    if not success:
        return jsonify({"success": False, "error": msg}), 404

    heatmap = get_risk_heatmap()
    metrics = get_attrition_metrics()

    return jsonify({
        "success": True,
        "message": msg,
        "heatmap": heatmap,
        "metrics": metrics
    })

@app.route('/api/attrition/nudge', methods=['POST'])
def send_batch_nudges():
    """Dispatch automated manager nudges for all critical/high risk employees."""
    count = trigger_batch_nudges()
    heatmap = get_risk_heatmap()
    metrics = get_attrition_metrics()
    return jsonify({
        "success": True,
        "message": f"Retention briefs dispatched to reporting managers for {count} at-risk employees.",
        "nudged_count": count,
        "heatmap": heatmap,
        "metrics": metrics
    })

# ── 4. PLATFORM CONFIGURATION & INTEGRATIONS ──
@app.route('/api/config', methods=['GET'])
def get_config():
    """Get all platform toggles, integrations, and company profile."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT key, value FROM platform_config')
    configs = {row['key']: row['value'] for row in cursor.fetchall()}

    cursor.execute('SELECT * FROM integrations')
    integrations = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify({"success": True, "config": configs, "integrations": integrations})

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update platform settings or AI model choice."""
    data = request.get_json() or {}
    conn = get_db()
    cursor = conn.cursor()
    for k, v in data.items():
        cursor.execute('INSERT OR REPLACE INTO platform_config (key, value) VALUES (?, ?)', (k, str(v)))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Settings updated successfully."})

@app.route('/api/integrations/<int_id>/toggle', methods=['POST'])
def toggle_integration(int_id):
    """Connect or disconnect an external enterprise tool integration."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM integrations WHERE id = ?', (int_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"success": False, "error": "Integration not found"}), 404

    new_status = 'off' if row['status'] == 'connected' else 'connected'
    cursor.execute('UPDATE integrations SET status = ?, last_sync = CURRENT_TIMESTAMP WHERE id = ?', (new_status, int_id))
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "id": int_id,
        "status": new_status,
        "message": f"Integration {int_id.upper()} status updated to {new_status}."
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"==================================================")
    print(f"NexusHR Autonomous HR Platform Backend Online")
    print(f"Pitch Fest: BITSoM Vertex Builders' Pitch Fest 2026")
    print(f"Server running at: http://127.0.0.1:{port}")
    print(f"==================================================")
    app.run(host='0.0.0.0', port=port, debug=True)
