import json
import os
import subprocess
import tempfile

from app.analysis.finding import Finding, MypyError


def run_mypy(files: dict[str, str]) -> list[Finding]:
    if not files:
        return []
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_paths = []
        for path, source in files.items():
            dest = os.path.join(tmpdir, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(source)
            temp_paths.append(dest)
        result = subprocess.run(
            ["mypy", "--output", "json", "--ignore-missing-imports",
             "--no-error-summary", *temp_paths],
            capture_output=True,
            text=True,
        )
        if result.returncode >= 2:
            raise MypyError(result.stderr)
        findings = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if item.get("severity") == "note":
                continue
            original = os.path.relpath(item["file"], tmpdir).replace(os.sep, "/")
            findings.append(Finding(
                path=original,
                line=item["line"],
                col=item["column"],
                rule=item.get("code") or "mypy",
                message=item["message"],
                severity=item["severity"],
            ))
        return findings
