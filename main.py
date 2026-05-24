import os
import textwrap
from dotenv import load_dotenv
import google.generativeai as genai
from agents.intake_agent import run_intake
from agents.security_agent import run_security_audit
from agents.performance_agent import run_performance_audit
from agents.error_agent import run_error_audit
from agents.orchestrator_agent import run_orchestrator
from agents.rewriter_agent import run_rewriter

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

SAMPLE_CODE = """
from flask import Flask, request

app = Flask(__name__)

DB_PASSWORD = "admin123"

@app.route('/do_everything', methods=['POST'])
def god_function():
    # No try/except anywhere
    user = request.json['username']
    password = request.json['password']
    
    # Auth logic
    if password != "secret":
        raise Exception("Invalid credentials!")
        
    # Database query
    db_conn = connect_database(DB_PASSWORD)
    data = db_conn.execute(f"SELECT * FROM user_data WHERE user = '{user}'")
    
    # Email send
    send_notification_email(user, "You queried the DB!")
    
    return f"Success: {data}"
"""

def print_report(manifest):
    print("─────────────────────────────────────────")
    print("  VIBEFIX — INTAKE REPORT")
    print("─────────────────────────────────────────")
    print(f"  Language       : {manifest.language}")
    print(f"  Framework      : {manifest.framework}")
    print(f"  Complexity     : {manifest.complexity_score}/10")
    print(f"  Files Detected : {manifest.file_count}")
    print("─────────────────────────────────────────")
    print("  Risk Flags:")
    
    if manifest.has_database:
        print("  ⚠️  Database usage detected")
    else:
        print("  ✅  No database usage detected")
        
    if manifest.has_auth:
        print("  ⚠️  Auth logic detected")
    else:
        print("  ✅  No auth logic detected")
        
    if manifest.has_env_vars:
        print("  ⚠️  Env vars detected")
    else:
        print("  ✅  No env vars detected")
        
    print("─────────────────────────────────────────")
    print("  Summary:")
    
    # Wrap summary to approx 40 characters for nice formatting
    wrapped_summary = textwrap.fill(manifest.summary, width=40)
    for line in wrapped_summary.split('\\n'):
        print(f"  {line}")
        
    print("─────────────────────────────────────────")
    print("  Status: MANIFEST READY → passing to agents")
    print("─────────────────────────────────────────")

def print_security_report(report):
    print("─────────────────────────────────────────")
    print("  VIBEFIX — SECURITY AUDIT")
    print("─────────────────────────────────────────")
    print(f"  Verdict: {report.verdict}")
    print("─────────────────────────────────────────")
    
    print(f"  🔴 CRITICAL  ({report.critical_count})")
    crit_issues = [i for i in report.issues if i.severity == "CRITICAL"]
    for idx, i in enumerate(crit_issues):
        prefix = "  └─" if idx == len(crit_issues) - 1 else "  ├─"
        print(f"{prefix} [{i.category}]")
        pipe = "      " if idx == len(crit_issues) - 1 else "  │   "
        print(f"{pipe}Issue : {i.description}")
        print(f"{pipe}Near  : {i.line_hint}")
        print(f"{pipe}Fix   : {i.fix}")
        if idx != len(crit_issues) - 1:
            print("  │")
    
    print()
    print(f"  🟡 HIGH  ({report.high_count})")
    high_issues = [i for i in report.issues if i.severity == "HIGH"]
    for idx, i in enumerate(high_issues):
        prefix = "  └─" if idx == len(high_issues) - 1 else "  ├─"
        print(f"{prefix} [{i.category}]")
        pipe = "      " if idx == len(high_issues) - 1 else "  │   "
        print(f"{pipe}Issue : {i.description}")
        print(f"{pipe}Near  : {i.line_hint}")
        print(f"{pipe}Fix   : {i.fix}")
        if idx != len(high_issues) - 1:
            print("  │")

    print()
    print(f"  🟢 MEDIUM / LOW  ({report.medium_count + report.low_count})")
    med_low_issues = [i for i in report.issues if i.severity in ("MEDIUM", "LOW")]
    for idx, i in enumerate(med_low_issues):
        prefix = "  └─" if idx == len(med_low_issues) - 1 else "  ├─"
        print(f"{prefix} [{i.category}]")
        pipe = "      " if idx == len(med_low_issues) - 1 else "  │   "
        print(f"{pipe}Issue : {i.description}")
        print(f"{pipe}Near  : {i.line_hint}")
        print(f"{pipe}Fix   : {i.fix}")
        if idx != len(med_low_issues) - 1:
            print("  │")

    print("─────────────────────────────────────────")
    print("  Status: SECURITY SCAN DONE → next agent")
    print("─────────────────────────────────────────")

