from dataclasses import dataclass

@dataclass
class CodeManifest:
    raw_code: str
    language: str          # "python" | "javascript" | "typescript" | "unknown"
    framework: str         # "fastapi" | "flask" | "express" | "react" | "none"
    file_count: int        # estimate from code blocks / file headers in paste
    complexity_score: int  # 1-10 (line count + nesting depth heuristic)
    has_env_vars: bool     # detects os.environ, process.env, dotenv
    has_database: bool     # detects sql, mongoose, prisma, sqlalchemy
    has_auth: bool         # detects jwt, oauth, session, login, password
    summary: str           # 1-2 lines: what this code does
