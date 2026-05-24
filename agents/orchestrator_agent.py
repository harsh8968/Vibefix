import json
from dataclasses import dataclass
import google.generativeai as genai
from agents.gemini_utils import clean_json_response, get_gemini_model_name
from models.manifest import CodeManifest
from agents.security_agent import SecurityReport
from agents.performance_agent import PerformanceReport
from agents.error_agent import ErrorReport

@dataclass
class FixItem:
    priority: int        # 1 = fix first, 2 = fix second, etc.
    source_agent: str    # "Security" | "Performance" | "Error Handling"
    severity: str        # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    title: str           # short name e.g. "Hardcoded DB Password"
    action: str          # exact one-line fix instruction

@dataclass
class OrchestratorReport:
    fix_plan: list[FixItem]
    total_issues: int
    ship_ready: bool
    overall_verdict: str
    one_liner: str

def run_orchestrator(
    manifest: CodeManifest,
    security_report: SecurityReport,
    performance_report: PerformanceReport,
    error_report: ErrorReport
) -> OrchestratorReport:
    model = genai.GenerativeModel(
        model_name=get_gemini_model_name(),
        system_instruction="You are a senior engineering lead reviewing audit reports from multiple agents.\nSynthesize all findings into a single prioritized fix plan.\nReturn ONLY valid JSON. No markdown. No explanation."
    )
    
    sec_issues_str = "\\n".join([f"- [{i.severity}] {i.category}: {i.description} | Fix: {i.fix}" for i in security_report.issues])
    perf_issues_str = "\\n".join([f"- [{i.severity}] {i.pattern}: {i.description} | Fix: {i.fix}" for i in performance_report.issues])
    err_issues_str = "\\n".join([f"- [{i.severity}] {i.issue_type}: {i.description} | Fix: {i.fix}" for i in error_report.issues])
    
    prompt = f"""You have received audit reports from 3 agents. Synthesize into one fix plan.

SECURITY ISSUES:
{sec_issues_str}

PERFORMANCE ISSUES:
{perf_issues_str}

ERROR HANDLING ISSUES:
{err_issues_str}

Rules for prioritization:
1. CRITICAL security issues always come first
2. HIGH security issues before HIGH performance issues
3. Error handling issues that expose internals treated as security (bump up)
4. Performance issues ranked by impact (database > CPU > I/O)
5. Duplicate or overlapping fixes should be merged into one item

Return JSON:
{{
  "fix_plan": [
    {{
      "priority": 1,
      "source_agent": "Security|Performance|Error Handling",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "title": "short title",
      "action": "exact fix instruction"
    }}
  ],
  "ship_ready": false,
  "overall_verdict": "DO NOT SHIP|NEEDS WORK|ALMOST THERE|SHIP IT",
  "one_liner": "one sentence summary for the dev"
}}"""

    try:
        response = model.generate_content(prompt)
        text = clean_json_response(response.text)
            
        data = json.loads(text)
        
        raw_plan = data.get("fix_plan", [])
        fix_plan = []
        
        for i in raw_plan:
            fix_plan.append(FixItem(
                priority=i.get("priority", len(fix_plan) + 1),
                source_agent=i.get("source_agent", "Unknown"),
                severity=i.get("severity", "LOW").upper(),
                title=i.get("title", "Unknown Issue"),
                action=i.get("action", "")
            ))
            
        fix_plan.sort(key=lambda x: x.priority)
            
        return OrchestratorReport(
            fix_plan=fix_plan,
            total_issues=len(fix_plan),
            ship_ready=data.get("ship_ready", False),
            overall_verdict=data.get("overall_verdict", "DO NOT SHIP"),
            one_liner=data.get("one_liner", "")
        )
    except Exception as e:
        return OrchestratorReport(
            fix_plan=[],
            total_issues=0,
            ship_ready=False,
            overall_verdict="DO NOT SHIP",
            one_liner="Orchestration failed - review individual agent reports"
        )
