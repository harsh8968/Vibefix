import json
from dataclasses import dataclass
import google.generativeai as genai
from agents.gemini_utils import clean_json_response, get_gemini_model_name
from models.manifest import CodeManifest

@dataclass
class PerformanceIssue:
    severity: str       # "HIGH" | "MEDIUM" | "LOW"
    pattern: str        # e.g. "N+1 Query", "Blocking I/O", "Quadratic Loop"
    description: str    # what is happening
    line_hint: str      # near which code
    impact: str         # e.g. "Slows down at 100+ records"
    fix: str            # one line fix

@dataclass
class PerformanceReport:
    issues: list[PerformanceIssue]
    high_count: int
    medium_count: int
    low_count: int
    estimated_bottleneck: str  # e.g. "Database layer" | "CPU" | "I/O" | "None detected"
    verdict: str               # "WILL NOT SCALE" | "NEEDS OPTIMIZATION" | "ACCEPTABLE" | "PERFORMANT"

def run_performance_audit(manifest: CodeManifest) -> PerformanceReport:
    model = genai.GenerativeModel(
        model_name=get_gemini_model_name(),
        system_instruction="You are a performance audit agent for source code.\nIdentify performance bottlenecks and anti-patterns.\nReturn ONLY valid JSON. No markdown. No explanation."
    )
    
    prompt = f"""Audit this code for performance issues.
Look specifically for:
- N+1 database query patterns
- Nested loops with O(n²) or worse complexity
- Blocking I/O operations (sleep, sync file reads)
- Missing pagination on DB queries
- Loading entire datasets into memory
- Repeated computation inside loops (should be cached)
- Missing indexes hint (querying without WHERE on large tables)

Return JSON:
{{
  "issues": [
    {{
      "severity": "HIGH|MEDIUM|LOW",
      "pattern": "pattern name",
      "description": "what is happening",
      "line_hint": "near which code",
      "impact": "what breaks at scale",
      "fix": "one line fix"
    }}
  ],
  "estimated_bottleneck": "Database layer|CPU|I/O|None detected",
  "verdict": "WILL NOT SCALE|NEEDS OPTIMIZATION|ACCEPTABLE|PERFORMANT"
}}

Context:
- Language: {manifest.language}
- Framework: {manifest.framework}
- Has Database: {manifest.has_database}
- Complexity Score: {manifest.complexity_score}/10

Code:
{manifest.raw_code}"""

    try:
        response = model.generate_content(prompt)
        text = clean_json_response(response.text)
            
        data = json.loads(text)
        
        raw_issues = data.get("issues", [])
        issues = []
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for i in raw_issues:
            severity = i.get("severity", "LOW").upper()
            if severity not in counts:
                severity = "LOW"
            counts[severity] += 1
                
            issues.append(PerformanceIssue(
                severity=severity,
                pattern=i.get("pattern", "Unknown"),
                description=i.get("description", ""),
                line_hint=i.get("line_hint", ""),
                impact=i.get("impact", ""),
                fix=i.get("fix", "")
            ))
            
        return PerformanceReport(
            issues=issues,
            high_count=counts["HIGH"],
            medium_count=counts["MEDIUM"],
            low_count=counts["LOW"],
            estimated_bottleneck=data.get("estimated_bottleneck", "None detected"),
            verdict=data.get("verdict", "ACCEPTABLE")
        )
    except Exception as e:
        return PerformanceReport(
            issues=[PerformanceIssue(
                severity="HIGH",
                pattern="Audit Failed",
                description="Could not parse performance response",
                line_hint="unknown",
                impact="unknown",
                fix="Check Gemini API integration"
            )],
            high_count=1,
            medium_count=0,
            low_count=0,
            estimated_bottleneck="Unknown",
            verdict="NEEDS OPTIMIZATION"
        )
