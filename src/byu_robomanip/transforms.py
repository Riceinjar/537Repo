"""
Transforms Module - Contains code to describe SO(3) and SE(3)

Key for HW 04
"""

import numpy as np
from numpy import sin, cos, sqrt
from numpy.typing import NDArray
from byu_robomanip.utility import clean_rotation_matrix


## 2D Rotations
def rot2(theta: float) -> NDArray:
    """
    R = rot2(th)

    :param float theta: angle of rotation (rad)
    :return R: 2x2 numpy array representing rotation in 2D by theta
    """
    # TODO: Implement the 2D SO(2) rotation matrix.
    # HW02 student task

    R = np.matrix([[np.cos(theta), -np.sin(theta)], 
                   [np.sin(theta), np.cos(theta)]])

    return R
    raise NotImplementedError("Complete rot2 for HW02")


## 3D Rotations
def rotx(theta: float) -> NDArray:
    """
    R = rotx(theta)

    :param float theta: angle of rotation (rad)
    :return R: 3x3 numpy array representing rotation about x-axis by amount theta
    """
    # TODO: Implement the 3D rotation matrix about the x-axis.
    # HW02 student task
    R = np.matrix([[1, 0, 0], 
                [0, np.cos(theta), -np.sin(theta)],
                [0, np.sin(theta), np.cos(theta)]])

    return R
    raise NotImplementedError("Complete rotx for HW02")


def roty(theta: float) -> NDArray:
    """
    R = roty(theta)

    :param float theta: angle of rotation (rad)
    :return R: 3x3 numpy array representing rotation about y-axis by amount theta
    """
    # TODO: Implement the 3D rotation matrix about the y-axis.
    # HW02 student task
    R = np.matrix([[np.cos(theta), 0, np.sin(theta)], 
                [0, 1, 0],
                [-np.sin(theta), 0, np.cos(theta)]])
    return R
    raise NotImplementedError("Complete roty for HW02")


def rotz(theta: float) -> NDArray:
    """
    R = rotz(theta)

    :param float theta: angle of rotation (rad)
    :return R: 3x3 numpy array representing rotation about z-axis by amount theta
    """
    # TODO: Implement the 3D rotation matrix about the z-axis.
    # HW02 student task

    R = np.matrix([[np.cos(theta), -np.sin(theta), 0], 
                [np.sin(theta), np.cos(theta), 0],
                [0, 0, 1]])
    return R
    raise NotImplementedError("Complete rotz for HW02")


# inverse of rotation matrix
def rot_inv(R: NDArray) -> NDArray:
    """
    R_inv = rot_inv(R)

    :param NDArray R: 2x2 or 3x3 numpy array representing a proper rotation matrix
    :return R_inv: 2x2 or 3x3 inverse of the input rotation matrix
    """
    # TODO: Implement matrix inversion for SO(2) and SO(3).
    # HW02 student task
    R_inv  = R.T
    return R_inv
    raise NotImplementedError("Complete rot_inv for HW02")


def se3(R: NDArray = np.eye(3), p: NDArray = np.zeros(3)) -> NDArray:
    """
    T = se3(R, p)

    Creates a 4x4 homogeneous transformation matrix "T" from a 3x3 rotation matrix
    and a position vector.

    :param NDArray R: 3x3 numpy array representing orientation, defaults to identity.
    :param NDArray p: numpy array representing position, defaults to [0, 0, 0].
    :return T: 4x4 numpy array representing the homogeneous transform.
    """

    # TODO: Construct a 4x4 homogeneous transform from a rotation matrix and translation vector.
    # HW03 student task

    T = np.zeros((4,4))
    T[0:3, 0:3] = R
    T[0:3, -1] = p
    T[-1, -1] = 1
    return T
    raise NotImplementedError("Complete se3 for HW03")


