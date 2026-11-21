"""
dynamics Module - Contains code for:
- Dynamic SerialArm class
- RNE Algorithm
- Euler - Lagrange formulation

John Morrell, Jan 28 2022
Tarnarmour@gmail.com

modified by:
Marc Killpack, October 25, 2022
               Nov. 20, 2023
"""

import numpy as np
from byu_robomanip.kinematics import SerialArm


class SerialArmDyn(SerialArm):
    """
    SerialArmDyn class represents serial arms with dynamic properties and is used to calculate forces, torques, accelerations,
    joint forces, etc. using the Newton-Euler and Euler-Lagrange formulations. It inherits from the previously defined kinematic
    robot arm class "SerialArm".
    """

    def __init__(
        self,
        dh,
        jt=None,
        base=np.eye(4),
        tip=np.eye(4),
        joint_limits=None,
        mass=None, # list of masses for each link
        r_com= None, 
        link_inertia=None,
        motor_inertia=None,
        joint_damping=None,
    ):

        SerialArm.__init__(self, dh, jt, base, tip, joint_limits)
        self.mass = mass
        self.r_com = r_com
        self.link_inertia = link_inertia
        self.motor_inertia = motor_inertia
        if joint_damping is None:
            self.B = np.zeros((self.n, self.n))
        else:
            self.B = np.diag(joint_damping)

    def rne(
        self,
        q,
        qd,
        qdd,
        Wext=np.zeros((6,)),
        g=np.zeros((3,)),
        omega_base=np.zeros((3,)),
        alpha_base=np.zeros((3,)),
        v_base=np.zeros((3,)),
        acc_base=np.zeros((3,)),
    ):
        """
        tau, W = RNE(q, qd, qdd):
        returns the torque in each joint (and the full wrench at each joint) given the joint configuration, velocity, and accelerations
        Args:
            q: Joint positions.
            qd: Joint velocities.
            qdd: Joint accelerations.
            Wext: External tip wrench, expressed in the tip frame.
            g: Physical gravitational acceleration expressed in frame 0. For
                example, the HW08 downward acceleration is [0, -9.81, 0].

        Returns:
            tau: Generalized joint forces.
            W: Joint wrenches, with column i expressed in link frame i.

        We start with the velocity and acceleration of the base frame, v0 and a0, and the joint positions, joint velocities,
        and joint accelerations (q, qd, qdd).

        For each joint, we find the new angular velocity, w_i = w_(i-1) + z * qdot_(i-1)
        v_i = v_(i-1) + w_i x r_(i-1, com_i)


        if motor inertia is None, we don't consider it. Solve for now without motor inertia. The solution will provide code for motor inertia as well.
        """

        # TODO: Implement the recursive Newton-Euler dynamics calculation.
        # HW08 student task


        #################################################################### OLD ############################################
        # ############# forward pass, find omega, alpha, a_com for each link       
        # ## parameters initializing 
        # Z_im1N0 = (self.base[:3,:3]).T[2] # third column of R_im1N0
        # r_Eim1_Ei_Ni = self.base[:3,:3].T @ self.base[:3,3]
        # r_Eim1_COMi_Ni = r_Eim1_Ei_Ni * 1/2 # I don't have this distance so, just going to make do here.
        # omega_im1Nim1 = omega_base
        # alpha_im1Nim1 = alpha_base
        # v_Eim1Nim1 = v_base
        # a_Eim1Nim1 = acc_base


        # for i in range(1, self.n + 1): # iterate from 1 to n
        #     ## i specific parameters
        #     I_COMiNi = self.link_inertia[i-1]
        #     R_im1Ni = (self.fk(q, (i-1, i))[:3,:3]).T
        #     R_0Ni = (self.fk(q, i)[:3,:3]).T

        #     ## calculation
        #     omega_iNi  = R_im1Ni @ omega_im1Nim1 + R_0Ni @ Z_im1N0 * qd[i-1] 
        #     alpha_iNi = R_im1Ni @ alpha_im1Nim1 + R_0Ni @ Z_im1N0 * qdd[i-1] + np.cross(omega_iNi, R_0Ni) @ Z_im1N0 * qd[i-1] 
        #     v_COMiNi = R_im1Ni @ v_Eim1Nim1 + np.cross(omega_iNi, r_Eim1_COMi_Ni)
        #     v_EiNi = R_im1Ni @ v_Eim1Nim1 + np.cross(omega_iNi, r_Eim1_Ei_Ni)
        #     a_COMiNi = R_im1Ni @ a_Eim1Nim1 + np.cross(alpha_iNi, r_Eim1_COMi_Ni) + np.cross(omega_iNi, np.cross(omega_iNi, r_Eim1_COMi_Ni))
        #     a_EiNi = R_im1Ni @ a_Eim1Nim1 + np.cross(alpha_iNi, r_Eim1_Ei_Ni) + np.cross(omega_iNi, np.cross(omega_iNi, r_Eim1_Ei_Ni))

        #     ## update parameters
        #     Z_im1N0 = (self.fk(q, i-1)[:3,:3]).T[2] # gives 3rd column of R_im1N0
        #     r_Eim1_Ei_Ni = R_im1Ni @ self.fk(q, (i-1, i))[:3, 3]
        #     r_Eim1_COMi_Ni = r_Eim1_Ei_Ni - self.r_com[i-1]
        #     omega_im1Nim1 = omega_iNi
        #     alpha_im1Nim1 = alpha_iNi
        #     v_Eim1Nim1 = v_EiNi
        #     a_Eim1Nim1 = a_EiNi


        #     ## append lists
        #     omega.append(omega_iNi)
        #     alpha.append(alpha_iNi)
        #     v_COM.append(v_COMiNi)
        #     v_E.append(v_EiNi)
        #     a_COM.append(a_COMiNi)
        #     a_E.append(a_EiNi)


        # ############# backward pass, find f and tau for each joint
        # ## parameters initializing
        # R_np1Nn = self.tip[:3, :3]
        # f_ip1Ni = R_np1Nn @ Wext[:3] # first would be for end effector
        # tau_ip1Ni = R_np1Nn @ Wext[3:] # first would be for end effector
        # r_Eim1_COMi_Ni = self.tip[:3,3] * 1/2  # again just making do for this
        # r_Ei_COMi_Ni = -self.tip[:3,3] - r_Eim1_COMi_Ni


        # for i in range(self.n, 0, -1): # iterate from n to 1
        #     ## i specific parameters
        #     I_COMiNi = self.link_inertia[i-1]
        #     R_im1Ni = (self.fk(q, (i-1, i))[:3,:3]).T
        #     R_0Ni = (self.fk(q, i)[:3,:3]).T

        #     ## calculation
        #     f_iNi  = -self.mass[i-1] * R_0Ni @ g - f_ip1Ni + self.mass[i-1] @ a_COM[i-1]
        #     tau_iNi = -tau_ip1Ni - np.cross(f_ip1Ni, r_Ei_COMi_Ni) - np.cross(f_ip1Ni, r_Eim1_COMi_Ni) + I_COMiNi @ alpha[i-1] + np.cross(omega[i-1], I_COMiNi @ omega[i-1])
            
        #     ## update parameters
        #     f_ip1Ni = f_iNi
        #     tau_ip1Ni = tau_iNi
        #     r_Ei_COMi_Ni = self.r_com[i-1]
        #     r_Eim1_COMi_Ni = (self.fk(q, (i-1,i))[:3,:3]).T @ self.fk(q, (i-1,i))[:3,3] - r_Ei_COMi_Ni

        #     ## append lists
        #     f.insert(0, f_iNi)
        #     tau.insert(0, tau_iNi)
        #################################################################### OLD ############################################





        #### Initialization
        omega = [] # omegas for links 1 through n, in frames 1 through n
        alpha = []
        v = [] # velocities at joints
        v_COM = [] # velocities at COM of link
        a = [] 
        a_COM = []
        tau = np.zeros((self.n,)) # 1xn array that holds the torque values for each joint
        Wrenches = np.zeros((6, self.n)) # 6xn array that holds the "external" forces and moments applied to each joint.
        R = []
        R0 = []
        zaxes = []
        r = [] # from frame i-1 to frame i, in frame i
        r_COM = self.r_com # from frame i to COM of body i, in frame i

        ## Only one call to self.fk per joint is better. 
        for i in range(self.n): 
            T = self.fk(q, (i, i+1)) 
            R_i = T[:3, :3]
            p = T[:3, 3]
            R.append(R_i)
            r.append(R_i.T @ p)
            R0.append(self.fk(q, i+1)[:3, :3])
            zaxes.append(R_i.T[0:3, 2])
            

        #### Forward Pass
        omega_prev = omega_base # initial base ang velocity
        alpha_prev = alpha_base
        v_prev = v_base
        a_prev = acc_base
        for i in range(self.n): # iterates for values joint/link 1 to joint/link n
            if self.jt[i] != "r": raise NotImplementedError("Yeah so not sure that this rne() method of SerialArmDyn works for non-revolute joints")
            omega.append(
                R[i].T @ omega_prev + zaxes[i] * qd[i]
            )  
            alpha.append(
                R[i].T @ alpha_prev + zaxes[i] * qdd[i] + np.cross(omega[i], zaxes[i]) * qd[i]
            )
            v.append(
                R[i].T @ v_prev + np.cross(omega[i], r[i])
            )
            v_COM.append(
                R[i].T @ v_prev + np.cross(omega[i], r[i]+r_COM[i])
            )
            a.append(
                R[i].T @ a_prev + np.cross(alpha[i], r[i]) + np.cross(omega[i], np.cross(omega[i], r[i]))
            )
            a_COM.append(
                R[i].T @ a_prev + np.cross(alpha[i], r[i]+r_COM[i]) + np.cross(omega[i], np.cross(omega[i], r[i]+r_COM[i]))
            )

            omega_prev = omega[i]
            alpha_prev = alpha[i]
            v_prev = v[i]
            a_prev = a[i]

        #### Backward Pass
        f_prev = self.tip[:3,:3]@Wext[:3]
        moment_prev = self.tip[:3,:3]@Wext[3:]
        for i in range(self.n-1, -1, -1): # iterates from joint/link n down to joint/link 1
            f = self.mass[i] * (a_COM[i] - R0[i].T @ g) + f_prev
            moment = (  + moment_prev 
                        - np.cross(f, r[i] + r_COM[i])
                        + np.cross(f_prev, r_COM[i]) 
                        + self.link_inertia[i] @ alpha[i] 
                        + np.cross(omega[i], (self.link_inertia[i] @ omega[i]))
                        )
            Wrenches[:3, i] = f 
            Wrenches[3:, i] = moment
            f_prev = R[i] @ f
            moment_prev = R[i] @ moment
   

        for i in range(self.n):
            tau[i] = zaxes[i] @ Wrenches[3:, i] # need portion of moment in direction of the joint q
        return tau, Wrenches
        raise NotImplementedError("Complete SerialArmDyn.rne for HW08")




    def get_M(self, q):
        """Return the numerical joint-space mass matrix M(q)."""
        # TODO: Compute the numerical joint-space mass matrix M(q).
        # HW08 student task
        M = np.zeros((self.n, self.n))
        for i in range(self.n):
            qdd = np.zeros((self.n,))
            qdd[i] = 1
            tau, _ = self.rne(q, np.zeros((self.n,)), qdd)
            M[:,i] = tau
        return M
        raise NotImplementedError("Complete SerialArmDyn.get_M for HW08")

    def get_C(self, q, qd):
        """Return the Coriolis/centrifugal vector C(q, qd) @ qd.

        Unlike the symbolic HW10 ``C`` callable, this method does not return
        the Coriolis matrix itself.
        """
        # TODO: Compute the numerical Coriolis/centrifugal vector C(q, qd) @ qd.
        # HW08 student task
        C_qd, _ = self.rne(q, qd, np.zeros((self.n,)))
        return C_qd
        raise NotImplementedError("Complete SerialArmDyn.get_C for HW08")

    def get_G(self, q, g):
        """Return the gravity generalized-force vector for acceleration ``g``.

        ``g`` is the physical acceleration vector expressed in frame 0, not
        the positive potential-energy vector used by the symbolic HW10 model.
        """
        # TODO: Compute the numerical gravity generalized-force vector G(q).
        # HW08 student task
        G, _ = self.rne(q, np.zeros((self.n,)), np.zeros((self.n,)), g=g) # default arg for Wext is zeros

        return G
        raise NotImplementedError("Complete SerialArmDyn.get_G for HW08")


if __name__ == "__main__":

    ## this just gives an example of how to define a robot, this is a planar 3R robot.
    dh = [[0, 0, 0.4, 0], [0, 0, 0.4, 0], [0, 0, 0.4, 0]]

    joint_type = ["r", "r", "r"]

    link_masses = [1, 1, 1]

    # defining three different centers of mass, one for each link
    r_coms = [np.array([-0.2, 0, 0]), np.array([-0.2, 0, 0]), np.array([-0.2, 0, 0])]

    link_inertias = []
    for i in range(len(joint_type)):
        iner = 0.01
        # this inertia tensor is only defined as having Izz non-zero
        link_inertias.append(np.array([[0, 0, 0], [0, 0, 0], [0, 0, iner]]))

    arm = SerialArmDyn(
        dh, jt=joint_type, mass=link_masses, r_com=r_coms, link_inertia=link_inertias
    )

    # once implemented, you can call arm.RNE and it should work.
    q = [np.pi / 4.0] * 3
    qd = [np.pi / 6.0, -np.pi / 4.0, np.pi / 3.0]
    qdd = [-np.pi / 6.0, np.pi / 3.0, np.pi / 6.0]
    arm.rne(q, qd, qdd, g=np.array([0, -9.81, 0]))
