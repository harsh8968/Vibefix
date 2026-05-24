import json
from dataclasses import dataclass
import google.generativeai as genai
from models.manifest import CodeManifest

@dataclass
class ErrorIssue:
    severity: str       # "HIGH" | "MEDIUM" | "LOW"
    issue_type: str     # e.g. "Bare Except", "Silent Failure", "Missing Null Check"
    description: str    # what is wrong
    line_hint: str      # near which code
    consequence: str    # what goes wrong at runtime e.g. "App crashes silently"
    fix: str            # one line fix

@dataclass
class ErrorReport:
    issues: list[ErrorIssue]
    high_count: int
    medium_count: int
    low_count: int
    has_any_error_handling: bool  # True if code has at least one try/except or .catch()
    verdict: str   # "NO ERROR HANDLING" | "FRAGILE" | "PARTIAL" | "SOLID"

def run_error_audit(manifest: CodeManifest) -> ErrorReport:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction="You are an error handling audit agent for source code.\nFind all places where errors are unhandled, swallowed, or poorly managed.\nReturn ONLY valid JSON. No markdown. No explanation."
    )
    
    prompt = f"""Audit this code for error handling issues.
Look specifically for:
- Bare except clauses that catch everything silently (except: pass)
- Catching exceptions but not logging them
- Missing try/except around DB calls, API calls, file I/O
- Returning raw exception messages to the user
- Functions that return None on failure with no indication
- Unhandled promise rejections (if JS)
- No null/undefined checks before accessing properties
- Missing validation before type casting (int(), float())

Return JSON:
{{
  "issues": [
    {{
      "severity": "HIGH|MEDIUM|LOW",
      "issue_type": "type of error handling problem",
      "description": "what is wrong",
      "line_hint": "near which code",
      "consequence": "what breaks at runtime",
      "fix": "one line fix"
    }}
  ],
  "has_any_error_handling": true or false,
  "verdict": "NO ERROR HANDLING|FRAGILE|PARTIAL|SOLID"
}}

Context:
- Language: {manifest.language}
- Framework: {manifest.framework}
- Complexity Score: {manifest.complexity_score}/10

Code:
{manifest.raw_code}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
            
        data = json.loads(text)
        
        raw_issues = data.get("issues", [])
        issues = []
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for i in raw_issues:
            severity = i.get("severity", "LOW").upper()
            if severity not in counts:
                severity = "LOW"
            counts[severity] += 1
                
            issues.append(ErrorIssue(
                severity=severity,
                issue_type=i.get("issue_type", "Unknown"),
                description=i.get("description", ""),
                line_hint=i.get("line_hint", ""),
                consequence=i.get("consequence", ""),
                fix=i.get("fix", "")
            ))
            
        return ErrorReport(
            issues=issues,
            high_count=counts["HIGH"],
            medium_count=counts["MEDIUM"],
            low_count=counts["LOW"],
            has_any_error_handling=data.get("has_any_error_handling", False),
            verdict=data.get("verdict", "FRAGILE")
        )
    except Exception as e:
        return ErrorReport(
            issues=[ErrorIssue(
                severity="HIGH",
                issue_type="Audit Failed",
                description="Could not parse error handling response",
                line_hint="unknown",
                consequence="unknown",
                fix="Check Gemini API integration"
            )],
            high_count=1,
            medium_count=0,
            low_count=0,
            has_any_error_handling=False,
            verdict="FRAGILE"
        )
