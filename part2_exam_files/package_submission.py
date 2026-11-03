"""Create a disclosed, inspectable submission ZIP; never copy the virtual environment."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import re
import sys
import tempfile
import zipfile
from pathlib import Path

MAX_FILE_BYTES = 20_000_000
BASE_DISTRIBUTIONS = ("numpy", "scipy", "sympy")

_spec = importlib.util.spec_from_file_location(
    "me537_package_paths", Path(__file__).with_name("exam_paths.py")
)
_paths = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_paths)
exam_directory = _paths.exam_directory


def recording_check(data):
    helper = Path(__file__).with_name("recording_integrity.py")
    if not helper.is_file():
        helper = Path(__file__).resolve().parents[1] / "common/recording_integrity.py"
    spec = importlib.util.spec_from_file_location("me537_recording_integrity", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.compare_recording(data)


def checked_file(root, path):
    path = Path(path)
    if not path.is_relative_to(root):
        raise ValueError(f"Path outside the submission: {path}")
    for parent in (path, *path.parents):
        if parent == root:
            break
        if parent.is_symlink() or getattr(parent, "is_junction", lambda: False)():
            raise ValueError(f"Links/junctions are not supported: {parent}")
    if not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError(f"Missing file or external path: {path}")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"File exceeds the 20 MB submission limit: {path}")
    return path


def source_files(root):
    work = exam_directory(root)
    required = ["submission.py", "exam_robot.py", "explanation.txt", "dependencies.txt"]
    files = [work / name for name in required]
    package_root = root / "src" / "byu_robomanip"
    if not (package_root / "kinematics.py").is_file():
        raise ValueError("Include your own src/byu_robomanip/kinematics.py.")
    for folder in {package_root, root / "exam_helpers", work / "exam_helpers"}:
        files.extend(p for p in folder.rglob("*.py") if "__pycache__" not in p.parts)
    if (work / "requirements-extra.txt").exists():
        files.append(work / "requirements-extra.txt")
    config = work / "submission_files.json"
    if config.exists():
        files.append(config)
        assets = json.loads(config.read_text(encoding="utf-8"))["assets"]
        if not isinstance(assets, list):
            raise ValueError("submission_files.json assets must be a list.")
        for name in assets:
            p = Path(name)
            if (
                p.is_absolute()
                or ".." in p.parts
                or not p.parts
                or p.parts[0] != "exam_assets"
                or p.suffix.lower() not in {".json", ".txt", ".csv", ".npy", ".npz"}
            ):
                raise ValueError(
                    "Extra assets must be explicit data files in exam_assets/."
                )
            files.append(work / p)
    session = work / "exam_session"
    if session.exists():
        # Everything recorded here is disclosed in the recorder's consent dialog.
        metadata = session / "session.json"
        if not metadata.is_file():
            raise ValueError("Incomplete exam_session folder: missing session.json.")
        if json.loads(metadata.read_text(encoding="utf-8")).get("state") == "recording":
            raise ValueError("Run ME537: Finish Session in VS Code before packaging.")
        files.extend(session.glob("*.json"))
        files.extend(session.glob("*.jsonl"))
        files.extend((session / "snapshots").glob("*.json"))
    return sorted({checked_file(root, p) for p in files})


def environment_report(root):
    installed = {}
    for dist in importlib.metadata.distributions():
        name, version = dist.metadata.get("Name", ""), dist.version
        # Record names/versions only: no local paths, pip URLs, tokens or credentials.
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
            installed[name.lower().replace("_", "-")] = version
    requested = list(BASE_DISTRIBUTIONS)
    extras = exam_directory(root) / "requirements-extra.txt"
    if extras.exists():
        for line in extras.read_text(encoding="utf-8").splitlines():
            name = line.partition("#")[0].strip()
            if not name:
                continue
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
                raise ValueError(
                    "requirements-extra.txt accepts distribution names only."
                )
            requested.append(name.lower().replace("_", "-"))
    missing = [name for name in requested if name not in installed]
    extra_missing = [name for name in missing if name not in BASE_DISTRIBUTIONS]
    if extra_missing:
        raise ValueError(
            f"Declared extra dependencies are not installed: {extra_missing}"
        )
    pins = []
    for name in sorted(set(requested) - set(missing)):
        version = installed[name]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.!+_-]*", version):
            raise ValueError(f"Unsupported dependency version for {name}")
        pins.append(f"{name}=={version}")
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "machine": platform.machine(),
        "installed_distribution_versions": installed,
        "missing_optional_baseline_distributions": missing,
        "notice": "Inventory and observed direct pins; not an offline or cross-platform environment.",
    }, "\n".join(pins) + "\n"


def package(root, output, case=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    work = exam_directory(root)
    prefix = _paths.exam_prefix(root)
    if output.exists():
        raise FileExistsError(output)
    files = source_files(root)
    generated = {}
    env, pins = environment_report(root)
    generated["environment.json"] = (json.dumps(env, indent=2) + "\n").encode()
    generated["requirements-observed.txt"] = pins.encode()
    if case is not None:
        import numpy as np

        spec = importlib.util.spec_from_file_location(
            "me537_package_preflight", Path(__file__).with_name("preflight.py")
        )
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)

        try:
            trajectory, checks = runner.run_submission(root, case, return_checks=True)
            with tempfile.TemporaryDirectory(prefix="me537-path-") as directory:
                path = Path(directory) / "trajectory.npy"
                np.save(path, trajectory, allow_pickle=False)
                generated[prefix + "results/trajectory.npy"] = path.read_bytes()
            preflight_report = {
                "status": "import_and_output_contract_pass",
                "rows": len(trajectory),
                **checks,
            }
        except Exception as error:
            # Broken code can still earn method/explanation credit. Preserve the
            # failure report, rather than preventing the student from submitting.
            preflight_report = {
                "status": "execution_or_contract_failure",
                "error": f"{type(error).__name__}: {error}",
            }
        generated[prefix + "results/public_case.json"] = (
            json.dumps(case, indent=2) + "\n"
        ).encode()
        generated[prefix + "results/preflight_report.json"] = (
            json.dumps(
                {
                    **preflight_report,
                    "notice": "Student-side record; not a convergence, collision, or authorship grade.",
                },
                indent=2,
            )
            + "\n"
        ).encode()

    def archive_name(path):
        # Preserve recorded source paths. Log files use their established ZIP
        # location so older instructor review tools can still find the session.
        session = work / "exam_session"
        if path.is_relative_to(session):
            return "exam_session/" + path.relative_to(session).as_posix()
        return path.relative_to(root).as_posix()

    data = {archive_name(p): p.read_bytes() for p in files}
    data.update(generated)
    integrity = recording_check(data)
    data["recording_integrity.json"] = (json.dumps(integrity, indent=2) + "\n").encode()
    if sum(len(value) for value in data.values()) > 100_000_000:
        raise ValueError(
            "Submission exceeds 100 MB uncompressed; contact the instructor about the recording size."
        )
    manifest = {
        "format_version": 2,
        "python": sys.version.split()[0],
        "preflight_ran": case is not None,
        "preflight_status": (
            preflight_report["status"] if case is not None else "not_run_via_API"
        ),
        "session_included": "exam_session/session.json" in data,
        "source_sha256": {
            name: hashlib.sha256(content).hexdigest()
            for name, content in sorted(data.items())
        },
        "notice": "Local hashes detect inconsistency, not deliberate fabrication or AI use.",
    }
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, content in sorted(data.items()):
            bundle.writestr(name, content)
        bundle.writestr(
            "submission_manifest.json", json.dumps(manifest, indent=2) + "\n"
        )
    return {
        "zip": str(output),
        "file_count": len(data) + 1,
        "preflight_ran": case is not None,
        "preflight_status": manifest["preflight_status"],
        "preflight_review_flags": (
            preflight_report.get("review_flags", []) if case is not None else []
        ),
        "session_included": manifest["session_included"],
        "recording_integrity": integrity,
        "files": sorted([*data, "submission_manifest.json"]),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        case = json.loads(args.case.read_text(encoding="utf-8"))
        result = package(args.root, args.output, case)
        print(json.dumps(result, indent=2))
        integrity = result["recording_integrity"]
        print("\nFINAL RECORDING / SUBMISSION CHECK:", integrity["status"].upper())
        print("Coverage:", integrity["coverage"])
        for kind in ("changed", "added", "missing", "record_issues"):
            for name in integrity[kind]:
                print(f"  {kind}: {name}")
        if integrity["status"] != "match":
            print(
                "REVIEW NEEDED: the ZIP was created with this flag. See recording_integrity.json; contact the instructor about discrepancies."
            )
    except Exception as error:
        print(f"Packaging failed: {error}", file=sys.stderr)
        sys.exit(1)
