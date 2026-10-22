"""Check numerical interfaces and export your own homework library."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib
import importlib.util
import json
import platform
import sys
import subprocess
import tempfile
import zipfile
import importlib.metadata
from pathlib import Path


def recording_helper():
    helper = Path(__file__).with_name("recording_integrity.py")
    if not helper.is_file():
        helper = Path(__file__).resolve().parents[1] / "common/recording_integrity.py"
    spec = importlib.util.spec_from_file_location("me537_recording_integrity", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return helper, module


def check(repo, on_pass=None):
    checks = []

    def passed(message):
        checks.append(message)
        if on_pass:
            on_pass(message)

    repo = Path(repo).resolve()
    source = repo / "src"
    if not (source / "byu_robomanip" / "kinematics.py").is_file():
        raise ValueError(
            "Use your homework repository root, containing src/byu_robomanip."
        )
    passed("Found your homework library in src/byu_robomanip.")
    sys.path.insert(0, str(source))
    import numpy as np

    kin = importlib.import_module("byu_robomanip.kinematics")
    if not Path(kin.__file__).resolve().is_relative_to(source):
        raise ValueError("Imported a different library; start a fresh Python process.")
    passed("Loaded the library from this repository.")
    # A separate two-link planar robot checks environment and interfaces.
    # Use the same small example on every operating system.
    arm = kin.SerialArm([[0, 0, 1.0, 0], [0, 0, 0.75, 0]])
    q = np.array([0.2, -0.1])
    T = np.asarray(arm.fk(q))
    if T.shape != (4, 4) or not np.isfinite(T).all():
        raise ValueError(
            f"Your fk() returned shape {T.shape}; it needs a finite 4-by-4 transform."
        )
    passed("Forward kinematics returned a finite 4-by-4 transform.")
    J = np.asarray(arm.jacob(q))
    if J.shape != (6, 2) or not np.isfinite(J).all():
        raise ValueError(
            f"Your jacob() returned shape {J.shape}; this two-link check needs a finite 6-by-2 matrix."
        )
    passed("The two-link Jacobian returned a finite 6-by-2 matrix.")
    return {
        "status": "environment_and_interfaces_pass",
        "checks": checks,
        "python": sys.version.split()[0],
        "system": platform.system(),
        "machine": platform.machine(),
        "numpy": np.__version__,
        "distribution_versions": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "scipy", "sympy")
            if any(
                d.metadata.get("Name", "").lower() == name
                for d in importlib.metadata.distributions()
            )
        },
        "library": str(Path(kin.__file__).resolve()),
        "notice": "This checks setup and shapes, not numerical correctness or exam readiness.",
    }


def checked_file(repo, path):
    if not path.is_relative_to(repo):
        raise ValueError("Practice files must be inside the repository.")
    for parent in (path, *path.parents):
        if parent == repo:
            break
        if parent.is_symlink() or getattr(parent, "is_junction", lambda: False)():
            raise ValueError("Practice export does not support source/output links.")
    if not path.is_file() or not path.resolve().is_relative_to(repo):
        raise ValueError(f"Missing practice file: {path.name}")
    if path.stat().st_size > 20_000_000:
        raise ValueError("A practice file exceeds 20 MB; contact the instructor.")
    return path


def next_steps(export):
    if not export["motion_included"]:
        return [
            "Animation and the VS Code recorder were NOT checked by this command.",
            "Next: continue with Step 3 of your download's README.md (VS Code setup).",
        ]
    steps = [
        f"Included animation report: {export['graphics_status']}",
        f"Included recorder session: {export['session_state']}",
        "This export command does not rerun the animation or verify recorder completeness.",
        f"Final recording / exported source comparison: {export['recording_integrity']['status'].upper()}",
    ]
    integrity = export["recording_integrity"]
    for kind in ("changed", "added", "missing", "record_issues"):
        steps.extend(f"  {kind}: {name}" for name in integrity[kind])
    if integrity["status"] != "match":
        steps.append(
            "REVIEW NEEDED: inspect recording_integrity.json and report discrepancies to the instructor."
        )
    if export["graphics_status"] != "completed":
        steps.append(
            "Next: finish the visible animation exercise (Step 5), then make a new export. A numerical-only run is not a graphics pass."
        )
    if export["session_state"] != "finished":
        steps.append(
            "Next: complete the recorder practice and finish its session (Steps 4 and 6), then make a new export."
        )
    if (
        export["graphics_status"] == "completed"
        and export["session_state"] == "finished"
    ):
        steps.append(
            f"Next: upload {Path(export['zip']).name} on Learning Suite. "
            "This upload is required to receive a score and grade for Part 2. "
            "The session log is included automatically; you do not need to inspect it."
        )
    return steps


def practice_summary(report, export):
    """Portable student-readable report, without local machine paths."""
    lines = [
        "ME 537 PRACTICE CHECK",
        "",
        "RESULT: PASS - your library export was created and tested.",
        "",
        "Checks completed:",
        *[f"  PASS: {message}" for message in report["checks"]],
        "  PASS: The exported library ran in a fresh Python process.",
        "",
        f"Python: {report['python']} | OS: {report['system']} | CPU: {report['machine']}",
        f"ZIP: {Path(export['zip']).name}",
        "Detailed report inside the ZIP: practice_report.json",
        "",
    ]
    lines.extend(next_steps(export))
    lines.extend(
        [
            "",
            "This is a setup and packaging check, not a grade or a check of numerical accuracy.",
            "",
            f"Files included in the ZIP ({len(export['files'])}):",
            *[f"  {name}" for name in export["files"]],
            "",
        ]
    )
    return "\n".join(lines)


def export_practice(
    repo, output, demo_results=None, require_session=False, on_pass=None
):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    summary_path = output.with_name(output.stem + "_summary.txt")
    for target in (output, summary_path):
        if target.exists():
            raise FileExistsError(f"This file already exists: {target}")
    files = [
        p
        for p in (repo / "src" / "byu_robomanip").rglob("*.py")
        if "__pycache__" not in p.parts
    ]
    if not (repo / "src/byu_robomanip/kinematics.py").is_file():
        raise ValueError("Include your own src/byu_robomanip/kinematics.py.")
    data = {
        p.relative_to(repo).as_posix(): checked_file(repo, p).read_bytes()
        for p in files
    }
    data["check_environment.py"] = Path(__file__).read_bytes()
    helper, checker = recording_helper()
    data["recording_integrity.py"] = helper.read_bytes()
    session_state = "not_included"
    if demo_results:
        motion_directory = Path(demo_results).absolute()
        if ".." in motion_directory.parts:
            raise ValueError("Use a practice-results path without '..'.")
        for name in ("trajectory.npy", "joint_angles.csv", "practice_report.json"):
            data[f"practice_motion/{name}"] = checked_file(
                repo, motion_directory / name
            ).read_bytes()
        motion_report = json.loads(data["practice_motion/practice_report.json"])
        if motion_report.get("demo_id") != "two_link_fixed_motion_v1":
            raise ValueError("Select the two-link demo's results folder.")
        for name in ("preview.png",):
            if (motion_directory / name).exists():
                data[f"practice_motion/{name}"] = checked_file(
                    repo, motion_directory / name
                ).read_bytes()
        for demo_source in (repo / "exam_helpers").rglob("*.py"):
            if "__pycache__" not in demo_source.parts:
                data[demo_source.relative_to(repo).as_posix()] = checked_file(
                    repo, demo_source
                ).read_bytes()
        session = repo / "exam_session"
        if session.exists():
            metadata = checked_file(repo, session / "session.json")
            session_state = json.loads(metadata.read_text(encoding="utf-8")).get(
                "state"
            )
            if session_state == "recording":
                raise ValueError(
                    "Run ME537: Finish Session before exporting practice logs."
                )
            for p in [
                *session.glob("*.json"),
                *session.glob("*.jsonl"),
                *(session / "snapshots").glob("*.json"),
            ]:
                data[p.relative_to(repo).as_posix()] = checked_file(
                    repo, p
                ).read_bytes()
    if require_session and session_state != "finished":
        raise ValueError(
            "A finished recorder session is required; use --demo-results and finish the practice session."
        )
    if sum(map(len, data.values())) > 100_000_000:
        raise ValueError("Practice export exceeds 100 MB; contact the instructor.")
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, content in sorted(data.items()):
            bundle.writestr(name, content)
    # Rerun the exported library in a fresh process using this same setup check.
    with tempfile.TemporaryDirectory(prefix="me537 practice export ") as directory:
        with zipfile.ZipFile(output) as bundle:
            for name in bundle.namelist():
                target = Path(directory) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bundle.read(name))
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(Path(directory) / "check_environment.py"),
                "--repo",
                directory,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode:
            detail = result.stderr[-3000:]
            try:
                detail = json.loads(result.stderr.strip().splitlines()[-1])["error"]
            except (ValueError, KeyError, IndexError, TypeError):
                pass
            raise ValueError("The exported copy could not run: " + detail)
        report = json.loads(result.stdout)
    if on_pass:
        on_pass("The exported library ran in a fresh Python process.")
    report.pop("library", None)  # Exclude the temporary local machine path.
    report["session_state"] = session_state
    report["motion_included"] = bool(demo_results)
    integrity = checker.compare_recording(data, practice=True)
    data["recording_integrity.json"] = (json.dumps(integrity, indent=2) + "\n").encode()
    report["recording_integrity"] = integrity
    if demo_results:
        report["graphics_status"] = motion_report.get("graphics", {}).get("status")
    data["practice_report.json"] = (json.dumps(report, indent=2) + "\n").encode()
    exported = {
        "zip": str(output),
        "summary": str(summary_path),
        "status": "exported_library_imports_in_fresh_process",
        "session_state": session_state,
        "motion_included": bool(demo_results),
        "graphics_status": report.get("graphics_status", "not_included"),
        "recording_integrity": integrity,
        "files": sorted([*data, "practice_summary.txt", "practice_manifest.json"]),
    }
    summary = practice_summary(report, exported)
    data["practice_summary.txt"] = summary.encode("utf-8")
    manifest = {
        "notice": "Local consistency hashes, not proof of authorship.",
        "cleanup": {
            "version": 1,
            "results_directory": (
                motion_directory.relative_to(repo).as_posix() if demo_results else None
            ),
        },
        "sha256": {
            name: hashlib.sha256(content).hexdigest()
            for name, content in sorted(data.items())
        },
    }
    with zipfile.ZipFile(output, "a", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("practice_report.json", data["practice_report.json"])
        bundle.writestr("recording_integrity.json", data["recording_integrity.json"])
        bundle.writestr("practice_summary.txt", data["practice_summary.txt"])
        bundle.writestr("practice_manifest.json", json.dumps(manifest, indent=2) + "\n")
    with summary_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(summary)
    return exported


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the student summary",
    )
    parser.add_argument(
        "--export",
        type=Path,
        help="Create and rerun a practice ZIP from your own library",
    )
    parser.add_argument(
        "--demo-results",
        type=Path,
        help="Include two-link motion results and disclosed session logs when present",
    )
    parser.add_argument(
        "--require-session",
        action="store_true",
        help="Require a finished practice recorder session",
    )
    args = parser.parse_args()
    stage = "Check your homework library"
    passed = (
        None if args.json else lambda message: print(f"  PASS: {message}", flush=True)
    )
    try:
        if not args.json:
            print("ME 537 practice: library and export check", flush=True)
            print(f"Repository: {Path(args.repo).resolve()}")
            print(f"Python: {sys.executable} ({platform.python_version()})\n")
            print(f"1. {stage}", flush=True)
        # Keep incidental prints from the student's library out of JSON stdout.
        with (
            contextlib.redirect_stdout(sys.stderr)
            if args.json
            else contextlib.nullcontext()
        ):
            report = check(args.repo, passed)
            if args.export:
                stage = "Create and test your library ZIP"
                if not args.json:
                    print(f"\n2. {stage}", flush=True)
                report["export"] = export_practice(
                    args.repo,
                    args.export,
                    args.demo_results,
                    args.require_session,
                    passed,
                )
            elif args.demo_results or args.require_session:
                raise ValueError("--demo-results and --require-session need --export.")
        if args.json:
            print(json.dumps(report, indent=2))
        elif args.export:
            export = report["export"]
            print("\nRESULT: PASS - your library export was created and tested.")
            print(f"ZIP created: {export['zip']}")
            print(f"Readable summary: {export['summary']}")
            print(
                f"Included: {len(export['files'])} files. The summary lists every file."
            )
            print()
            for message in next_steps(export):
                print(message)
            print(
                "This checks setup and packaging, not numerical accuracy or exam readiness."
            )
        else:
            print("\nRESULT: PASS - the numerical library interface checks passed.")
            print(
                "Next: rerun with --export library_check_practice.zip to test your library export."
            )
            print(
                "Animation, graphics, recorder operation and numerical accuracy were not checked."
            )
    except Exception as error:
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "failed",
                        "stage": stage,
                        "error": f"{type(error).__name__}: {error}",
                    }
                ),
                file=sys.stderr,
            )
        else:
            print(f"\nRESULT: FAIL - {stage}.", file=sys.stderr)
            print(f"Problem: {error}", file=sys.stderr)
            if isinstance(error, FileExistsError):
                advice = "Choose a new ZIP filename, for example --export library_check_2.zip. Existing files are kept."
            elif isinstance(error, ModuleNotFoundError):
                advice = "Activate the virtual environment you use for homework and check that its dependencies are installed."
            elif isinstance(error, NotImplementedError):
                advice = "This uses your existing homework fk()/jacob() methods. Check that they are implemented in this working copy."
            elif isinstance(error, subprocess.TimeoutExpired):
                advice = "The exported library did not finish within 30 seconds. Check for input prompts, GUI startup or a loop in your library."
            else:
                advice = "Correct the problem above, then rerun. See Step 3 of the README.md supplied with these tools for setup help."
            print(f"What to do: {advice}", file=sys.stderr)
            print(
                "If it still fails, send your instructor this output and the Python interpreter path shown above.",
                file=sys.stderr,
            )
            if stage == "Create and test your library ZIP" and not isinstance(
                error, FileExistsError
            ):
                print(
                    "This attempt did not produce a verified export. A ZIP left by a failed check is incomplete.",
                    file=sys.stderr,
                )
        sys.exit(1)
