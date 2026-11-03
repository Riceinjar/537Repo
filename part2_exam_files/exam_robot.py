"""Define your robot here, then run this file to check its appearance."""

import numpy as np
from byu_robomanip import kinematics as kin
import time



dh = [[np.pi/2, 4, 0, np.pi/2],
      [np.pi/6, 0, 0, np.pi/2],
      [0, 4, 0, np.pi/2],
      [np.pi/6, 0, 2, np.pi/2]]


arm = kin.SerialArm(dh)


if __name__ == "__main__":
    # This preview runs only when you run exam_robot.py directly.
    from byu_robomanip.visualization import VizScene

    viz = VizScene()
    viz.add_arm(arm, draw_frames=True, gripper_scale=1, label_axes=True)
#     viz.update(qs=[np.zeros(arm.n).tolist()])
    
#     q = [0, 0, 0, 0]
#     target = np.array([3,3,3])
#     # target = arm.fk(q)[:3,3]
#     K = .2*np.array([[1, 0, 0],
#                 [0, 1, 0],
#                 [0, 0, 1]])
#     qf, error_f, iters, converged, q_hist, qdot_hist = arm.ik_position(
#         target = target, 
#         q0 = q, 
#         method = "pinv",
#         K = K,
#         max_iter = 100,
#         debug = True)
#     viz.add_marker(target, radius = .5)  
#     for q in q_hist:
#       viz.update(qs=[q], poss=[target])
#       time.sleep(.02)

    viz.update(qs=[qf], poss=[target])
    viz.hold()
