#%%
%load_ext autoreload
%autoreload 2
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

arm = SerialArm(dh_params, tip = T_6_tool)
q = [0., 0, 0, 0, 0, 0]
J = arm.jacob(q) # jacobian 6 in 0
print(f"Jacobian 6 in 0: \n", J)
T = arm.fk(q) # T 6 in 0

############ Doing it in two steps, first shifting J_6in0 to J_6in6, and then to J_tipintip
R_0in6 = T[:3, :3].T
Z1 = arm.Z_shift(R_0in6) # no translation vec needed here, as it's staying at point 6. This gives J_6in6.
R_6intip = T_6_tool[:3, :3].T
p_6totip = T_6_tool[:3, 3] # this gives p from 6 to tooltip, in frame 6 (use 'i' in z_shift)
Z2 = arm.Z_shift(R_6intip, p_6totip) # Z 6intip, from 6 to tip
J_shifted = Z2@Z1@J

########### Trying to do it in one step
# R = T[:3, :3]  # R tip in 0, or from 0 to tip
# R = R.T # R 0 in tip
# p = T_6_tool[:3, 3]    # P from 6 to tip expressed in 0
# p = R @ p   # P from 6 to tip expressed in tip
# Z = arm.Z_shift(R = R, p = p, p_frame = "j")
# J_shifted = Z @ J

print(f"Shifted Jacobian: \n", J_shifted)

A = np.array([
    [0,      -0.4518, -0.02,  0,   0,   0],
    [0.4518,  0,      0,      0,   0,   0],
    [0.15,   -1.0318, -1.0318, 0,  -0.6, 0],
    [-1,      0,      0,     -1,   0,  -1],
    [0,      -1,     -1,      0,  -1,   0],
    [0,       0,      0,      0,   0,   0]])
print(f"Correctly shifted Jacobian according to hw solution: \n", A)


# arm = SerialArm(dh_params, tip = tip)
# ArmPlayer(arm, q = q)
# %%
