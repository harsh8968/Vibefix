import json
import google.generativeai as genai
from agents.gemini_utils import clean_json_response, get_gemini_model_name
from models.manifest import CodeManifest

def run_intake(raw_code: str) -> CodeManifest:
    model = genai.GenerativeModel(
        model_name=get_gemini_model_name(),
        system_instruction="You are a code analysis agent. Analyze the provided code and return ONLY valid JSON. No markdown, no backticks, no explanation. Just raw JSON."
    )
    
    prompt = f"""Analyze this code and return JSON with these exact keys:
language, framework, file_count, complexity_score,
has_env_vars, has_database, has_auth, summary

Code:
{raw_code}"""

    try:
        response = model.generate_content(prompt)
        text = clean_json_response(response.text)
        data = json.loads(text)
        
        return CodeManifest(
            raw_code=raw_code,
            language=data.get("language", "unknown"),
            framework=data.get("framework", "none"),
            file_count=data.get("file_count", 1),
            complexity_score=data.get("complexity_score", 5),
            has_env_vars=data.get("has_env_vars", False),
            has_database=data.get("has_database", False),
            has_auth=data.get("has_auth", False),
            summary=data.get("summary", "")
        )
    except Exception as e:
        return CodeManifest(
            raw_code=raw_code,
            language="unknown",
            framework="none",
            file_count=1,
            complexity_score=5,
            has_env_vars=False,
            has_database=False,
            has_auth=False,
            summary="Parse failed"
        )
