"""Write your method below. Run this file to watch the resulting motion."""

import time
import numpy as np
from exam_robot import *

def path_pusher(q_init, goal, obst_location, obst_radius, tol): # allows tip of robot to avoid obstacle, but does not allow full arm to avoid obstacle. 
    res = 50
    p_0 = arm.fk(q_init)[:3,3]
    p_02g = goal - p_0
    p_02g = np.array(p_02g)
    increments = list(range(1, res + 1))
    targ_list = np.zeros((res, 3))

    for i in range(len(increments)):
        for j in range(3):
            targ_list[i][j] = p_0[j] + (p_02g[j] * increments[i]/res)

    for i in range(len(targ_list)):
        while np.linalg.norm(targ_list[i] - obst_location) < (obst_radius + tol):
            targ_list[i] = targ_list[i] + (targ_list[i] - obst_location) * .01 # pushes target(goal) away from obstacle

    return targ_list



def compute_robot_path(q_init, goal, obst_location, obst_radius):
    # Use arm and your own homework library to compute the path.
    # Return a list of joint configurations (or a NumPy array with one per row).
    # Include q_init first. Use radians for revolute joints and meters for prismatic joints.
    # TODO: implement your method here.
    # Save the initial row with q_s.append(q_init.copy()); use q = q_init.copy() to work.
    # Store each configuration using q_s.append(q.copy()).
    K = .25*np.array([[1, 0, 0],
                     [0, 1, 0],
                     [0, 0, 1]])
    t_list = path_pusher(q_init, goal, obst_location, obst_radius, tol = obst_radius)
    target_list = np.array([arm.fk(q_init)[:3,3]])
    target_list = np.append(target_list, t_list, axis = 0)
    q_s = np.array([q_init])
    q_prev = q_init
    for targ in target_list:
        qf, error_f, iters, converged, q_hist, qdot_hist = arm.ik_position(
            target = targ, 
            q0 = q_prev, 
            method = "pinv",
            K = K,
            max_iter = 10,
            debug = True)
        
        q_s = np.append(q_s, q_hist, axis = 0)
        q_prev = qf
    return q_s




if __name__ == "__main__":
    # These values are for your own testing. The instructor will also use other cases.
    from byu_robomanip.visualization import VizScene

    q_0 = np.zeros(arm.n)
    goal = np.array([1.0, 2.0, 4.0])
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
