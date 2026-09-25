"""
NexusHR - Test Suite for Backend & Agents
Verifies SQLite persistence, Onboarding agent, Policy RAG agent, and Attrition agent.
"""

import unittest
import json
from app import app
from database import init_db
from seed_data import seed_all

class TestNexusHRBackend(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        seed_all()

    def test_status_endpoint(self):
        res = self.app.get('/api/status')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'online')
        self.assertIn('NexusHR', data['platform'])

    def test_hires_list(self):
        res = self.app.get('/api/hires')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['hires']), 1)

    def test_create_hire_and_toggle(self):
        new_hire_payload = {
            "name": "Pooja Hegde",
            "role": "Frontend Architect",
            "department": "Engineering",
            "start_date": "Jan 10, 2026",
            "email": "pooja.hegde@bitsom.io",
            "manager": "Rohit Kumar"
        }
        res = self.app.post('/api/hires', json=new_hire_payload)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        emp_id = data['hire']['id']

        # Check tasks created
        tasks = data['hire']['tasks']
        self.assertIn('Pre-Joining', tasks)
        task_id = tasks['Pre-Joining'][0]['id']

        # Toggle task
        toggle_res = self.app.post(f'/api/hires/{emp_id}/tasks/{task_id}/toggle')
        self.assertEqual(toggle_res.status_code, 200)
        toggle_data = json.loads(toggle_res.data)
        self.assertTrue(toggle_data['success'])

    def test_policy_copilot_rag(self):
        query_payload = {"query": "How many casual leaves per year?"}
        res = self.app.post('/api/policy/ask', json=query_payload)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn('12 Casual Leaves', data['answer'])
        self.assertGreaterEqual(len(data['sources']), 1)

    def test_attrition_guard(self):
        res = self.app.get('/api/attrition/heatmap')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['heatmap']), 1)

        # Trigger batch nudge
        nudge_res = self.app.post('/api/attrition/nudge')
        self.assertEqual(nudge_res.status_code, 200)
        nudge_data = json.loads(nudge_res.data)
        self.assertTrue(nudge_data['success'])

if __name__ == '__main__':
    unittest.main()
