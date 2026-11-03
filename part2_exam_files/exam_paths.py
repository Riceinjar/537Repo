"""Locate exam work within the student's own homework repository."""

from pathlib import Path


def exam_directory(root):
    root = Path(root).resolve()
    nested = root / "part2_exam_files"
    if (nested / "submission.py").is_file():
        if (root / "submission.py").exists() or (root / "exam_robot.py").exists():
            raise ValueError(
                "Exam files exist both in the repository root and part2_exam_files/. "
                "Keep a backup, then keep your completed exam files in part2_exam_files/ "
                "and remove the old root-level copies."
            )
        if not nested.resolve().is_relative_to(root) or nested.is_symlink():
            raise ValueError("part2_exam_files must be inside the homework repository.")
        return nested
    # Previously exported submissions used the repository root.
    return root


def exam_prefix(root):
    relative = exam_directory(root).relative_to(Path(root).resolve()).as_posix()
    return "" if relative == "." else relative + "/"
