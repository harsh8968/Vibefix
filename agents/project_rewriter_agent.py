import json
from dataclasses import dataclass
import google.generativeai as genai
from agents.gemini_utils import clean_json_response, get_gemini_model_name
from agents.orchestrator_agent import OrchestratorReport
from agents.project_scanner import ProjectSnapshot


@dataclass
class ProjectRewriteReport:
    files: list[dict]
    changes_made: list[str]
    changes_count: int
    fixes_applied: int
    fixes_skipped: int
    final_verdict: str


def run_project_rewriter(
    snapshot: ProjectSnapshot,
    orchestrator_report: OrchestratorReport
) -> ProjectRewriteReport:
    model = genai.GenerativeModel(
        model_name=get_gemini_model_name(),
        system_instruction="You are a senior software engineer fixing one project file at a time. Return ONLY valid JSON. No markdown. No explanation."
    )

    plan_str = "\n".join(
        f"#{item.priority} [{item.severity}] {item.title}: {item.action}"
        for item in orchestrator_report.fix_plan
    )

    changed_files: list[dict] = []
    changes_made: list[str] = []
    fixes_applied = 0
    failures = 0

    for project_file in snapshot.files:
        prompt = f"""Review this single file from a larger project and apply only the relevant fixes from the project fix plan.

FILE PATH:
{project_file.path}

FILE CONTENT:
{project_file.content}

PROJECT FIX PLAN:
{plan_str}

Rules:
- If this file does not need changes, set "changed" to false and omit "content".
- If this file needs changes, return the complete replacement file content.
- Preserve the file path exactly.
- Preserve original behavior wherever possible.
- Do not include secrets or API keys.
- Do not invent new dependencies unless the fix clearly requires one.
- Add short VIBEFIX comments only above meaningful changed sections.

Return JSON:
{{
  "changed": true,
  "path": "{project_file.path}",
  "content": "complete replacement file content when changed",
  "changes_made": ["plain English summary for this file"],
  "fixes_applied": number
}}"""

        try:
            response = model.generate_content(prompt)
            data = json.loads(clean_json_response(response.text))
        except Exception:
            failures += 1
            continue

        if not data.get("changed"):
            continue

        content = data.get("content")
        if not content:
            continue

        changed_files.append({
            "path": data.get("path", project_file.path),
            "content": content,
        })
        changes_made.extend(data.get("changes_made", []))
        fixes_applied += int(data.get("fixes_applied", 0) or 0)

    fixes_skipped = max(len(orchestrator_report.fix_plan) - fixes_applied, 0) + failures
    if changed_files and failures == 0:
        verdict = "SIGNIFICANTLY IMPROVED"
    elif changed_files:
        verdict = "PARTIALLY FIXED"
    else:
        verdict = "PARTIALLY FIXED"
        changes_made.append("No files were rewritten; review the fix plan manually")

    return ProjectRewriteReport(
        files=changed_files,
        changes_made=changes_made,
        changes_count=len(changes_made),
        fixes_applied=fixes_applied,
        fixes_skipped=fixes_skipped,
        final_verdict=verdict
    )
