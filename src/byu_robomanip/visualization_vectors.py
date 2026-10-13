"""Reusable world-frame vector glyphs and a joint-velocity overlay.

The glyphs know nothing about robot kinematics or physical units. Their scale
maps the supplied vector magnitude to a length (straight arrow) or radius
(circular arrow) in scene coordinates.
"""

import numpy as np
import pyqtgraph.opengl as gl
from pyqtgraph.opengl.GLGraphicsItem import GLGraphicsItem

# Okabe-Ito Color Universal Design palette: https://jfly.uni-koeln.de/color/
# Totals also use thicker strokes; arrow shape identifies linear/angular data.
LINEAR_VELOCITY_COLOR = (86 / 255, 180 / 255, 233 / 255, 1.0)  # sky blue
ANGULAR_VELOCITY_COLOR = (0.0, 158 / 255, 115 / 255, 1.0)  # bluish green
LINEAR_TOTAL_COLOR = (0.0, 114 / 255, 178 / 255, 1.0)  # blue
ANGULAR_TOTAL_COLOR = (213 / 255, 94 / 255, 0.0, 1.0)  # vermilion


def _finite_vector(value, size, name):
    array = np.asarray(value, dtype=float)
    if array.shape != (size,) or not np.isfinite(array).all():
        raise ValueError(f"{name} must be a finite vector with shape ({size},)")
    return array.copy()


def _positive_scale(value):
    value = float(value)
    if not np.isfinite(value) or value <= 0:
        raise ValueError("scale must be finite and positive")
    return value


def _normal_basis(direction):
    """Return two unit vectors with u cross v = direction."""
    reference = np.eye(3)[np.argmin(np.abs(direction))]
    u = np.cross(reference, direction)
    u /= np.linalg.norm(u)
    return u, np.cross(direction, u)


class ArrowViz:
    """An updatable 3D arrow at ``pos``, with length ``scale * ||vector||``.

    Add ``item`` to a GLViewWidget, or use ``VizScene.add_arrow``. All inputs
    are in world coordinates. A zero vector hides the entire glyph, including
    its label, without losing the requested visibility.
    """

    def __init__(
        self, vector, pos=(0, 0, 0), scale=1.0, color=LINEAR_VELOCITY_COLOR, label=None
    ):
        self.item = GLGraphicsItem()
        self.shaft = gl.GLLinePlotItem(
            parentItem=self.item,
            width=3,
            antialias=True,
            color=color,
            glOptions="opaque",
        )
        self.head = gl.GLMeshItem(
            parentItem=self.item, color=color, smooth=False, computeNormals=False
        )
        self.label = (
            gl.GLTextItem(parentItem=self.item, text=label, color=(0, 0, 0))
            if label is not None
            else None
        )
        self._visible = True
        self.vector = _finite_vector(vector, 3, "vector")
        self.pos = _finite_vector(pos, 3, "pos")
        self.scale = _positive_scale(scale)
        self.update()

    def set_visible(self, visible):
        self._visible = bool(visible)
        self.item.setVisible(self._visible and np.linalg.norm(self.vector) > 0)

    def update(self, vector=None, pos=None, scale=None):
        vector = self.vector if vector is None else _finite_vector(vector, 3, "vector")
        pos = self.pos if pos is None else _finite_vector(pos, 3, "pos")
        scale = self.scale if scale is None else _positive_scale(scale)
        self.vector, self.pos, self.scale = vector, pos, scale
        magnitude = np.linalg.norm(vector)
        self.set_visible(self._visible)
        if magnitude == 0:
            return
        direction = vector / magnitude
        length = scale * magnitude
        endpoint = pos + direction * length
        self.shaft.setData(pos=np.array([pos, endpoint]))
        self._set_head(endpoint, direction, min(0.08, 0.2 * length))

    def _set_head(self, endpoint, direction, length):
        u, v = _normal_basis(direction)
        angles = np.linspace(0, 2 * np.pi, 13)
        ring = (
            endpoint
            - length * direction
            + 0.4 * length * (np.cos(angles)[:, None] * u + np.sin(angles)[:, None] * v)
        )
        vertices = np.array(
            [[ring[i], ring[i + 1], endpoint] for i in range(len(ring) - 1)]
        )
        self.head.setMeshData(vertexes=vertices)
        if self.label is not None:
            self.label.setData(pos=endpoint + length * direction)


