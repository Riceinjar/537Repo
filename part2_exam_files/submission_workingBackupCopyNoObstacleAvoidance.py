"""Write your method below. Run this file to watch the resulting motion."""

import time
import numpy as np
from exam_robot import arm

def compute_robot_path(q_init, goal, obst_location, obst_radius):
    # Use arm and your own homework library to compute the path.
    # Return a list of joint configurations (or a NumPy array with one per row).
    # Include q_init first. Use radians for revolute joints and meters for prismatic joints.
    # TODO: implement your method here.
    # Save the initial row with q_s.append(q_init.copy()); use q = q_init.copy() to work.
    # Store each configuration using q_s.append(q.copy()).
    K = .2*np.array([[1, 0, 0],
                     [0, 1, 0],
                     [0, 0, 1]])
    qf, error_f, iters, converged, q_hist, qdot_hist = arm.ik_position(
        target = goal, 
        q0 = q_init, 
        method = "pinv",
        K = K,
        max_iter = 100,
        debug = True)
    q_s = q_hist
    if (q_s[0] != q_init.tolist()):
        raise Exception('First entry for q_s is not equal to q_init.')
    
    return q_s

if __name__ == "__main__":
    # These values are for your own testing. The instructor will also use other cases.
    from byu_robomanip.visualization import VizScene

    q_0 = np.zeros(arm.n)
    goal = np.array([0.0, 2.0, 4.0])
    obst_position = np.array([0.0, 3.0, 2.0])
    obst_rad = 1.0

    q_s = compute_robot_path(q_0, goal, obst_position, obst_rad)
    if len(q_s) == 0:
        raise ValueError(
            "No path returned. Implement compute_robot_path before running it."
        )

    viz = VizScene()
    viz.add_arm(arm)
    viz.add_marker(goal, radius=0.1)
    viz.add_obstacle(obst_position, rad=obst_rad)
    viz.update(qs=[q_0.tolist()])
    for q in q_s:
        viz.update(qs=[np.asarray(q).tolist()])
        time.sleep(0.02)
    viz.hold()
