"""Check your completed submission locally before handing it in."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

_spec = importlib.util.spec_from_file_location(
    "me537_exam_paths", Path(__file__).with_name("exam_paths.py")
)
_paths = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_paths)
exam_directory = _paths.exam_directory


def read_model(robot):
    """Keep model-format checks in the supplied tool, outside student code."""
    if hasattr(robot, "arm"):
        table = np.asarray(robot.arm.dh, dtype=float)
        types = list(robot.arm.jt)
        original = list(getattr(robot, "original_joints", [0, 1, 2, 3]))
    else:
        # Accept the earlier starter for students who already downloaded it.
        previous = robot.get_model()
        table = np.asarray(previous["dh"], dtype=float)
        types = list(previous["joint_types"])
        original = list(previous["original_joints"])
    if (
        table.ndim != 2
        or table.shape[1] != 4
        or not 4 <= len(table) <= 6
        or not np.isfinite(table).all()
    ):
        raise ValueError("Your DH table must have 4 to 6 finite rows of four numbers.")
    if len(types) != len(table) or any(t not in {"r", "p"} for t in types):
        raise ValueError("The arm's jt list must contain one 'r' or 'p' per DH row.")
    if (
        len(original) != 4
        or any(type(i) is not int or not 0 <= i < len(table) for i in original)
        or original != sorted(set(original))
    ):
        raise ValueError(
            "original_joints must list the four original row indices in order."
        )
    if any(types[i] != "r" for i in original):
        raise ValueError("The original four joints must remain revolute.")
    return {"dh": table.tolist(), "joint_types": types, "original_joints": original}


def expand_initial(q_init, model):
    """Map instructor cases into an optional five- or six-joint student model."""
    initial = np.asarray(q_init, dtype=float)
    n = len(model["dh"])
    if initial.shape == (4,) and n > 4:
        expanded = np.zeros(n)
        expanded[model["original_joints"]] = initial
        return expanded
    if initial.shape != (n,):
        raise ValueError(
            f"q_init must contain four original angles or {n} model coordinates."
        )
    return initial.copy()


def run_submission(
    root, case, timeout=60, python=None, return_model=False, return_checks=False
):
    """Use a fresh process, so imports/hangs cannot contaminate the caller."""
    root = Path(root).resolve()
    work = exam_directory(root)
    if not (work / "submission.py").is_file():
        raise ValueError("Put submission.py in part2_exam_files/ beside src/.")
    if not (root / "src" / "byu_robomanip" / "kinematics.py").is_file():
        raise ValueError("Include your own src/byu_robomanip package.")
    with tempfile.TemporaryDirectory(prefix="me537-preflight-") as directory:
        directory = Path(directory)
        case_file = directory / "case.json"
        output = directory / "path.npy"
        case_file.write_text(json.dumps(case), encoding="utf-8")
        result = subprocess.run(
            [
                # Preserve POSIX venv symlinks; resolving them selects base Python.
                str(Path(python).expanduser().absolute() if python else sys.executable),
                "-I",
                "-B",
                str(Path(__file__).resolve()),
                "--worker",
                str(root),
                str(case_file),
                str(output),
            ],
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if result.returncode or not output.is_file():
            raise RuntimeError(
                f"Submission failed ({result.returncode}).\n"
                + result.stderr[-4000:]
                + "\n"
                + result.stdout[-2000:]
            )
        path = np.load(output, allow_pickle=False)
        results = [path]
        for requested, suffix in (
            (return_model, ".model.json"),
            (return_checks, ".checks.json"),
        ):
            if requested:
                results.append(
                    json.loads(output.with_suffix(suffix).read_text(encoding="utf-8"))
                )
        return tuple(results) if len(results) > 1 else path


def validate(path, initial):
    path = np.asarray(path, dtype=float)
    if path.size == 0:
        raise ValueError(
            "No path returned. Implement compute_robot_path in submission.py and "
            "return at least one configuration, starting with q_init."
        )
    if (
        path.ndim != 2
        or not 4 <= path.shape[1] <= 6
        or path.shape[1] != len(initial)
        or not 1 <= len(path) <= 5001
    ):
        raise ValueError(
            "Return an H-by-N path matching q_init, with 4 <= N <= 6 and 1 <= H <= 5001."
        )
    if not np.isfinite(path).all():
        raise ValueError("The trajectory contains NaN or infinite values.")
    return path


def trajectory_checks(path, initial):
    """Review cues only: never reject or repair an otherwise usable trajectory."""
    matches = bool(np.allclose(path[0], initial, atol=1e-8, rtol=0))
    maximum_step = (
        float(np.max(np.abs(np.diff(path, axis=0)))) if len(path) > 1 else 0.0
    )
    large_step = maximum_step > 0.10 + 1e-10
    flags = []
    if not matches:
        flags.append(
            "First configuration differs from the original q_init. "
            "Review your saved first row; use .copy() when saving NumPy arrays."
        )
    if large_step:
        flags.append(
            "Large joint change recorded for instructor review. "
            "0.10 is a review threshold, not a pass/fail limit."
        )
    return {
        "initial_configuration_matches": matches,
        "expected_first_configuration": np.asarray(initial).tolist(),
        "returned_first_configuration": path[0].tolist(),
        "maximum_joint_step": maximum_step,
        "joint_step_review_threshold": 0.10,
        "large_joint_step": large_step,
        "review_flags": flags,
    }


def worker(root, case_file, output):
    root = Path(root).resolve()
    work = exam_directory(root)
    source = root / "src"
    sys.path[:0] = [str(work), str(root), str(source)]
    case = json.loads(Path(case_file).read_text(encoding="utf-8"))
    # The callable always receives float NumPy vectors, regardless of the JSON
    # representation or OS. Fail malformed instructor/local cases explicitly.
    vectors = []
    for name, size in (("q_init", None), ("goal", 3), ("obst_location", 3)):
        vector = np.asarray(case[name], dtype=float)
        valid_shape = (
            vector.ndim == 1 and 4 <= len(vector) <= 6
            if size is None
            else vector.shape == (size,)
        )
        if not valid_shape or not np.isfinite(vector).all():
            raise ValueError(
                f"{name} must be a finite vector with "
                + ("4 to 6 coordinates." if size is None else f"shape ({size},).")
            )
        vectors.append(vector)
    radius = float(case["obst_radius"])
    if not np.isfinite(radius) or radius <= 0:
        raise ValueError("obst_radius must be finite and positive.")
    # Remove runner-directory search entries: a missing exam_robot.py must
    # fail rather than silently falling back to the distributed tool's copy.
    own_directory = Path(__file__).resolve().parent
    sys.path[:] = [
        p
        for p in sys.path
        if not p or Path(p).resolve() != own_directory or own_directory == work
    ]
    import exam_robot

    model = read_model(exam_robot)
    vectors[0] = expand_initial(vectors[0], model)
    spec = importlib.util.spec_from_file_location("submission", work / "submission.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from byu_robomanip import kinematics

    if not Path(kinematics.__file__).resolve().is_relative_to(source):
        raise ValueError("The submission must use its own included homework library.")
    # The method may update its input array in place. Compare with the case's
    # original configuration, not an array that student code can change.
    initial = vectors[0].copy()
    path = module.compute_robot_path(*vectors, radius)
    path = validate(path, initial)
    np.save(output, path, allow_pickle=False)
    Path(output).with_suffix(".checks.json").write_text(
        json.dumps(trajectory_checks(path, initial)), encoding="utf-8"
    )
    Path(output).with_suffix(".model.json").write_text(
        json.dumps(model), encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        case = json.loads(args.case.read_text(encoding="utf-8"))
        path, checks = run_submission(args.root, case, return_checks=True)
        output = args.output or exam_directory(args.root) / "results/trajectory.npy"
        output.parent.mkdir(parents=True, exist_ok=True)
        np.save(output, path, allow_pickle=False)
        output.with_suffix(".checks.json").write_text(
            json.dumps(checks, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "status": "import_and_output_contract_pass",
                    "rows": len(path),
                    "trajectory": str(output.resolve()),
                    **checks,
                    "review_notice": "Review flags do not prevent saving or submission; the returned trajectory is unchanged.",
                    "notice": "No goal-accuracy or collision grade is calculated here.",
                },
                indent=2,
            )
        )
    except Exception as error:
        print(f"Preflight failed: {type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        worker(*sys.argv[2:])
    else:
        main()