class CircularArrowViz(ArrowViz):
    """A 300-degree arrow around an axis, oriented by the right-hand rule.

    ``vector`` gives the signed axis and magnitude; ``pos`` is the center.
    Radius is ``scale * ||vector||``. Magnitude changes radius, while sweep
    remains fixed. Reversing the vector reverses circulation. ``phase`` (in
    radians) separates arrowheads when several glyphs share an axis.
    """

    def __init__(
        self,
        vector,
        pos=(0, 0, 0),
        scale=0.25,
        color=ANGULAR_VELOCITY_COLOR,
        label=None,
        phase=0.0,
    ):
        self.phase = float(phase)
        if not np.isfinite(self.phase):
            raise ValueError("phase must be finite")
        super().__init__(vector, pos, scale, color, label)

    def update(self, vector=None, pos=None, scale=None):
        vector = self.vector if vector is None else _finite_vector(vector, 3, "vector")
        pos = self.pos if pos is None else _finite_vector(pos, 3, "pos")
        scale = self.scale if scale is None else _positive_scale(scale)
        self.vector, self.pos, self.scale = vector, pos, scale
        magnitude = np.linalg.norm(vector)
        self.set_visible(self._visible)
        if magnitude == 0:
            return
        direction = vector / magnitude
        u, v = _normal_basis(direction)
        angles = np.linspace(self.phase, self.phase + 5 * np.pi / 3, 65)
        radius = scale * magnitude
        points = pos + radius * (
            np.cos(angles)[:, None] * u + np.sin(angles)[:, None] * v
        )
        tangent = -np.sin(angles[-1]) * u + np.cos(angles[-1]) * v
        self.shaft.setData(pos=points)
        self._set_head(points[-1], tangent, min(0.08, 0.25 * radius))


class JointVelocityViz:
    """Per-joint tip velocities, separated from player widgets and state.

    Uses the arm's geometric Jacobian with ``base=True, tip=True``: rows 0:3
    are linear velocity and rows 3:6 are angular velocity, in the world frame.
    Column i is multiplied by qd[i]. Selection affects visibility and the
    displayed selected totals, without changing state or joint contributions.
    """

    def __init__(self, arm, view, linear_scale=1.0, angular_scale=0.25):
        self.arm = arm
        self.view = view
        self.linear_scale = _positive_scale(linear_scale)
        self.angular_scale = _positive_scale(angular_scale)
        self.linear_selected = np.zeros(arm.n, dtype=bool)
        self.angular_selected = np.zeros(arm.n, dtype=bool)
        self.linear = np.zeros((3, arm.n))
        self.angular = np.zeros((3, arm.n))
        self.tip_pos = np.zeros(3)
        self.linear_total = np.zeros(3)
        self.angular_total = np.zeros(3)
        self.total_enabled = False
        self.linear_arrows = []
        self.angular_arrows = []
        self.enabled = False
        for i in range(arm.n):
            linear = ArrowViz(np.zeros(3), label=f"v{i + 1}")
            angular = CircularArrowViz(
                np.zeros(3), label=f"w{i + 1}", phase=2 * np.pi * i / arm.n
            )
            self.linear_arrows.append(linear)
            self.angular_arrows.append(angular)
            view.addItem(linear.item)
            view.addItem(angular.item)
        self.linear_total_arrow = ArrowViz(
            np.zeros(3), color=LINEAR_TOTAL_COLOR, label="v selected"
        )
        self.angular_total_arrow = CircularArrowViz(
            np.zeros(3), color=ANGULAR_TOTAL_COLOR, label="w selected", phase=np.pi
        )
        for arrow in (self.linear_total_arrow, self.angular_total_arrow):
            arrow.shaft.setData(width=6)
            view.addItem(arrow.item)

    def update(self, q, qd):
        q = _finite_vector(q, self.arm.n, "q")
        qd = _finite_vector(qd, self.arm.n, "qd")
        jacobian = np.asarray(self.arm.jacob(q, base=True, tip=True), dtype=float)
        if jacobian.shape != (6, self.arm.n) or not np.isfinite(jacobian).all():
            raise ValueError("arm.jacob must return a finite array with shape (6, n)")
        self.tip_pos = self.arm.fk(q, base=True, tip=True)[:3, 3]
        self.linear = jacobian[:3] * qd[None, :]
        self.angular = jacobian[3:] * qd[None, :]
        for i, (linear, angular) in enumerate(
            zip(self.linear_arrows, self.angular_arrows)
        ):
            linear.update(self.linear[:, i], self.tip_pos, self.linear_scale)
            angular.update(self.angular[:, i], self.tip_pos, self.angular_scale)
        self.refresh_visibility()

    def refresh_visibility(self):
        for i, (linear, angular) in enumerate(
            zip(self.linear_arrows, self.angular_arrows)
        ):
            linear.set_visible(self.enabled and self.linear_selected[i])
            angular.set_visible(self.enabled and self.angular_selected[i])
        self.linear_total = self.linear[:, self.linear_selected].sum(axis=1)
        self.angular_total = self.angular[:, self.angular_selected].sum(axis=1)
        self.linear_total_arrow.update(
            self.linear_total, self.tip_pos, self.linear_scale
        )
        self.angular_total_arrow.update(
            self.angular_total, self.tip_pos, self.angular_scale
        )
        self.linear_total_arrow.set_visible(self.enabled and self.total_enabled)
        self.angular_total_arrow.set_visible(self.enabled and self.total_enabled)

    def remove(self):
        """Detach this overlay from the view without affecting the robot."""
        for arrow in self.linear_arrows + self.angular_arrows:
            self.view.removeItem(arrow.item)
        self.view.removeItem(self.linear_total_arrow.item)
        self.view.removeItem(self.angular_total_arrow.item)
