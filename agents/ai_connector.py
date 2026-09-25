"""
NexusHR - Universal AI & LLM Add-on Connector
Enables plug-and-play connectivity to external Large Language Models:
- OpenAI (GPT-4o, GPT-4o-mini, GPT-3.5) / OpenAI-compatible APIs (Groq, DeepSeek, Together, OpenRouter)
- Google Gemini (Gemini 1.5 Flash, Gemini 1.5 Pro)
- Local LLMs (Ollama, LM Studio, vLLM)

Zero external dependencies required (uses standard library urllib & json).
Graceful Fallback: If no API key is provided, the platform seamlessly uses
the built-in offline heuristic & semantic agent engine without errors.
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path

# Auto-load .env file if present in workspace root without requiring python-dotenv
def _load_env_file():
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

_load_env_file()

def get_active_ai_provider():
    """
    Detect configured AI provider.
    Returns: (provider_name, model_name, is_live)
    """
    if os.getenv("OPENAI_API_KEY"):
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return "OpenAI", model, True
    elif os.getenv("GEMINI_API_KEY"):
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        return "Google Gemini", model, True
    elif os.getenv("OLLAMA_BASE_URL"):
        model = os.getenv("OLLAMA_MODEL", "llama3")
        return "Local Ollama", model, True
    else:
        return "Built-in Autonomous Engine (Zero-Key)", "Deterministic Heuristic/RAG", False

def is_ai_connected():
    """Check if any external live LLM provider is active."""
    _, _, is_live = get_active_ai_provider()
    return is_live

def _call_openai(prompt, system_instruction="You are NexusHR Enterprise AI Agent."):
    """Call OpenAI or OpenAI-compatible endpoint using urllib."""
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip('/')
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 800
    }

    data = json.dumps(payload).encode('utf-8')
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            return res_json['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"[AI Connector] OpenAI request failed: {e}")
        return None

def _call_gemini(prompt, system_instruction="You are NexusHR Enterprise AI Agent."):
    """Call Google Gemini REST API using urllib."""
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    combined_prompt = f"{system_instruction}\n\nUser Query:\n{prompt}"
    payload = {
        "contents": [{
            "parts": [{"text": combined_prompt}]
        }]
    }

    data = json.dumps(payload).encode('utf-8')
    headers = {"Content-Type": "application/json"}

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            candidates = res_json.get('candidates', [])
            if candidates and 'content' in candidates[0]:
                parts = candidates[0]['content'].get('parts', [])
                if parts:
                    return parts[0].get('text', '').strip()
            return None
    except Exception as e:
        print(f"[AI Connector] Gemini request failed: {e}")
        return None

def _call_ollama(prompt, system_instruction="You are NexusHR Enterprise AI Agent."):
    """Call local Ollama endpoint."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip('/')
    model = os.getenv("OLLAMA_MODEL", "llama3")
    url = f"{base_url}/api/generate"

    payload = {
        "model": model,
        "prompt": f"{system_instruction}\n\n{prompt}",
        "stream": False
    }

    data = json.dumps(payload).encode('utf-8')
    headers = {"Content-Type": "application/json"}

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            return res_json.get('response', '').strip()
    except Exception as e:
        print(f"[AI Connector] Ollama request failed: {e}")
        return None

def ask_llm(prompt, system_instruction="You are NexusHR Enterprise AI Agent."):
    """
    Route prompt to active LLM provider.
    Returns string response, or None if no provider configured or call failed.
    """
    provider, _, is_live = get_active_ai_provider()
    if not is_live:
        return None

    if provider == "OpenAI":
        return _call_openai(prompt, system_instruction)
    elif provider == "Google Gemini":
        return _call_gemini(prompt, system_instruction)
    elif provider == "Local Ollama":
        return _call_ollama(prompt, system_instruction)
    return None

def ask_policy_rag(query, doc_context):
    """
    Query LLM with grounded HR policy context.
    Returns LLM generated answer or None (to trigger fallback).
    """
    system_instruction = (
        "You are NexusHR Policy Copilot, an enterprise HR compliance specialist. "
        "Answer employee policy questions accurately based ONLY on the provided policy documents. "
        "Highlight key numbers, days, or rules using <strong> tags. Format concisely with paragraphs. "
        "If the answer is not in the context, state that HR leadership should be consulted."
    )
    prompt = f"POLICY CONTEXT:\n{doc_context}\n\nEMPLOYEE QUESTION: {query}\n\nACCURATE ENTERPRISE ANSWER:"
    return ask_llm(prompt, system_instruction)

def generate_llm_offer_letter(name, role, department, manager, start_date, ctc):
    """
    Generate customized offer letter via LLM.
    Returns letter text or None (to trigger fallback).
    """
    system_instruction = "You are NexusHR Autonomous Onboarding Orchestrator. Draft formal, encouraging enterprise offer letters."
    prompt = (
        f"Draft an official executive job offer letter for {name}.\n"
        f"Role: {role}\nDepartment: {department}\nReporting Manager: {manager}\n"
        f"Start Date: {start_date}\nCTC: {ctc}\n"
        f"Include standard terms: 3 months probation, NDA & IP assignment, background check contingency. "
        f"Sign off from Priya Ramesh, Head of People & Culture — NexusHR Inc."
    )
    return ask_llm(prompt, system_instruction)
