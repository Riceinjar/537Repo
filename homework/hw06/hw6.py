#%%
import numpy as np
from byu_robomanip import transforms as tr
from byu_robomanip import kinematics as kin
from byu_robomanip.visualization import VizScene as viz

q = [np.pi/4, np.pi/4]
a1 = 1
a2 = 1
dh = [[0, 0, a1, -np.pi/2],
      [0, 0, a2, 0]]
jt = ["r", "r"]

# baseFrame = np.array([[1, 0, 0, 0],
#                       [0, 0, -1, 0],
#                       [0, 1, 0, 1],
#                       [0, 0, 0, 1]])
arm = kin.SerialArm(dh, jt)

#%%
Jacob = arm.jacob(q, index = 2)
print("Jacob = \n", Jacob)
scene = viz()
scene.add_arm(arm, draw_frames = True, label_axes=True)
scene.update(qs=[q])
scene.hold()


#%%
q_list = np.array([[0, np.pi/4],
                   [0, np.pi/2],
                   [np.pi/4, np.pi/4],
                   [0, 0],
                   [0, 0]])
f_list = np.array([[-1, 0, 0],
                   [-1, 0, 0],
                   [-1, -1, 0],
                   [0, 0, 1],
                   [1, 0, 0]])

for i in range(len(q_list)):
    W = np.append(f_list[i], np.array([0, 0, 0]))
    print(f"\nW_{i+1}= \n", W)
    J = arm.jacob(q_list[i])
    tau = J.T @ W
    tau_motors = -tau
    print(f"tau_motors_jt{i+1} = \n", tau_motors)


# %%
#hw6 part 2

dh = [
    [0,        0.2, 0,   -np.pi / 2],
    [0,        0,   0.2,  0],
    [np.pi / 2, 0,   0,    np.pi / 2],
    [np.pi / 2, 0.4, 0,   -np.pi / 2],
    [0,        0,   0,    np.pi / 2],
    [0,        0.4, 0,    0],
]
jt = ["r", "r", "r", "r", "r", "r"]
arm = kin.SerialArm(dh, jt=jt)

scene = viz()
scene.add_arm(arm, draw_frames = True, label_axes=True)
q = [-np.pi/4, 0, -np.pi/4, np.pi/4, np.pi/2, np.pi/4]
goal = arm.fk(q)[:3, 3]
scene.add_marker(goal)
scene.update(qs=[q], poss = [goal])
scene.hold()





# %%
#hw6 part 3
import numpy as np
from byu_robomanip import transforms as tr
from byu_robomanip import kinematics as kin
from byu_robomanip.visualization import VizScene as viz
dh = [
    [0,        0.2, 0,   -np.pi / 2],
    [0,        0,   0.2,  0],
    [np.pi / 2, 0,   0,    np.pi / 2],
    [np.pi / 2, 0.4, 0,   -np.pi / 2],
    [0,        0,   0,    np.pi / 2],
    [0,        0.4, 0,    0],
]
jt = ["r", "r", "r", "r", "r", "r"]
arm = kin.SerialArm(dh, jt=jt)

scene = viz()
scene.add_arm(arm, draw_frames = True, label_axes=True)

q_list = [[0, 0, 0, 0, 0, 0],
          [np.pi/4, np.pi/4, np.pi/4, np.pi/4, np.pi/4, np.pi/4]
          ]

goal_list = np.array([[-0.149,  0.364,  1.03],
                [-0.171, -0.682, -0.192],
                [ 0.822, -0.1878, 0.533],
                [-0.336,  0.095,  0.931],
                [ 0.335,  0.368,  0.88]
                ])
scene.add_marker([0, 0, 0])
# scene.update(qs=[q_list[0]], poss = [goal_list[0]])
# scene.hold(10)
for q_i in range(len(q_list)):
    for g in range(len(goal_list)):
        K = np.array([[1, 0, 0],
                      [0, 1, 0],
                      [0, 0, 1]])
        qf, error_f, iters, converged = arm.ik_position(
            target = goal_list[g], 
            q0 = q_list[q_i], 
            method = "J_T",
            K = K,
            max_iter = 100)
        print(f"\n qf for method J_T, target{g}, q{q_i} = ", qf)
        scene.update(qs=[qf], poss = [goal_list[g]])
        scene.hold(10)

scene.close_viz

# %%
