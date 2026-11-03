"""Optional GUI replay, deliberately separate from import and planning."""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", type=Path)
    parser.add_argument("--trajectory", required=True, type=Path)
    parser.add_argument(
        "--case", type=Path, help="Optional case JSON to show goal and obstacle."
    )
    args = parser.parse_args()
    from exam_paths import exam_directory

    work = exam_directory(args.root)
    sys.path[:0] = [
        str(work),
        str(args.root.resolve()),
        str(args.root.resolve() / "src"),
    ]
    from byu_robomanip.kinematics import SerialArm
    from byu_robomanip.visualization import VizScene
    import exam_robot
    from preflight import read_model

    model = read_model(exam_robot)
    path = np.load(args.trajectory, allow_pickle=False)
    viz = VizScene()
    viz.add_arm(SerialArm(model["dh"], jt=model["joint_types"]))
    if args.case:
        case = json.loads(args.case.read_text(encoding="utf-8"))
        viz.add_marker(case["goal"], radius=0.1)
        viz.add_obstacle(case["obst_location"], rad=case["obst_radius"])
    for q in path:
        viz.update(qs=[q.tolist()])
        time.sleep(0.02)
    viz.hold()


if __name__ == "__main__":
    main()
