"""Remove verified practice artifacts after uploading the practice ZIP.

Without --apply, show the cleanup plan. Keep the final ZIP, its summary,
practice_files/, and the student's own library. Close the ME537 window first.
"""

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath

try:
    from .prepare_vscode import user_data_directory
except ImportError:  # Also support the downloaded script run directly.
    from prepare_vscode import user_data_directory


def checked_target(repo, relative):
    name = PurePosixPath(relative)
    if name.is_absolute() or ".." in name.parts or "\\" in relative or ":" in relative:
        raise ValueError(f"Unsupported cleanup path: {relative}")
    target = repo / name
    if target == repo or not target.resolve().is_relative_to(repo):
        raise ValueError("Cleanup targets must stay inside the practice repository.")
    for item in (target, *target.parents):
        if item == repo:
            break
        if item.is_symlink() or getattr(item, "is_junction", lambda: False)():
            raise ValueError(f"Cleanup will not follow links: {relative}")
    return target


def read_archive(archive):
    with zipfile.ZipFile(archive) as bundle:
        if sum(item.file_size for item in bundle.infolist()) > 100_000_000:
            raise ValueError("Practice archive exceeds 100 MB.")
        names = bundle.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Practice archive contains duplicate members.")
        data = {name: bundle.read(name) for name in names if not name.endswith("/")}
    if "practice_manifest.json" not in data:
        raise ValueError("Select the practice submission ZIP created in Step 6.")
    manifest = json.loads(data["practice_manifest.json"])
    if not isinstance(manifest, dict) or not isinstance(manifest.get("sha256"), dict):
        raise ValueError("Invalid practice manifest; keep your files and export again.")
    expected = manifest["sha256"]
    if set(expected) != set(data) - {"practice_manifest.json"}:
        raise ValueError("Practice archive file list differs from its manifest.")
    for name, digest in expected.items():
        if hashlib.sha256(data[name]).hexdigest() != digest:
            raise ValueError(f"Practice archive hash mismatch: {name}")
    return data, manifest


