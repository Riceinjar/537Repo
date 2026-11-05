#%%
import numpy as np
from byu_robomanip.visualization import ArmPlayer
from byu_robomanip.kinematics import SerialArm
from byu_robomanip import transforms as tr

# these DH parameters are based on solutions from HW 3, if you
# pick a different set that still describes the robots accurately,
# that's fine.
a_len = 0.5
d_len = 0.35

dh_part_a = [[0, d_len, 0.0, np.pi / 2.0], [0, 0, a_len, 0], [0, 0, a_len, 0]]

dh_part_b = [
    [0, d_len, 0.0, -np.pi / 2.0],
    [0, 0, a_len, 0],
    [np.pi / 2.0, 0, 0, np.pi / 2.0],
    [np.pi / 2.0, d_len * 2, 0, -np.pi / 2.0],
    [0, 0, 0, np.pi / 2],
    [0, d_len * 2, 0, 0],
]

tipb = tr.se3(tr.roty(-np.pi/2))
tipa = np.eye(4)

#%%
q_part_a = [0., np.pi/2, 0]
q_part_b = [0., 0, -np.pi/6, 0, np.pi/4, 0]
arm = SerialArm(dh_part_b, tip = tipb)
J = arm.jacob(q_part_b)
print("the Jacobian's rank is: ", np.linalg.matrix_rank(J))
print("the Jacobian's condition # is : ", np.linalg.cond(J))
ArmPlayer(arm, q = q_part_b)


# %%

dh_params = [
    [0, 0.0, 0.0, np.pi/2],
    [0, 0.0, 0.4318, 0.0],
    [0, 0.15, 0.02, -np.pi/2],
    [0, 0.4318, 0.0, np.pi/2],
    [0, 0.0, 0.0, -np.pi/2],
    [0, 0.4, 0.0, 0.0]]
T_6_tool = np.array([
    [0, 0, 1, 0],
    [0, 1, 0, 0],
    [-1, 0, 0, 0.2],
    [0, 0, 0, 1]])
tip = T_6_tool

arm = SerialArm(dh_params, tip = tip)
q = [0., 0, 0, 0, 0, 0]
J = arm.jacob(q)
R = tip[:3, :3].T
p = tip[:3, 3]
print(f"Jacobian at EE in Frame 0: \n", J)
Z = arm.Z_shift(R = R, p = p, p_frame = "i")
J_shifted = Z @ J
print(f"Jacobian at Tooltip in Frame Tooltip: \n", J_shifted)

# arm = SerialArm(dh_params, tip = tip)
# ArmPlayer(arm, q = q)
# %%
