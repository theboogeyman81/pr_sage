import json
import os
import subprocess
import tempfile

from app.analysis.finding import Finding, RuffError


def run_ruff(files: dict[str, str]) -> list[Finding]:
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
            ["ruff", "check", "--output-format", "json", "--no-cache", *temp_paths],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode >= 2:
            raise RuffError(result.stderr)
        findings = []
        for item in json.loads(result.stdout or "[]"):
            original = os.path.relpath(item["filename"], tmpdir).replace(os.sep, "/")
            findings.append(Finding(
                path=original,
                line=item["location"]["row"],
                col=item["location"]["column"],
                rule=item["code"],
                message=item["message"],
                severity="error",
            ))
        return findings