def print_performance_report(report):
    print("─────────────────────────────────────────")
    print("  VIBEFIX — PERFORMANCE AUDIT")
    print("─────────────────────────────────────────")
    print(f"  Verdict  : {report.verdict}")
    print(f"  Bottleneck: {report.estimated_bottleneck}")
    print("─────────────────────────────────────────")
    
    print(f"  🔴 HIGH  ({report.high_count})")
    high_issues = [i for i in report.issues if i.severity == "HIGH"]
    for idx, i in enumerate(high_issues):
        prefix = "  └─" if idx == len(high_issues) - 1 else "  ├─"
        print(f"{prefix} [{i.pattern}]")
        pipe = "      " if idx == len(high_issues) - 1 else "  │   "
        print(f"{pipe}What   : {i.description}")
        print(f"{pipe}Near   : {i.line_hint}")
        print(f"{pipe}Impact : {i.impact}")
        print(f"{pipe}Fix    : {i.fix}")
        if idx != len(high_issues) - 1:
            print("  │")

    print()
    print(f"  🟡 MEDIUM  ({report.medium_count})")
    med_issues = [i for i in report.issues if i.severity == "MEDIUM"]
    for idx, i in enumerate(med_issues):
        prefix = "  └─" if idx == len(med_issues) - 1 else "  ├─"
        print(f"{prefix} [{i.pattern}]")
        pipe = "      " if idx == len(med_issues) - 1 else "  │   "
        print(f"{pipe}What   : {i.description}")
        print(f"{pipe}Near   : {i.line_hint}")
        print(f"{pipe}Impact : {i.impact}")
        print(f"{pipe}Fix    : {i.fix}")
        if idx != len(med_issues) - 1:
            print("  │")

    print()
    print(f"  🟢 LOW  ({report.low_count})")
    low_issues = [i for i in report.issues if i.severity == "LOW"]
    for idx, i in enumerate(low_issues):
        prefix = "  └─" if idx == len(low_issues) - 1 else "  ├─"
        print(f"{prefix} [{i.pattern}]")
        pipe = "      " if idx == len(low_issues) - 1 else "  │   "
        print(f"{pipe}What   : {i.description}")
        print(f"{pipe}Near   : {i.line_hint}")
        print(f"{pipe}Impact : {i.impact}")
        print(f"{pipe}Fix    : {i.fix}")
        if idx != len(low_issues) - 1:
            print("  │")

    print("─────────────────────────────────────────")
    print("  Status: PERFORMANCE SCAN DONE → next agent")
    print("─────────────────────────────────────────")

def print_error_report(report):
    print("─────────────────────────────────────────")
    print("  VIBEFIX — ERROR HANDLING AUDIT")
    print("─────────────────────────────────────────")
    print(f"  Verdict             : {report.verdict}")
    if report.has_any_error_handling:
        print("  Has Any Handling    : ✅ Yes")
    else:
        print("  Has Any Handling    : ❌ None detected")
    print("─────────────────────────────────────────")
    
    print(f"  🔴 HIGH  ({report.high_count})")
    high_issues = [i for i in report.issues if i.severity == "HIGH"]
    for idx, i in enumerate(high_issues):
        prefix = "  └─" if idx == len(high_issues) - 1 else "  ├─"
        print(f"{prefix} [{i.issue_type}]")
        pipe = "      " if idx == len(high_issues) - 1 else "  │   "
        print(f"{pipe}What        : {i.description}")
        print(f"{pipe}Near        : {i.line_hint}")
        print(f"{pipe}Consequence : {i.consequence}")
        print(f"{pipe}Fix         : {i.fix}")
        if idx != len(high_issues) - 1:
            print("  │")

    print()
    print(f"  🟡 MEDIUM  ({report.medium_count})")
    med_issues = [i for i in report.issues if i.severity == "MEDIUM"]
    for idx, i in enumerate(med_issues):
        prefix = "  └─" if idx == len(med_issues) - 1 else "  ├─"
        print(f"{prefix} [{i.issue_type}]")
        pipe = "      " if idx == len(med_issues) - 1 else "  │   "
        print(f"{pipe}What        : {i.description}")
        print(f"{pipe}Near        : {i.line_hint}")
        print(f"{pipe}Consequence : {i.consequence}")
        print(f"{pipe}Fix         : {i.fix}")
        if idx != len(med_issues) - 1:
            print("  │")

    print()
    print(f"  🟢 LOW  ({report.low_count})")
    low_issues = [i for i in report.issues if i.severity == "LOW"]
    for idx, i in enumerate(low_issues):
        prefix = "  └─" if idx == len(low_issues) - 1 else "  ├─"
        print(f"{prefix} [{i.issue_type}]")
        pipe = "      " if idx == len(low_issues) - 1 else "  │   "
        print(f"{pipe}What        : {i.description}")
        print(f"{pipe}Near        : {i.line_hint}")
        print(f"{pipe}Consequence : {i.consequence}")
        print(f"{pipe}Fix         : {i.fix}")
        if idx != len(low_issues) - 1:
            print("  │")

    print("─────────────────────────────────────────")
    print("  Status: ERROR AUDIT DONE → next agent")
    print("─────────────────────────────────────────")