def cleanup(repo, archive, apply=False):
    repo, archive = Path(repo).resolve(), Path(archive).resolve()
    if not (repo / "src/byu_robomanip/kinematics.py").is_file():
        raise ValueError(
            "Use the practice homework repository containing src/byu_robomanip."
        )
    if any(
        (folder / name).exists()
        for folder in (repo, repo / "part2_exam_files")
        for name in ("submission.py", "exam_robot.py")
    ):
        raise ValueError(
            "Exam files are present. Cleanup stopped to preserve exam work."
        )
    data, manifest = read_archive(archive)
    settings = manifest.get("cleanup", {})
    if not isinstance(settings, dict):
        raise ValueError(
            "Export a full practice ZIP with the updated tools before cleanup."
        )
    results_name = settings.get("results_directory")
    if (
        settings.get("version") != 1
        or not isinstance(results_name, str)
        or not results_name
    ):
        raise ValueError(
            "Export a full practice ZIP with the updated tools before cleanup."
        )
    if json.loads(data["exam_session/session.json"]).get("state") != "finished":
        raise ValueError("Finish the practice recording and export it before cleanup.")
    results = checked_target(repo, results_name)
    if any(
        part.startswith(".") for part in PurePosixPath(results_name).parts
    ) or PurePosixPath(results_name).parts[0] in {
        "src",
        "homework",
        "tests",
        "instructor",
        "practice_files",
        "part2_exam_files",
        # Preserve folders from earlier releases too.
        "practice_tools",
        "part2_handout",
        "exam_helpers",
        "exam_session",
        "exam_assets",
        "venv",
    }:
        raise ValueError(
            "The saved results location is not an eligible practice-results folder."
        )
    files = {}

    def include(relative, content):
        target = checked_target(repo, relative)
        if target.exists():
            if not target.is_file() or target.read_bytes() != content:
                raise ValueError(
                    f"Changed since export; nothing was deleted: {relative}. Export again first."
                )
            files[target] = content

    for name in (
        "trajectory.npy",
        "joint_angles.csv",
        "practice_report.json",
        "preview.png",
    ):
        archived = f"practice_motion/{name}"
        if archived in data:
            include(f"{results_name}/{name}", data[archived])
    include("exam_helpers/practice_motion.py", data["exam_helpers/practice_motion.py"])
    session_names = {name for name in data if name.startswith("exam_session/")}
    for name in session_names:
        include(name, data[name])
    session = checked_target(repo, "exam_session")
    if session.exists():
        for path in session.rglob("*"):
            checked_target(repo, path.relative_to(repo).as_posix())
            if (
                path.is_file()
                and path.relative_to(repo).as_posix() not in session_names
            ):
                raise ValueError(
                    "Unexported recording files exist; nothing was deleted. Export again first."
                )
    # Only preliminary library-check exports, with verified practice manifests.
    for candidate in repo.glob("*.zip"):
        if candidate.resolve() == archive or not candidate.stem.startswith(
            ("library_check", "library_practice")
        ):
            continue
        try:
            preliminary, _ = read_archive(candidate)
            if (
                json.loads(preliminary["practice_report.json"]).get("motion_included")
                is not False
            ):
                continue
        except (ValueError, KeyError, zipfile.BadZipFile):
            continue
        include(candidate.name, candidate.read_bytes())
        include(candidate.stem + "_summary.txt", preliminary["practice_summary.txt"])
    profile = checked_target(repo, ".me537_exam_profile")
    if profile.exists():
        workspace = json.loads(
            (profile / "ME537.code-workspace").read_text(encoding="utf-8")
        )
        if workspace.get("folders") != [{"path": ".."}] or not workspace.get(
            "settings", {}
        ).get("chat.disableAIFeatures"):
            raise ValueError("Unrecognized VS Code profile; nothing was deleted.")
    user_data = user_data_directory(repo, profile)
    external_user_data = user_data != profile / "user-data"
    if external_user_data and user_data.exists():
        marker = user_data / ".me537-repo"
        if (
            user_data.parent.is_symlink()
            or user_data.is_symlink()
            or not marker.is_file()
            or marker.is_symlink()
            or marker.read_text(encoding="utf-8") != str(repo) + "\n"
        ):
            raise ValueError("Unrecognized short VS Code user-data directory; nothing was deleted.")
    # All checks above finish before any removal. Never remove library files.
    print("Practice cleanup" + ("" if apply else " (preview only)"))
    for folder in (results, session):
        count = sum(path.is_relative_to(folder) for path in files)
        print(
            f"  {'Remove' if apply else 'Would remove'} {count} exported files from {folder.name}/"
        )
    for path in sorted(files):
        if path.parent == repo or path == repo / "exam_helpers/practice_motion.py":
            print(
                f"  {'Remove' if apply else 'Would remove'} {path.relative_to(repo).as_posix()}"
            )
    if profile.exists():
        print(
            f"  {'Remove' if apply else 'Would remove'} the generated .me537_exam_profile/ (close the ME537 window first)."
        )
    if external_user_data and user_data.exists():
        print(f"  {'Remove' if apply else 'Would remove'} the generated macOS VS Code user data in {user_data}.")
    print(
        f"Keep: {archive.name}, {archive.stem}_summary.txt, practice_files/, and your own homework/library files."
    )
    if not apply:
        print(
            "No files were deleted. After confirming your Learning Suite upload, rerun with --apply."
        )
        return
    if external_user_data and user_data.exists():
        if user_data.is_symlink() or (user_data / ".me537-repo").read_text(encoding="utf-8") != str(repo) + "\n":
            raise ValueError("Short VS Code user data changed during cleanup; stop and inspect it.")
    if profile.exists():
        # Resolve/check the exact owned directory immediately before recursive
        # removal. shutil.rmtree does not follow nested directory junctions.
        checked_target(repo, ".me537_exam_profile")
        shutil.rmtree(profile)
    if external_user_data and user_data.exists():
        shutil.rmtree(user_data)
    for path in files:
        path.unlink()
    parents = {p.parent for p in files} | {
        results,
        session,
        session / "snapshots",
        repo / "exam_helpers",
    }
    for folder in sorted(parents, key=lambda p: len(p.parts), reverse=True):
        if folder != repo and folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
    for folder in (results, session, repo / "exam_helpers"):
        if folder.is_dir():
            print(
                f"Kept {folder.relative_to(repo).as_posix()}/ because it contains other files."
            )
    print(
        "Cleanup complete. Keep the practice ZIP as your backup. You can reuse this repository and virtual environment for the exam; follow the exam README to start a new recording."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--archive", type=Path, default=Path("exam_practice.zip"))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Remove verified practice artifacts after upload",
    )
    args = parser.parse_args()
    try:
        cleanup(args.repo, args.archive, args.apply)
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as error:
        print(
            f"Practice cleanup stopped: {error}\nKeep your files and contact the instructor if needed. On Windows, close the ME537 VS Code window and retry from another terminal.",
            file=sys.stderr,
        )
        sys.exit(1)
