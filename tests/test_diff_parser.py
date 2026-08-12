from pathlib import Path

from app.parser.diff import FileDiff, Hunk, Range, parse_diff

RAW = (Path(__file__).parent / "fixtures" / "sample.diff").read_text()
RESULTS = parse_diff(RAW)
BY_PATH = {f.path: f for f in RESULTS}


def test_parsed_file_count():
    assert len(RESULTS) == 3


def test_modified_file_hunk():
    fd = BY_PATH["app/foo.py"]
    assert len(fd.hunks) == 1
    hunk = fd.hunks[0]
    assert hunk.old_range == Range(1, 4)
    assert hunk.new_range == Range(1, 5)
    assert "+import sys" in hunk.lines


def test_new_file_path_and_range():
    fd = BY_PATH["app/new_file.py"]
    assert fd.hunks[0].old_range == Range(0, 0)
    assert fd.hunks[0].new_range == Range(1, 3)


def test_deleted_file_path():
    assert "app/deleted.py" in BY_PATH


def test_binary_and_rename_skipped():
    assert "assets/image.png" not in BY_PATH
    assert "app/renamed_new.py" not in BY_PATH
