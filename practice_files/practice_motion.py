"""Two-link setup rehearsal: play and save a supplied joint-angle table.

Run the copy installed in exam_helpers/ by prepare_vscode.py --practice-demo.
This file is complete public setup code.
"""

import argparse
import importlib
import importlib.metadata
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

PRACTICE_NOTE = "Change this text to describe your OS practice check."
DEMO_ID = "two_link_fixed_motion_v1"
DH = [[0, 0, 1.0, 0], [0, 0, 0.75, 0]]
FPS = 20


class OutputFolderExistsError(FileExistsError):
    """The selected output already exists and must be kept unchanged."""

    def __init__(self, folder):
        self.folder = Path(folder)
        super().__init__(f"Output already exists: {self.folder}")


def fixed_trajectory():
    """Interpolate a supplied joint-angle table."""
    times = np.linspace(0, 6, 121)
    key_times = [0, 1.5, 3, 4.5, 6]
    key_angles = np.deg2rad([[10, 30], [70, -45], [15, 85], [-45, 20], [10, 30]])
    return times, np.column_stack(
        [np.interp(times, key_times, key_angles[:, joint]) for joint in range(2)]
    )


def own_library(repo):
    source = Path(repo).resolve() / "src"
    if not (source / "byu_robomanip/kinematics.py").is_file():
        raise ValueError("Use your homework repository containing src/byu_robomanip.")
    sys.path.insert(0, str(source))
    kin = importlib.import_module("byu_robomanip.kinematics")
    if not Path(kin.__file__).resolve().is_relative_to(source):
        raise ValueError("Another library is loaded; run in a fresh Python process.")
    return kin


def animate(arm, path, output, auto_close=False, hidden=False):
    """Render course meshes. Hidden mode is only used by instructor GUI checks."""
    import pyqtgraph as pg
    import pyqtgraph.opengl as gl
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget
    from byu_robomanip.visualization import (
        ArmMeshObject,
        EEMeshObject,
        _reset_opengl_shader_caches,
    )

    _reset_opengl_shader_caches()
    app = pg.mkQApp("ME537 practice")
    window = QWidget()
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, hidden)
    window.setWindowTitle("ME537 practice: supplied two-link motion")
    layout = QVBoxLayout(window)
    layout.addWidget(QLabel("Two-link practice | Supplied joint-angle playback"))
    view = gl.GLViewWidget()
    view.setMinimumSize(640, 420)
    view.setBackgroundColor("w")
    view.setCameraPosition(distance=4.8, azimuth=35, elevation=55)
    view.opts["center"] = pg.Vector(0.35, 0, 0)
    layout.addWidget(view, 1)
    grid = gl.GLGridItem(color=(50, 65, 80, 65))
    grid.setSize(4, 4)
    grid.setSpacing(0.5, 0.5)
    view.addItem(grid)
    axes = gl.GLAxisItem()
    axes.setSize(0.5, 0.5, 0.5)
    view.addItem(axes)
    mesh = ArmMeshObject(arm, q0=path[0])
    mesh.ee_object = EEMeshObject(scale=0.25)
    # Fit the course meshes over the complete supplied motion, including the
    # gripper, rather than relying on one initial pose or a particular display DPI.
    bounds = []
    for q in path:
        mesh.update(q)
        vertices = mesh.mesh.reshape(-1, 3)
        bounds.extend([vertices.min(axis=0), vertices.max(axis=0)])
    low, high = np.min(bounds, axis=0) - 0.2, np.max(bounds, axis=0) + 0.2
    mesh.update(path[0])
    view.opts["center"] = pg.Vector(*((low + high) / 2))
    view.addItem(mesh.mesh_object)
    tips = np.array([arm.fk(q)[:3, 3] for q in path])
    view.addItem(gl.GLLinePlotItem(pos=tips, color=(0.2, 0.4, 0.7, 0.4), width=1))
    label = QLabel("Starting motion...")
    layout.addWidget(label)
    close = QPushButton("Close after reviewing")
    close.clicked.connect(window.close)
    layout.addWidget(close)
    window.resize(800, 620)
    state = {
        "status": "interrupted",
        "frames_rendered": 0,
        "frames_expected": len(path),
    }
    errors = []
    timer = QTimer()
    try:
        window.show()
        app.processEvents()
        if not view.isValid():
            raise RuntimeError("No valid OpenGL context; test on a graphical desktop.")
        corners = np.array(
            [
                [x, y, z, 1]
                for x in (low[0], high[0])
                for y in (low[1], high[1])
                for z in (low[2], high[2])
            ]
        )
        distance = 3.0
        for _ in range(60):
            view.setCameraPosition(distance=distance, azimuth=35, elevation=55)
            viewport = (0, 0, view.width(), view.height())
            matrix = view.projectionMatrix(viewport, viewport) * view.viewMatrix()
            clip = corners @ np.asarray(matrix.copyDataTo()).reshape(4, 4).T
            if (clip[:, 3] > 0).all() and (
                np.abs(clip[:, :2] / clip[:, 3, None]) < 0.88
            ).all():
                break
            distance *= 1.06
        else:
            raise RuntimeError("Could not frame the supplied mesh trajectory.")

        def step():
            try:
                index = state["frames_rendered"]
                if not window.isVisible():
                    timer.stop()
                    return
                q = path[index]
                mesh.update(q)
                label.setText(
                    f"Frame {index + 1}/{len(path)} | Joint angles (rad): "
                    f"{q[0]:.3f}, {q[1]:.3f} | Close after the motion finishes."
                )
                # Capture only this application's robot viewport, never the screen.
                if output is not None and index == len(path) - 1:
                    image = view.grabFramebuffer()
                    if image.isNull():
                        raise RuntimeError("Robot viewport capture failed.")
                    if not image.save(str(output / "preview.png")):
                        raise RuntimeError("Could not save the robot preview.")
                state["frames_rendered"] += 1
                if state["frames_rendered"] == len(path):
                    timer.stop()
                    state["status"] = "completed"
                    label.setText(
                        "Motion complete. Preview and trajectory saved. You may close this window."
                        if output is not None
                        else "Replay complete. You may close this window."
                    )
                    if auto_close:
                        window.close()
            except Exception as error:
                errors.append(error)
                timer.stop()
                window.close()

        timer.timeout.connect(step)
        timer.start(0 if hidden else round(1000 / FPS))
        # Do not quit an existing QApplication; this loop owns only this window.
        while window.isVisible():
            app.processEvents()
            if not hidden:
                time.sleep(0.005)
        if errors:
            raise errors[0]
        return state
    finally:
        timer.stop()
        view.clear()
        window.close()
        window.deleteLater()
        app.processEvents()
        _reset_opengl_shader_caches()


