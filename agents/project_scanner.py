from dataclasses import dataclass
from pathlib import Path
import shutil


SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".scss",
    ".json", ".yaml", ".yml", ".toml", ".md", ".sql", ".java", ".go",
    ".rs", ".php", ".rb", ".cs", ".cpp", ".c", ".h",
}

SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "node_modules", "dist", "build", ".next", ".vercel",
    ".venv", "venv", "env", "coverage", "vibefix-output",
}

SKIP_FILES = {".env", ".env.local", ".env.production"}

MAX_FILE_BYTES = 60_000
MAX_PROJECT_CHARS = 260_000


@dataclass
class ProjectFile:
    path: str
    content: str


@dataclass
class ProjectSnapshot:
    root: Path
    files: list[ProjectFile]
    skipped: list[str]
    raw_code: str


def is_source_file(path: Path) -> bool:
    return path.suffix.lower() in SOURCE_EXTENSIONS


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts) or path.name in SKIP_FILES


def read_text_file(path: Path) -> str:
    data = path.read_bytes()
    if len(data) > MAX_FILE_BYTES:
        data = data[:MAX_FILE_BYTES]
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def build_project_snapshot(project_path: str) -> ProjectSnapshot:
    root = Path(project_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Project folder does not exist: {root}")

    files: list[ProjectFile] = []
    skipped: list[str] = []
    total_chars = 0

    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if should_skip(relative):
            if path.is_file():
                skipped.append(str(relative))
            continue
        if not path.is_file() or not is_source_file(path):
            continue

        content = read_text_file(path)
        next_total = total_chars + len(content)
        if next_total > MAX_PROJECT_CHARS:
            skipped.append(f"{relative} (project context limit reached)")
            continue

        files.append(ProjectFile(path=str(relative).replace("\\", "/"), content=content))
        total_chars = next_total

    if not files:
        raise ValueError(f"No supported source files found in: {root}")

    raw_code = "\n\n".join(
        f"===== FILE: {file.path} =====\n{file.content}" for file in files
    )

    return ProjectSnapshot(root=root, files=files, skipped=skipped, raw_code=raw_code)


def copy_project_without_junk(snapshot: ProjectSnapshot, output_dir: str) -> Path:
    target = Path(output_dir).resolve()
    if target == snapshot.root or snapshot.root in target.parents and target.name == "":
        raise ValueError("Output folder must be separate from the project root.")
    if snapshot.root == target or target in snapshot.root.parents:
        raise ValueError("Output folder cannot be the project root or one of its parents.")

    if target.exists():
        shutil.rmtree(target)

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = set()
        for name in names:
            item = Path(directory, name)
            relative = item.relative_to(snapshot.root)
            if should_skip(relative):
                ignored.add(name)
        return ignored

    shutil.copytree(snapshot.root, target, ignore=ignore)
    return target


def write_changed_files(output_root: Path, files: list[dict]) -> list[str]:
    written: list[str] = []
    for file in files:
        relative_path = str(file.get("path", "")).strip().replace("\\", "/")
        content = file.get("content")
        if not relative_path or content is None:
            continue

        destination = (output_root / relative_path).resolve()
        try:
            destination.relative_to(output_root)
        except ValueError:
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        written.append(relative_path)
    return written
