# %% [markdown]
# # Homework 5
# * Complete the HW05-labeled SerialArm.jacob method in the cumulative package.
# * Use it to calculate the geometric Jacobian for any robot based on a DH parameter description.
# * After completion, check that your answers match the the answers for the Jacobian test below.

# %%
from byu_robomanip import kinematics as kin
from byu_robomanip import transforms as tr
from byu_robomanip.visualization import VizScene
import numpy as np

np.set_printoptions(precision=4, suppress=True)


# %% [markdown]
# # Problem 1:

# Check your implementation of "jacob" using the DH parameters shown below. For the given vectors of q's, you should get the following:
# $$ q = \left[\begin{matrix}0 \\ 0 \\ 0 \\0 \end{matrix}\right]$$
# $$ J = \left[\begin{matrix}0 & 0 & 0 & 0\\0.5 & 0 & 0.1 & -1.0\\0 & 0.3 & 0 & 0\\0 & 0 & 0 & 0\\0 & -1.0 & 0 & 0\\1.0 & 0 & 1.0 & 0\end{matrix}\right]$$

# While for $$ q = \left[\begin{matrix}\pi/4 \\ \pi/4 \\ \pi/4 \\ 0.10 \end{matrix}\right]$$
# $$ J = \left[\begin{matrix}-0.3121 & -0.1707 & -0.1 & 0.8536\\0.3121 & -0.1707 & 0.1 & -0.1464\\0 & 0.2414 & -6.939 \cdot 10^{-18} & 0.5\\0 & 0.7071 & -0.5 & 0\\0 & -0.7071 & -0.5 & 0\\1.0 & 0 & 0.7071 & 0\end{matrix}\right] $$


# %%
dh = [
    [0, 0, 0.2, np.pi / 2.0],
    [0, 0, 0.2, -np.pi / 2.0],
    [0, 0, 0.1, np.pi / 2.0],
    [0, 0, 0.0, 0.0],
]

# An example of defining joint types which we may not have done yet.
# The 4th joint, and 4th row of the DH parameters correspond to a prismatic joint.
jt_types = ["r", "r", "r", "p"]

# notice how "jt_types" can be passed as an argument into "SerialArm"
arm = kin.SerialArm(dh, jt=jt_types)

# defining two different sets of joint angles
q_set1 = [0, 0, 0, 0]
q_set2 = [np.pi / 4, np.pi / 4, np.pi / 4, 0.10]

# calculating two different jacobians for the two different joint configurations.
J1 = arm.jacob(q_set1)
J2 = arm.jacob(q_set2)

print("from first set of q's, J is:")
print(J1)

print("now look at the configuration of the arm for q_set1 to understand J")

# making a visualization
viz = VizScene()

# adding a SerialArm to the visualization, and telling it to draw the joint frames.
viz.add_arm(arm, draw_frames=True)

# setting the joint angles to draw
viz.update(qs=[q_set1])

viz.hold()


print("from second set of q's, J is:")
print(J2)

# updating position of the arm in visualization
viz = VizScene()
viz.add_arm(arm, draw_frames=True)
viz.update(qs=[q_set2])

print("now look at the configuration of the arm for q_set2 to understand J")
viz.hold()



# %%
# hw5 prob 2b
dh = [
    [0, 3.0, 0, -np.pi/2],
    [0, 0, 3.0, 0],]
jt = ["r", "r"]
arm = kin.SerialArm(dh, jt)

# defining two different sets of joint angles
q_set1 = [0, 0]
q_set2 = [np.pi / 4, -np.pi / 2]

# calculating two different jacobians for the two different joint configurations.
J1 = arm.jacob(q_set1)
J2 = arm.jacob(q_set2)

print("from first set of q's, J is:")
print(J1)

print("now look at the configuration of the arm for q_set1 to understand J")

# making a visualization
viz = VizScene()

# adding a SerialArm to the visualization, and telling it to draw the joint frames.
viz.add_arm(arm, draw_frames=True)

# setting the joint angles to draw
viz.update(qs=[q_set1])

viz.hold()


print("from second set of q's, J is:")
print(J2)

# updating position of the arm in visualization
viz = VizScene()
viz.add_arm(arm, draw_frames=True)
viz.update(qs=[q_set2])

print("now look at the configuration of the arm for q_set2 to understand J")
viz.hold()


# %%
#hw5 prob 4
dh = [
    [0,          0,     0, -np.pi / 2],
    [0,       0.154,    0,  np.pi / 2],
    [0,       0.250,    0,  0],
    [-np.pi / 2, 0,     0, -np.pi / 2],
    [-np.pi / 2, 0,     0,  np.pi / 2],
    [np.pi / 2, 0.263,  0,  0],
]
T_tip = np.eye(4)
T_tip[:3, :3] = tr.roty(-np.pi/2)
jt = ["r", "r", "p", "r", "r", "r"]
arm = kin.SerialArm(dh, jt=jt, tip = T_tip)
q_set = [0., 0, 0, 0, 0, 0]
J = arm.jacob(q_set, tip = True)
viz = VizScene()
viz.add_arm(arm, draw_frames=True)
viz.update(qs=[q_set])
viz.hold()

print("\n Jacobian when all angles are 0: \n", arm.jacob(q_set, tip= True))
q_set[2] = .1
print("\n Jacobian when prismatic joint moves by 0.1 meters: \n", arm.jacob(q_set, tip=True))


# %%
