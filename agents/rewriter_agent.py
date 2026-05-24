import json
from dataclasses import dataclass
import google.generativeai as genai
from agents.gemini_utils import clean_json_response, get_gemini_model_name
from models.manifest import CodeManifest
from agents.orchestrator_agent import OrchestratorReport

@dataclass
class RewriterReport:
    fixed_code: str
    changes_made: list[str]
    changes_count: int
    fixes_applied: int
    fixes_skipped: int
    final_verdict: str

def run_rewriter(
    manifest: CodeManifest,
    orchestrator_report: OrchestratorReport
) -> RewriterReport:
    model = genai.GenerativeModel(
        model_name=get_gemini_model_name(),
        system_instruction="You are a senior software engineer.\nYou receive broken vibe-coded code and a prioritized fix plan.\nRewrite the code applying every fix in the plan.\nReturn ONLY valid JSON. No markdown. No explanation."
    )
    
    plan_str = "\\n".join([f"#{i.priority} [{i.severity}] {i.title}: {i.action}" for i in orchestrator_report.fix_plan])
    
    prompt = f"""Rewrite this code applying all fixes from the plan below.

ORIGINAL CODE:
{manifest.raw_code}

FIX PLAN TO APPLY:
{plan_str}

Rules for rewriting:
- Apply every fix in priority order (1 first)
- Keep the original logic and functionality intact
- Add proper error handling where missing
- Move hardcoded secrets to os.environ.get() calls
- Add input validation where missing
- Do NOT add new features, only fix what is listed
- Add a comment above each changed section: # VIBEFIX: what was fixed

Return JSON:
{{
  "fixed_code": "complete rewritten code as a single string",
  "changes_made": ["list of changes applied in plain english"],
  "fixes_applied": number,
  "fixes_skipped": number,
  "final_verdict": "PRODUCTION READY|SIGNIFICANTLY IMPROVED|PARTIALLY FIXED"
}}"""

    try:
        response = model.generate_content(prompt)
        text = clean_json_response(response.text)
            
        data = json.loads(text)
        
        changes = data.get("changes_made", [])
        
        return RewriterReport(
            fixed_code=data.get("fixed_code", manifest.raw_code),
            changes_made=changes,
            changes_count=len(changes),
            fixes_applied=data.get("fixes_applied", 0),
            fixes_skipped=data.get("fixes_skipped", 0),
            final_verdict=data.get("final_verdict", "PARTIALLY FIXED")
        )
    except Exception as e:
        return RewriterReport(
            fixed_code=manifest.raw_code,
            changes_made=["Rewrite failed - apply fixes manually"],
            changes_count=1,
            fixes_applied=0,
            fixes_skipped=len(orchestrator_report.fix_plan),
            final_verdict="PARTIALLY FIXED"
        )
