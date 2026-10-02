# %% [markdown]
# # Homework 4
# * Complete the HW04 sections in the cumulative byu_robomanip package.
# * Implement the sections that convert between Euler angles, Axis/Angle,
#   Quaternions, and rotation matrices, all of which represent SO(3).
# * Run the provided checks and reason through what each operation means.

# %%
import importlib
from byu_robomanip import transforms as tr
import numpy as np
import sympy as sp
from IPython.display import display

np.set_printoptions(precision=4, suppress=True)
importlib.reload(tr)


# %% [markdown]
# # Problem 1:

# Check your implementation of rpy, axis, and quaternion. For the given "R_test", you should get the following for RPY, axis/angle, and quaternion represenations:
# $$[\phi, \theta, \psi] = \left[\begin{matrix}1.041\\0.147\\0.5299\end{matrix}\right]$$
# $$[\theta, r] = \left[\begin{matrix}1.13\\0.3574\\0.3574\\0.8629\end{matrix}\right] $$
# $$\mathcal{Q} = \left[\begin{matrix}0.8446\\0.1913\\0.1913\\0.4619\end{matrix}\right] $$


#%%
phi, theta, psi = sp.symbols("phi, theta, psi")
display(tr.rotz(psi, symbolic=True) @ tr.roty(theta, symbolic=True) @ tr.rotx(phi, symbolic=True))


# %%
R_test = (
    tr.rotx(45 * np.pi / 180.0)
    @ tr.rotz(45 * np.pi / 180.0)
    @ tr.roty(45 * np.pi / 180.0)
)
# print('R_test:\n', R_test)

print("Roll, pitch, yaw angles:")
print(tr.R2rpy(R_test))

print("axis/angle representation:")
print(tr.R2axis(R_test))

print("quaternion representation:")
print(tr.R2quat(R_test))


# %% [markdown]
# Now check that rotation about XZY of $\psi=0.787$, $\theta=0.787$, $\phi=0.787$ gives the
# following:
# $$R =  \left[\begin{matrix}0.4984 & -0.7082 & 0.5\\0.8546 & 0.4984 & -0.1459\\-0.1459 & 0.5 & 0.8537\end{matrix}\right]$$

# the rotation for axis/angle of $\frac{\pi}{2}$ about the $[1, 0, 0]$ axis should give the following rotation matrix:
# $$R =  \left[\begin{matrix}1.0 & 0 & 0\\0 & 0.0 & -1.0\\0 & 1.0 & 0.0\end{matrix}\right]$$

# finally, a quaternion of $\mathcal{Q}=[0.707, 0.707, 0.0, 0.0]$ (assuming an order of $[\nu, \mathbf{\eta}]$) will give the rotation matrix:
# $$R = \left[\begin{matrix}0.9994 & 0 & 0\\0 & -0.000302 & -0.9997\\0 & 0.9997 & -0.000302\end{matrix}\right]$$

# %%
# this should be identical to R_test earlier in our code
R = tr.euler2R(0.787, 0.787, 0.787, "xzy")
print("R for euler2R was:")
print(R)

# this is just a rotation about the x-axis by pi/2. So checking it should be easy for you.
R = tr.axis2R(3.14 / 2, np.array([1, 0, 0]))
print("R for axis2R was:")
print(R)

# quaternions are harder to understand, but after looking at the resulting R matrix,
# can you tell what axis this is quaternion is rotating about?
R = tr.quat2R(np.array([0.707, 0.707, 0.0, 0.0]))
print("R for quaternion2R was:")
print(R)


#%%