def print_orchestrator_report(report):
    print("─────────────────────────────────────────")
    print("  VIBEFIX — ORCHESTRATOR REPORT")
    print("─────────────────────────────────────────")
    print(f"  Overall Verdict : {report.overall_verdict}")
    ship_emoji = "✅" if report.ship_ready else "❌"
    print(f"  Ship Ready      : {ship_emoji}")
    print(f"  Total Issues    : {report.total_issues}")
    print("─────────────────────────────────────────")
    print(f"  💬 \"{report.one_liner}\"")
    print("─────────────────────────────────────────")
    print("  PRIORITIZED FIX PLAN:")
    print("─────────────────────────────────────────")
    
    for idx, i in enumerate(report.fix_plan):
        if i.severity in ("CRITICAL", "HIGH"):
            emoji = "🔴"
        elif i.severity == "MEDIUM":
            emoji = "🟡"
        else:
            emoji = "🟢"
            
        print(f"  #{i.priority} {emoji} [{i.source_agent}] {i.title}")
        print(f"     → {i.action}")
        if idx != len(report.fix_plan) - 1:
            print()

    print("─────────────────────────────────────────")
    print("  Status: ORCHESTRATION DONE → ready for rewriter")
    print("─────────────────────────────────────────")

def print_rewriter_report(report):
    print("─────────────────────────────────────────")
    print("  VIBEFIX — CODE REWRITER")
    print("─────────────────────────────────────────")
    print(f"  Final Verdict   : {report.final_verdict}")
    total_fixes = report.fixes_applied + report.fixes_skipped
    print(f"  Fixes Applied   : {report.fixes_applied}/{total_fixes}")
    print(f"  Fixes Skipped   : {report.fixes_skipped}")
    print(f"  Changes Made    : {report.changes_count}")
    print("─────────────────────────────────────────")
    print("  CHANGES APPLIED:")
    
    num_changes = len(report.changes_made)
    applied_count = num_changes - report.fixes_skipped
    
    for idx, change in enumerate(report.changes_made):
        if idx >= applied_count:
            print(f"  ⚠️  {change}")
        else:
            print(f"  ✅ {change}")
            
    if num_changes == 0:
        print("  None")

    print("─────────────────────────────────────────")
    print("  FIXED CODE:")
    print("─────────────────────────────────────────")
    print(report.fixed_code)
    print("─────────────────────────────────────────")
    print("  PIPELINE COMPLETE")
    print("  Intake → Security → Performance → Errors")
    print("  → Orchestrator → Rewriter ✅")
    print("─────────────────────────────────────────")

if __name__ == "__main__":
    print("Running intake agent analysis...")
    manifest = run_intake(SAMPLE_CODE)
    print_report(manifest)
    
    print("Running security audit analysis...")
    security_report = run_security_audit(manifest)
    print_security_report(security_report)
    
    print("Running performance audit analysis...")
    performance_report = run_performance_audit(manifest)
    print_performance_report(performance_report)
    
    print("Running error handling audit analysis...")
    error_report = run_error_audit(manifest)
    print_error_report(error_report)
    
    print("Running orchestrator analysis...")
    orchestrator_report = run_orchestrator(manifest, security_report, performance_report, error_report)
    print_orchestrator_report(orchestrator_report)
    
    print("Running code rewriter...")
    rewriter_report = run_rewriter(manifest, orchestrator_report)
    print_rewriter_report(rewriter_report)
