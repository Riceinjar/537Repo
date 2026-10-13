"""Explore each joint's contribution to tip velocity after completing HW05.

Run from the repository root:
    python examples/hw05/velocity_kinematics_example.py

Choose Linear/Angular checkboxes to isolate individual contributions. Change
the signed joint rates to compare actual velocity contributions with unit-rate
Jacobian columns. Sky-blue straight arrows show linear velocity, and green circular
arrows show angular velocity. Thicker blue/vermilion selected-total arrows use
the Okabe-Ito palette and sum checked contributions
in each column independently. Use the Position tab to set q without advancing
time, then return to Velocity to change rates and selections.
"""

import numpy as np

from byu_robomanip import kinematics as kin
from byu_robomanip import transforms as tr
from byu_robomanip.visualization import ArmPlayer


def main():
    # Same six-revolute-joint arm as the introductory lecture example.
    a_len, d_len = 0.5, 0.35
    dh = [
        [0, d_len, 0.0, -np.pi / 2],
        [0, 0, a_len, 0],
        [np.pi / 2, 0, 0, np.pi / 2],
        [np.pi / 2, 2 * d_len, 0, -np.pi / 2],
        [0, 0, 0, np.pi / 2],
        [0, 2 * d_len, 0, 0],
    ]
    arm = kin.SerialArm(dh, tip=tr.se3(R=tr.roty(-np.pi / 2)))
    ArmPlayer(
        arm,
        show_velocity_contributions=True,
        qd=np.ones(arm.n),  # rad/s for revolute joints, m/s for prismatic joints
        linear_scale=0.5,
        angular_scale=0.15,
    )


if __name__ == "__main__":
    main()