def run_demo(
    repo,
    output=None,
    no_gui=False,
    trajectory=None,
    auto_close=False,
    hidden=False,
):
    repo = Path(repo).resolve()
    if trajectory is not None:
        if output is not None:
            raise ValueError(
                "Replay only displays saved motion; omit --output. "
                "To create new results, run without --trajectory."
            )
        path = np.load(trajectory, allow_pickle=False)
        if (
            path.ndim != 2
            or path.shape[1] != 2
            or not 2 <= len(path) <= 10000
            or not np.isfinite(path).all()
        ):
            raise ValueError(
                "Replay requires a finite H-by-2 trajectory, 2 to 10000 rows."
            )
    else:
        output = Path(output if output is not None else "results_practice").resolve()
        if not output.is_relative_to(repo) or output == repo:
            raise ValueError(
                "Choose a new results folder inside your practice repository."
            )
        if output.exists():
            raise OutputFolderExistsError(output)
        times, path = fixed_trajectory()
    kin = own_library(repo)
    arm = kin.SerialArm(DH)
    poses = np.asarray([arm.fk(q) for q in path])
    if poses.shape != (len(path), 4, 4) or not np.isfinite(poses).all():
        raise ValueError("Your FK must return a finite 4-by-4 transform for each pose.")
    if trajectory is not None:
        return {
            "mode": "replay",
            "trajectory": str(Path(trajectory).resolve()),
            "rows": len(path),
            "graphics": (
                {"status": "not_requested"}
                if no_gui
                else animate(arm, path, None, auto_close, hidden)
            ),
            "notice": "Loaded saved joint angles; no output files were created or changed.",
        }
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        # Another process may have created the folder since the initial check.
        raise OutputFolderExistsError(output) from None
    np.save(output / "trajectory.npy", path, allow_pickle=False)
    np.savetxt(
        output / "joint_angles.csv",
        np.column_stack([times, path]),
        delimiter=",",
        header="time_s,q1_rad,q2_rad",
        comments="",
    )
    report = {
        "demo_id": DEMO_ID,
        "note": PRACTICE_NOTE,
        "python": platform.python_version(),
        "system": platform.system(),
        "machine": platform.machine(),
        "fps": FPS,
        "rows": len(path),
        "own_library_loaded": True,
        "numerical_status": "finite_pose_shapes_pass",
        "graphics": {"status": "not_requested"},
        "distribution_versions": {},
        "notice": "Supplied two-link motion for checking graphics and file export. Editor recording is separate and requires explicit VS Code consent.",
    }
    for name in ("numpy", "PySide6", "pyqtgraph", "PyOpenGL"):
        try:
            report["distribution_versions"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    try:
        if not no_gui:
            report["graphics"] = animate(arm, path, output, auto_close, hidden)
    except Exception as error:
        report["graphics"] = {
            "status": "failed",
            "error": f"{type(error).__name__}: {error}",
        }
        raise
    finally:
        (output / "practice_report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="New results folder (default: results_practice); omit for replay",
    )
    parser.add_argument(
        "--trajectory",
        type=Path,
        help="Optional view-only replay of saved joint angles; creates no output files",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Numerical check only, not a graphics pass",
    )
    parser.add_argument(
        "--auto-close", action="store_true", help="Close after one complete playback"
    )
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                run_demo(
                    args.repo,
                    args.output,
                    args.no_gui,
                    args.trajectory,
                    args.auto_close,
                ),
                indent=2,
            )
        )
    except OutputFolderExistsError as error:
        print(
            "\nPractice motion was not run: the output location already exists.\n"
            f"Existing output: {error.folder}\n\n"
            "Choose one:\n"
            "  1. Delete the existing output folder and its contents if you no longer need them, then rerun.\n"
            "  2. Change the folder name after --output to a name that does not already exist.\n\n"
            "Example: use --output results_2_practice to choose a new practice results folder.\n"
            "Keep the rest of your command the same.\n"
            "Your existing output was left unchanged.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as error:
        print(
            f"Practice motion failed: {type(error).__name__}: {error}", file=sys.stderr
        )
        sys.exit(1)
