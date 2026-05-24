import json
from dataclasses import dataclass
import google.generativeai as genai
from models.manifest import CodeManifest

@dataclass
class SecurityIssue:
    severity: str        # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    category: str        # e.g. "Hardcoded Secrets", "SQL Injection", "XSS"
    description: str     # one line: what the issue is
    line_hint: str       # e.g. "near 'password = admin123'" or "unknown"
    fix: str             # one line: how to fix it

@dataclass
class SecurityReport:
    issues: list[SecurityIssue]
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    verdict: str         # "UNSAFE - DO NOT SHIP" | "RISKY" | "MOSTLY SAFE" | "CLEAN"

def run_security_audit(manifest: CodeManifest) -> SecurityReport:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction="You are a security audit agent for source code.\nFind all security vulnerabilities.\nReturn ONLY valid JSON. No markdown. No explanation."
    )
    
    prompt = f"""Audit this code for security vulnerabilities.
Return JSON with this structure:
{{
  "issues": [
    {{
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "category": "issue category",
      "description": "what the issue is",
      "line_hint": "near which code",
      "fix": "how to fix in one line"
    }}
  ],
  "verdict": "UNSAFE - DO NOT SHIP|RISKY|MOSTLY SAFE|CLEAN"
}}

Context from intake:
- Language: {manifest.language}
- Framework: {manifest.framework}
- Has Auth: {manifest.has_auth}
- Has Database: {manifest.has_database}

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
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for i in raw_issues:
            severity = i.get("severity", "LOW").upper()
            if severity not in counts:
                severity = "LOW"
            counts[severity] += 1
                
            issues.append(SecurityIssue(
                severity=severity,
                category=i.get("category", "Unknown"),
                description=i.get("description", ""),
                line_hint=i.get("line_hint", ""),
                fix=i.get("fix", "")
            ))
            
        return SecurityReport(
            issues=issues,
            critical_count=counts["CRITICAL"],
            high_count=counts["HIGH"],
            medium_count=counts["MEDIUM"],
            low_count=counts["LOW"],
            verdict=data.get("verdict", "RISKY")
        )
    except Exception as e:
        return SecurityReport(
            issues=[SecurityIssue(
                severity="CRITICAL",
                category="Audit Failed",
                description="Could not parse security response",
                line_hint="unknown",
                fix="Check Gemini API integration"
            )],
            critical_count=1,
            high_count=0,
            medium_count=0,
            low_count=0,
            verdict="UNSAFE - DO NOT SHIP"
        )
