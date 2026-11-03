import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUTHOR_LICENSE_NAME = "Kakali" + " " + "Bandyopadhyay"


def test_git_tracked_and_untracked_nonignored_files_do_not_contain_scan_terms():
    terms_path = ROOT / "scan_terms.txt"
    if not terms_path.exists():
        pytest.skip("scan_terms.txt is the author's private, untracked term list; the scan runs on the author's machine")
    terms = [line.strip().casefold() for line in terms_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    tracked_result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT, check=True, capture_output=True,
        stdin=subprocess.DEVNULL,
    )
    scan_paths = [
        item for item in tracked_result.stdout.decode("utf-8").split("\0")
        if item and Path(item).as_posix() != "scan_terms.txt"
    ]
    matches = []
    for relative in scan_paths:
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").casefold()
        for term in terms:
            if relative.casefold() == "license" and term == AUTHOR_LICENSE_NAME.casefold():
                continue
            if term in text:
                matches.append(f"{relative}: {term}")
    assert not matches, "Scan terms found in git-tracked or untracked non-ignored files:\n" + "\n".join(matches)