def inv(T: NDArray) -> NDArray:
    """
    T_inv = inv(T)

    Returns the inverse transform to T.

    :param NDArray T: 4x4 homogeneous transformation matrix
    :return T_inv: 4x4 numpy array that is the inverse to T so that T @ T_inv = I
    """

    # TODO: Implement the inverse of a 4x4 homogeneous transform.
    # HW03 student task
    R = T[0:3, 0:3]
    P = T[0:3, -1]
    T_inv = np.eye(4)
    T_inv[0:3, 0:3] = R.T
    T_inv[0:3, -1] = -R.T@P
    return T_inv
    raise NotImplementedError("Complete inv for HW03")


def R2rpy(R: NDArray) -> NDArray:
    """
    rpy = R2rpy(R)

    Returns the roll-pitch-yaw representation of the SO3 rotation matrix.

    :param NDArray R: 3x3 Numpy array for any rotation.
    :return rpy: Numpy array, containing [roll, pitch, yaw] coordinates (in radians).
    """

    # TODO: Implement conversion from a rotation matrix to roll-pitch-yaw angles.
    # HW04 student task

    raise NotImplementedError("Complete R2rpy for HW04")


def R2axis(R: NDArray) -> NDArray:
    """
    axis_angle = R2axis(R)

    Returns an axis angle representation of a SO(3) rotation matrix.

    :param NDArray R: 3x3 rotation matrix.
    :return axis_angle: numpy array containing the axis angle representation
        in the form: [angle, rx, ry, rz]
    """

    # see equation (2.27) and (2.28) on pg. 54, using functions like "np.acos," "np.sin," etc.

    # TODO: Implement conversion from a rotation matrix to axis-angle form.
    # HW04 student task

    raise NotImplementedError("Complete R2axis for HW04")


def axis2R(angle: float, axis: NDArray) -> NDArray:
    """
    R = axis2R(angle, axis)

    Returns an SO3 object of the rotation specified by the axis-angle.

    :param float angle: the angle to rotate about the axis (in radians).
    :param NDArray axis: components of the unit axis about which to rotate as
        a numpy array [rx, ry, rz].
    :return R: 3x3 numpy array representing the rotation matrix.
    """

    # follow formula in book, see equation (2.25) on pg. 54
    # TODO: Implement conversion from axis-angle form to a rotation matrix.
    # HW04 student task

    raise NotImplementedError("Complete axis2R for HW04")


def R2quat(R: NDArray) -> NDArray:
    """
    quaternion = R2quat(R)

    Returns a quaternion representation of pose.

    :param NDArray R: 3x3 rotation matrix.
    :return quaternion: numpy array for the quaternion representation of pose in
        the format [nu, ex, ey, ez]
    """

    # TODO: Implement conversion from a rotation matrix to quaternion form.
    # HW04 student task

    raise NotImplementedError("Complete R2quat for HW04")


def quat2R(q: NDArray) -> NDArray:
    """
    R = quat2R(q)

    Returns a 3x3 rotation matrix from a quaternion.

    :param NDArray q: [nu, ex, ey, ez ] - defining the quaternion.
    :return R: numpy array, 3x3 rotation matrix.
    """

    # TODO: Implement conversion from quaternion form to a rotation matrix.
    # HW04 student task

    raise NotImplementedError("Complete quat2R for HW04")


def euler2R(th1: float, th2: float, th3: float, order: str = "xyz") -> NDArray:
    """
    R = euler2R(th1, th2, th3, order='xyz')

    Returns a 3x3 rotation matrix as specified by the euler angles, we assume in all cases
    that these are defined about the "current axis," which is why there are only 12 versions
    (instead of the 24 possiblities noted in the course slides).

    :param float th1: angle of rotation about 1st axis (rad)
    :param float th2: angle of rotation about 2nd axis (rad)
    :param float th3: angle of rotation about 3rd axis (rad)
    :param str order: specifies the euler rotation to use, for example 'xyx', 'zyz', etc.
    :return R: 3x3 numpy array, the rotation matrix.
    """

    # TODO: Implement conversion from Euler angles to a rotation matrix.
    # HW04 student task

    raise NotImplementedError("Complete euler2R for HW04")
