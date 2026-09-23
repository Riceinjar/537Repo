import numpy as np
from numpy.typing import NDArray
from pathlib import Path
import struct
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSlider,
    QPushButton,
    QSizePolicy,
    QLabel,
    QLineEdit,
    QSpacerItem,
)
from PySide6.QtCore import QCoreApplication, QEvent, Qt
import pyqtgraph.opengl as gl
from pyqtgraph.opengl import shaders as gl_shaders
from pyqtgraph.opengl.items.GLLinePlotItem import GLLinePlotItem
from pyqtgraph.opengl.items import GLTextItem
import pyqtgraph as pg
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.widgets import Slider
from time import perf_counter, sleep, time
import signal

red = np.array([0.8, 0, 0, 1])
green = np.array([0, 0.7, 0, 1])
blue = np.array([0, 0, 0.8, 1])
dark_red = np.array([0.3, 0, 0, 1])
dark_green = np.array([0, 0.3, 0, 1])
dark_blue = np.array([0, 0, 0.3, 1])
white = np.array([1, 1, 1, 1])
grey = np.array([0.3, 0.3, 0.3, 1])
yellow = np.array([223.0 / 255.0, 238.0 / 255.0, 95.0 / 255.0, 1.0])

# Set this to "shaded" to immediately return to PyQtGraph's standard shader.
ARM_SHADER = "byu_lighter_shaded"


def _register_lighter_arm_shader() -> None:
    """Register the optional arm shader with a higher ambient-light level."""
    gl_shaders.ShaderProgram(
        ARM_SHADER,
        [
            gl_shaders.VertexShader(
                """
                uniform mat4 u_mvp;
                uniform mat3 u_normal;
                attribute vec4 a_position;
                attribute vec3 a_normal;
                attribute vec4 a_color;
                varying vec4 v_color;
                varying vec3 v_normal;
                void main() {
                    v_normal = normalize(u_normal * a_normal);
                    v_color = a_color;
                    gl_Position = u_mvp * a_position;
                }
                """
            ),
            gl_shaders.FragmentShader(
                """
                #ifdef GL_ES
                precision mediump float;
                #endif
                varying vec4 v_color;
                varying vec3 v_normal;
                void main() {
                    float light = max(dot(v_normal, normalize(vec3(1.0, -1.0, -1.0))), 0.0);
                    float brightness = 0.3 + 0.7 * light;
                    gl_FragColor = vec4(v_color.rgb * brightness, v_color.a);
                }
                """
            ),
        ],
    )


_register_lighter_arm_shader()


def _reset_opengl_shader_caches() -> None:
    """Reset PyQtGraph shader handles before creating a new GL context.

    PyQtGraph 0.14 stores shader programs at module/class scope even though
    OpenGL program handles belong to a particular context.  This matters in a
    long-lived Jupyter kernel: closing one ``VizScene`` destroys its context,
    but the next scene otherwise reuses the old handles.  Text items continue
    to render while mesh and line items fail with OpenGL attribute errors.
    """
    GLLinePlotItem._shaderProgram = None
    for shader_program in gl_shaders.ShaderProgram.names.values():
        shader_program.prog = None


class TransformMPL:

    def __init__(self, A, ax=None):
        self.A = A

    def update(self, A):
        self.A = A

    def show(self):
        plt.show()


class PlanarMPL:

    def __init__(
        self,
        arm,
        q0: None | list = None,
        trace: bool = False,
        ax: None | plt.Axes = None,
    ):
        self.arm = arm
        if ax is not None:
            fig = ax.figure
            flag = True
        else:
            fig, ax = plt.subplots()
            flag = False
        self.fig: plt.Figure = fig
        self.ax: plt.Axes = ax
        self.n = arm.n
        self.reach = arm.reach
        if not flag:
            plt.axis("equal")
            plt.xlim([-arm.reach * 1.5, arm.reach * 1.5])
            plt.ylim([-arm.reach * 1.5, arm.reach * 1.5])

        self.joints: list[Circle] = []
        self.links: list[plt.Line2D] = []
        self.joints.append(self.ax.add_patch(Circle([0, 0], 0.15, color=[0, 0, 0, 1])))

        if q0 is None:
            q0 = [0] * self.n
        self.q0 = q0
        for i in range(self.n):
            A = self.arm.fk(q0, index=i)
            A_next = self.arm.fk(q0, index=i + 1)

            if i != 0:
                joint = Circle(A[0:2, 3], 0.1, color=[0, 0, 0, 1])
                self.joints.append(self.ax.add_patch(joint))
            (link,) = self.ax.plot(
                [A[0, 3], A_next[0, 3]],
                [A[1, 3], A_next[1, 3]],
                lw=3,
                color=[0, 0, 0, 1],
            )
            self.links.append(link)

        end_effector = Circle(A_next[0:2, 3], 0.1, color=[0.5, 0, 0, 1])
        self.joints.append(self.ax.add_patch(end_effector))

        self.do_trace = trace
        if trace:
            self.start_trace(q0)

    def start_trace(self, q0):
        self.xs: list[list[float]] = []
        self.ys: list[list[float]] = []
        self.traces: list[plt.Line2D] = []
        for i in range(self.n):
            pos = self.arm.fk(q0, index=i + 1)[0:2, 3]
            C = [0, 0, 0, 0.4]
            C[i] = 0.5
            (line,) = self.ax.plot(pos[0], pos[1], lw=1, color=C)
            self.xs.append([pos[0]])
            self.ys.append([pos[1]])
            self.traces.append(line)

    def update(self, q):

        for i in range(self.n):
            A = self.arm.fk(q, index=i)
            A_next = self.arm.fk(q, index=i + 1)

            if i != 0:
                self.joints[i].set_center(A[0:2, 3])

            self.links[i].set_xdata([A[0, 3], A_next[0, 3]])
            self.links[i].set_ydata([A[1, 3], A_next[1, 3]])
        self.joints[-1].set_center(A_next[0:2, 3])

        if self.do_trace:
            for i in range(self.n):
                pos = self.arm.fk(q, index=i + 1)[0:2, 3]
                self.xs[i].append(pos[0])
                self.ys[i].append(pos[1])
                self.traces[i].set_xdata(self.xs[i])
                self.traces[i].set_ydata(self.ys[i])

        plt.pause(0.02)

    def show(self):
        plt.show()

    def set_bounds(self, xbound=None, ybound=None):
        print("finish me")

    def play(self):
        # clear all the line plots
        if self.do_trace:
            self.do_trace = False
            for i in range(self.n):
                self.ax.lines.remove(self.traces[i])
                # NOTE: This might be what you want if line above doesn't work - Mat
                # self.ax.remove(self.traces[i])

        # move to the default position
        self.update(self.q0)

        # resize and create slider bars
        self.ax.set_position([0, 0, 0.75, 1])
        # NOTE: I think these changes work and isolate the plot. If not, revert to the original code - Mat
        self.ax.axis("equal")
        self.ax.set_xlim([-self.arm.reach * 1.5, self.arm.reach * 1.5])
        self.ax.set_ylim([-self.arm.reach * 1.5, self.arm.reach * 1.5])
        # plt.axis('equal')
        # plt.xlim([-self.arm.reach * 1.5, self.arm.reach * 1.5])
        # plt.ylim([-self.arm.reach * 1.5, self.arm.reach * 1.5])

        max_h = 0.2
        min_h = 0.8 / self.n
        h = min(max_h, min_h)
        self.sliders: list[Slider] = []
        self.gui_axes: list[plt.Axes] = []

        def get_text_from_A(A):
            pos = np.around(A[0:2, 3], decimals=2)
            theta = np.around(np.arctan2(A[1, 0], A[0, 0]), decimals=2)

            s = "Pos: [" + str(pos[0]) + ", " + str(pos[1]) + "]\n"
            s += "Angle: [" + str(theta) + "]\n"

            return s

        text_pos = [-self.reach * 1.35, self.reach * 1.15]
        self.text_box = self.ax.text(
            text_pos[0], text_pos[1], get_text_from_A(self.arm.fk(self.q0))
        )

        def slider_update(val):
            q = self.q0
            for i in range(self.n):
                q[i] = self.sliders[i].val
            self.update(q)
            self.text_box.set_text(get_text_from_A(self.arm.fk(q)))
            plt.draw()

        for i in range(self.n):
            self.gui_axes.append(self.fig.add_subplot())
            self.gui_axes[i].set_position([0.775, 0.8 - h * i, 0.15, h - 0.05])
            self.sliders.append(
                Slider(
                    ax=self.gui_axes[i],
                    label=str(i),
                    valmin=-np.pi,
                    valmax=np.pi,
                    valinit=0,
                    orientation="horizontal",
                )
            )
            self.sliders[i].on_changed(slider_update)

        # plt.show()


class VizScene:
    """The viz scene holds all the 3d objects to be plotted. This includes arms (which are GLMeshObjects), transforms
    (which are plots or quiver type things), scatter points, and lines."""

    def __init__(self):
        # A notebook may construct a new scene after an earlier scene was
        # closed, while the QApplication itself remains alive.
        _reset_opengl_shader_caches()
        self._closed = False
        self.arms: list[ArmMeshObject] = []
        self.frames: list[FrameViz] = []
        self.axes: list[AxisViz] = []
        self.markers: list[gl.GLMeshItem] = []
        self.obstacles: list[gl.GLMeshItem] = []
        self.range = 5

        if QApplication.instance() is None:
            self.app: QApplication = QApplication([])
        else:
            self.app = QApplication.instance()
        self.window = gl.GLViewWidget()
        self.window.setWindowTitle("Robot Visualization 2: The Sequel")

        screen_size = self.app.primaryScreen().size()
        screen_w, screen_h = screen_size.width(), screen_size.height()
        fraction_of_screen = 0.7  # could be a function parameter
        x = int(screen_w * (1 - fraction_of_screen)) // 2
        y = int(screen_h * (1 - fraction_of_screen)) // 2
        win_w = int(screen_w * fraction_of_screen)
        win_h = int(screen_h * fraction_of_screen)
        self.window.setGeometry(x, y, win_w, win_h)

        self.grid = gl.GLGridItem(color=(0, 0, 0, 76.5))
        self.grid.scale(1, 1, 1)
        self.window.addItem(self.grid)
        self.window.setCameraPosition(distance=self.range)
        self.window.setBackgroundColor("w")
        self.window.show()
        self.window.raise_()
        self.window.opts["center"] = pg.Vector(0, 0, 0)

        self.app.processEvents()

    def show_grid(self):
        """Show the reference grid for this scene."""
        self.grid.show()
        self.app.processEvents()

    def hide_grid(self):
        """Hide the reference grid for this scene."""
        self.grid.hide()
        self.app.processEvents()

    def add_arm(
        self,
        arm,
        draw_frames=False,
        label_axes=False,
        joint_colors=None,
        gripper_stl=None,
        gripper_offset=None,
        gripper_scale=1.0,
        q=None,
    ):
        """
        :param SerialArm arm: The arm to be visualized.
        :param bool draw_frames: If True, the frames of the arm will be drawn.
        :param bool | list label_axes: (bool or n+3 list of bools for each joint
           plus end effector, base, and tip frames). If True and draw_frames is
           True, the axes of the frames will be labeled. When frames are on top
           of each other, the labels can be hard to see and you can turn them
           off individually by passing in a list of bools. By default, the base
           and tip frames are not labeled if arm.base and arm.tip are identity
           matrices to avoid label clutter.
        :param list joint_colors: (list of colors for each joint, each color is
            a list of 4 for [r,g,b,1]). The color of the joints. If None, rotary
            joints are red and prismatic joints are green.
        :param str | pathlib.Path | None gripper_stl: Path to an ASCII or binary
            STL mesh to display in place of the default end effector.
        :param NDArray | None gripper_offset: 4x4 homogeneous transform from the
            arm tip frame to the STL mesh frame.
        :param float gripper_scale: Additional positive scale for STL coordinates.
        :param Iterable[float] | None q: Initial joint configuration. If None,
            the arm is displayed at its zero configuration.
        """
        a = ArmMeshObject(
            arm,
            q0=q,
            draw_frames=draw_frames,
            label_axes=label_axes,
            joint_colors=joint_colors,
            gripper_stl=gripper_stl,
            gripper_offset=gripper_offset,
            gripper_scale=gripper_scale,
        )
        self.arms.append(a)
        a.update()
        self.window.addItem(a.mesh_object)

        def draw_axes(frame: FrameViz, label: bool):
            for axis in frame.axes:
                self.window.addItem(axis)
            if label:
                for txt in frame.axis_labels:
                    self.window.addItem(txt)

        if draw_frames:
            draw_axes(a.frame_objects[0], a.label_base)
            for frame, label in zip(a.frame_objects[1:-1], a.label_axes[1:-1]):
                draw_axes(frame, label)
            draw_axes(a.frame_objects[-1], a.label_tip)

        if 2 * arm.reach > self.range:
            self.range = 2 * arm.reach
            self.window.setCameraPosition(distance=self.range)

        self.app.processEvents()

    def remove_arm(self, index: None | int = None):
        """
        :param int index: The index of the arm to be removed based on the order
            they were added. If None, all arms are removed.
        """

        def remove_axes(frame: FrameViz, label: bool):
            for axis in frame.axes:
                self.window.removeItem(axis)
            if label:
                for txt in frame.axis_labels:
                    self.window.removeItem(txt)

        if index is None:
            for arm in self.arms:
                self.window.removeItem(arm.mesh_object)
                if arm.draw_frames:
                    remove_axes(arm.frame_objects[0], arm.label_base)
                    for frame, label in zip(
                        arm.frame_objects[1:-1], arm.label_axes[1:-1]
                    ):
                        remove_axes(frame, label)
                    remove_axes(arm.frame_objects[-1], arm.label_tip)
            self.arms.clear()
        elif isinstance(index, int):
            arm = self.arms[index]
            self.window.removeItem(arm.mesh_object)
            if arm.draw_frames:
                for frame, label in zip(arm.frame_objects, arm.label_axes):
                    for axis in frame.axes:
                        self.window.removeItem(axis)
                    if label:
                        for txt in frame.axis_labels:
                            self.window.removeItem(txt)
            self.arms.pop(arm)
        else:
            raise TypeError("Invalid index type")
        self.app.processEvents()

    def add_frame(self, A: NDArray, label: str = None, axes_label: str = None):
        """
        :param np.ndarray A: The 4x4 transformation matrix of the frame to be visualized.
        :param str|None label: The label of the origin of the frame.
        :param str|None axes_label: The label to append to the axes of the frame,
            e.g. 'b' would display 'x_b', 'y_b', 'z_b'.
        """
        self.frames.append(FrameViz(A, frame_label=label, axes_label=axes_label))
        self.window.addItem(self.frames[-1].axes[0])
        self.window.addItem(self.frames[-1].axes[1])
        self.window.addItem(self.frames[-1].axes[2])
        if label is not None:
            self.window.addItem(self.frames[-1].frame_label)
        if axes_label is not None:
            for txt in self.frames[-1].axis_labels:
                self.window.addItem(txt)

            # this was from the old version of text rendering. I don't think it's needed, but
            # seems to assign a windwo to render to, so I don't know for sure. - Killpack
            # self.frames[-1].label.setGLViewWidget(self.window)

        if 2 * np.linalg.norm(A[:3, 3]) > self.range:
            self.range = 2 * np.linalg.norm(A[:3, 3])
            self.window.setCameraPosition(distance=self.range)

        self.app.processEvents()

    def remove_frame(self, index: None | int = None):
        """
        :param int index: The index of the frame to be removed based on the
            order they were added. If None, all frames are removed.
        """
        if index is None:
            for frame in self.frames:
                for axis in frame.axes:
                    self.window.removeItem(axis)
                if frame.frame_label is not None:
                    self.window.removeItem(frame.frame_label)
                if frame.axis_labels is not None:
                    for txt in frame.axis_labels:
                        self.window.removeItem(txt)
            self.frames.clear()
        elif isinstance(index, int):
            for axis in self.frames[index].axes:
                self.window.removeItem(axis)
            if self.frames[index].frame_label is not None:
                self.window.removeItem(self.frames[index].frame_label)
            if self.frames[index].axis_labels is not None:
                for txt in self.frames[index].axis_labels:
                    self.window.removeItem(txt)
            self.frames.pop(index)
        else:
            raise TypeError("Invalid index type")
        self.app.processEvents()

    def add_axis(
        self,
        axis: NDArray,
        pos_offset: NDArray = np.zeros(3),
        scale: float = 1.0,
        label: str | None = None,
    ):
        """
        :param np.ndarray axis: The axis to be visualized relative to global origin
            (the axis is normalized to unit length).
        :param np.ndarray pos_offset: Position offset for the origin of the axis.
        :param int scale: The scale of the axis (length and radius of cylinder).
        :param str|None label: Label placed at the tip of the axis.
        """
        self.axes.append(AxisViz(axis, pos_offset, scale, label=label))
        self.window.addItem(self.axes[-1].axis)
        if label is not None:
            self.window.addItem(self.axes[-1].label)

        self.app.processEvents()

    def remove_axis(self, index=None):
        """
        :param int index: The index of the axis to be removed based on the order
            they were added. If None, all axes are removed.
        """
        if index is None:
            for axis in self.axes:
                self.window.removeItem(axis.axis)
                if axis.label is not None:
                    self.window.removeItem(axis.label)
            self.axes.clear()
        elif isinstance(index, int):
            ax_viz = self.axes[index]
            self.window.removeItem(ax_viz.axis)
            if ax_viz.label is not None:
                self.window.removeItem(ax_viz.label)
            self.axes.pop(index)
        else:
            raise TypeError("Invalid index type")
        self.app.processEvents()

    def add_marker(self, pos, color=green, radius=0.1):
        if not isinstance(pos, (np.ndarray)):
            pos = np.array(pos)

        marker = gl.MeshData.sphere(rows=20, cols=20, radius=radius)

        mesh_marker = gl.GLMeshItem(meshdata=marker, smooth=True, color=color)
        mesh_marker.translate(*pos)

        self.markers.append(mesh_marker)
        self.window.addItem(self.markers[-1])

        if 2 * np.linalg.norm(pos) > self.range:
            self.range = 2 * np.linalg.norm(pos)
            self.window.setCameraPosition(distance=self.range)

        self.app.processEvents()

    def remove_marker(self, index=None):
        if index is None:
            for marker in self.markers:
                self.window.removeItem(marker)
            self.markers = []
        elif isinstance(index, int):
            self.window.removeItem(self.markers[index])
            self.markers.pop(index)
        else:
            raise TypeError("Invalid index type")
        self.app.processEvents()

    def add_obstacle(self, pos, color=yellow, rad=1.0):
        if not isinstance(pos, (np.ndarray)):
            pos = np.array(pos)

        mobst = gl.MeshData.sphere(rows=20, cols=20, radius=rad)

        m1 = gl.GLMeshItem(meshdata=mobst, smooth=True, color=yellow)
        m1.translate(*pos)

        self.obstacles.append(m1)
        self.window.addItem(self.obstacles[-1])

        self.app.processEvents()

    def remove_obstacle(self, index=None):
        if index is None:
            for obstacle in self.obstacles:
                self.window.removeItem(obstacle)
            self.obstacles = []
        elif isinstance(index, int):
            self.window.removeItem(self.obstacles[index])
            self.obstacles.pop(index)
        else:
            raise TypeError("Invalid index type")
        self.app.processEvents()

    def update(self, qs=None, As=None, poss=None):
        """
        :param np.ndarray|list|None qs: list of joint angles for each arm in the
            scene in the order they were added to the scene. If None, arm
            configurations will not change.
        :param list|None As: list of 4x4 transformation matrices for each frame
            in the scene in the order they were added to the scene. If None,
            frame poses will not change.
        :param np.ndarray|list|None poss: list of positions for each marker in
            the scene in the order they were added to the scene. If None, marker
            positions will not change.
        """
        if qs is not None:
            if isinstance(qs[0], (list, tuple, np.ndarray)):
                for i in range(len(self.arms)):
                    self.arms[i].update(qs[i])
            else:
                self.arms[0].update(qs)

        if As is not None:
            if isinstance(As, (list, tuple)):
                for i in range(len(self.frames)):
                    self.frames[i].update(As[i])
            elif len(As.shape) == 3:
                for i in range(len(self.frames)):
                    self.frames[i].update(As[i])
            else:
                self.frames[0].update(As)

        if poss is not None:
            if isinstance(poss, (list, tuple)):
                for i in range(len(self.markers)):
                    if not isinstance(poss[i], (np.ndarray)):
                        pos = np.array(poss[i])
                    else:
                        pos = poss[i]
                    self.markers[i].resetTransform()
                    self.markers[i].translate(*pos)
            else:
                if not isinstance(poss, (np.ndarray)):
                    pos = np.array(poss)
                else:
                    pos = poss
                self.markers[0].resetTransform()
                self.markers[0].translate(*pos)

        self.app.processEvents()
        sleep(0.00001)

    def hold(self, seconds: float | None = None):
        """
        :param float|None seconds: Will keep the window open for this many
            seconds and then will return leaving the window in a usable state.
            If None, the window will stay open until manually closed, at which
            point the VizScene object is no longer usable.
        """
        if seconds is None:
            while self.window.isVisible():
                self.app.processEvents()
        else:
            tstart = time()
            end = tstart + seconds
            while time() < end and self.window.isVisible():
                self.app.processEvents()

        # A user closing the window ends the hold loop. Clean up immediately
        # so a later notebook cell can safely create another VizScene even if
        # it does not retain the old scene object to call close_viz().
        if not self.window.isVisible():
            self.close_viz()

    def wander(self, index=None, q0=None, speed=1e-1, duration=np.inf, accel=5e-4):
        if index is None:
            index = range(len(self.arms))

        tstart = perf_counter()
        t = tstart
        flag = True
        qs = []
        dqs = []

        while t < tstart + duration and self.window.isVisible():
            for i, ind in enumerate(index):
                n = self.arms[ind].n
                if flag:
                    if q0 is None:
                        qs.append(np.zeros((n,)))
                    else:
                        qs.append(q0[i])
                    # dqs.append(np.random.random_sample((n,)) * speed - speed / 2)
                    dqs.append(np.zeros((n,)))

                dqq = np.zeros((n,))
                for j in range(n):
                    s = dqs[i][j] / speed
                    dqq[j] = (
                        dqq[j]
                        + np.random.random_sample((1,)) * accel
                        - accel / 2
                        - accel * s**3
                    )
                dqs[i] = dqs[i] + dqq
                qs[i] = qs[i] + dqs[i]
                self.arms[ind].update(qs[i])

            if flag:
                flag = False
            t = perf_counter()
            self.app.processEvents()

    def add_ellipse(
        self,
        position,
        orientation,
        size,
        scale=1.0,
        color=blue,
        alpha=1.0,
        resolution=50,
        show_edges=True,
        edge_color=None,
        wireframe=False,
    ):
        """
        Add a 3D ellipse to the visualization scene.

        :param np.ndarray position: 3D position of the ellipse center [x, y, z]
        :param np.ndarray orientation: 3x3 rotation matrix defining ellipse orientation
        :param np.ndarray|list size: Ellipse radii in x, y, z directions before rotation [rx, ry, rz]
        :param np.ndarray|list color: RGBA color [r, g, b, a] where values are 0-1
        :param float alpha: Transparency value (0=transparent, 1=opaque), overrides color alpha
        :param int resolution: Number of segments for ellipse smoothness
        :param bool show_edges: If True, show mesh edges for better depth perception
        :param np.ndarray|list|None edge_color: Color for edges. If None, uses darker version of main color
        :param bool wireframe: If True, show only wireframe (no solid surface)
        """
        size = np.array(size) * scale

        # Input validation and conversion
        if not isinstance(position, np.ndarray):
            position = np.array(position)
        if not isinstance(orientation, np.ndarray):
            orientation = np.array(orientation)
        if not isinstance(size, np.ndarray):
            size = np.array(size)
        if not isinstance(color, np.ndarray):
            color = np.array(color, dtype=np.float64)
        else:
            color = color.astype(np.float64)

        # Validate input dimensions
        if position.shape != (3,):
            raise ValueError("Position must be a 3-element array [x, y, z]")
        if orientation.shape != (3, 3):
            raise ValueError("Orientation must be a 3x3 rotation matrix")
        if size.shape != (3,):
            raise ValueError("Size must be a 3-element array [rx, ry, rz]")
        if len(color) not in [3, 4]:
            raise ValueError("Color must be RGB [r,g,b] or RGBA [r,g,b,a] format")

        # Validate size values (must be positive)
        if np.any(size <= 0):
            raise ValueError("All size values (rx, ry, rz) must be positive")

        # Validate alpha range
        if not 0 <= alpha <= 1:
            raise ValueError("Alpha must be between 0 and 1")

        # Ensure color has alpha channel and apply alpha parameter
        if len(color) == 3:
            color = np.append(color, alpha)
        else:
            color[3] = alpha

        # Ensure color is float array for mathematical operations
        color = color.astype(np.float64)

        # Handle edge color
        if edge_color is None:
            # Create darker version of main color for edges
            edge_color = color.copy()
            edge_color[:3] *= 0.3  # Make RGB components darker
            if len(edge_color) == 3:
                edge_color = np.append(edge_color, alpha)
        elif not isinstance(edge_color, np.ndarray):
            edge_color = np.array(edge_color, dtype=np.float64)
            if len(edge_color) == 3:
                edge_color = np.append(edge_color, alpha)
        else:
            edge_color = edge_color.astype(np.float64)
            if len(edge_color) == 3:
                edge_color = np.append(edge_color, alpha)

        # Create ellipse mesh data
        ellipse_mesh = self._create_ellipse_mesh(size, resolution)

        # Apply transformation to mesh vertices directly
        vertices = ellipse_mesh.vertexes()
        transformed_vertices = vertices @ orientation.T + position
        ellipse_mesh.setVertexes(transformed_vertices)

        # Create main mesh item
        if wireframe:
            # Wireframe mode - show only edges
            mesh_item = gl.GLMeshItem(
                meshdata=ellipse_mesh,
                smooth=False,
                color=edge_color,
                drawFaces=False,
                drawEdges=True,
                glOptions="translucent" if alpha < 1.0 else "opaque",
            )
            self.obstacles.append(mesh_item)
            self.window.addItem(mesh_item)
        else:
            # Solid surface mode
            mesh_item = gl.GLMeshItem(
                meshdata=ellipse_mesh,
                smooth=True,
                color=color,
                drawFaces=True,
                drawEdges=show_edges,
                edgeColor=edge_color if show_edges else None,
                glOptions="translucent" if alpha < 1.0 else "opaque",
            )
            self.obstacles.append(mesh_item)
            self.window.addItem(mesh_item)

        # Update camera distance if needed
        if 2 * np.linalg.norm(position) > self.range:
            self.range = 2 * np.linalg.norm(position)
            self.window.setCameraPosition(distance=self.range)

        self.app.processEvents()

    def _create_ellipse_mesh(self, size, resolution):
        """
        Create mesh data for an ellipse with given radii.

        :param np.ndarray size: Ellipse radii [rx, ry, rz]
        :param int resolution: Number of segments for smoothness
        :return: gl.MeshData object
        """
        rx, ry, rz = size

        # Create parametric ellipse surface
        # Using spherical coordinates and scaling by ellipse radii
        phi = np.linspace(0, 2 * np.pi, resolution)  # azimuth angle
        theta = np.linspace(0, np.pi, resolution // 2)  # polar angle

        phi_grid, theta_grid = np.meshgrid(phi, theta)

        # Parametric equations for ellipse (scaled sphere)
        x = rx * np.sin(theta_grid) * np.cos(phi_grid)
        y = ry * np.sin(theta_grid) * np.sin(phi_grid)
        z = rz * np.cos(theta_grid)

        # Flatten arrays for vertices
        vertices = np.column_stack([x.flatten(), y.flatten(), z.flatten()])

        # Create faces (triangulation)
        faces = []
        rows, cols = theta_grid.shape

        for i in range(rows - 1):
            for j in range(cols - 1):
                # Current quad vertices
                v1 = i * cols + j
                v2 = i * cols + (j + 1) % cols
                v3 = (i + 1) * cols + (j + 1) % cols
                v4 = (i + 1) * cols + j

                # Two triangles per quad
                faces.append([v1, v2, v3])
                faces.append([v1, v3, v4])

        # Handle wraparound for last column
        for i in range(rows - 1):
            v1 = i * cols + (cols - 1)
            v2 = i * cols + 0
            v3 = (i + 1) * cols + 0
            v4 = (i + 1) * cols + (cols - 1)

            faces.append([v1, v2, v3])
            faces.append([v1, v3, v4])

        faces = np.array(faces)

        # Create and return mesh data
        mesh = gl.MeshData(vertexes=vertices, faces=faces)
        return mesh

    def remove_ellipse(self, index=None):
        """
        Remove ellipse(s) from the scene. Note: ellipses are stored in the obstacles list.

        :param int|None index: Index of ellipse to remove (based on order added).
                              If None, removes all ellipses. Note this will also remove
                              other obstacles added via add_obstacle().
        """
        # Note: This uses the same remove logic as obstacles since ellipses are stored there
        if index is None:
            for obstacle in self.obstacles:
                self.window.removeItem(obstacle)
            self.obstacles = []
        elif isinstance(index, int):
            self.window.removeItem(self.obstacles[index])
            self.obstacles.pop(index)
        else:
            raise TypeError("Invalid index type")
        self.app.processEvents()

    def close_viz(self):
        """Close this scene and release its OpenGL resources.

        The Qt application is intentionally left running because it may be
        owned by a Jupyter kernel or by another visualization.  Resetting
        PyQtGraph's process-global shader caches makes a later ``VizScene``
        safe after this widget's OpenGL context has been destroyed.
        """
        if self._closed:
            return
        self._closed = True
        self.window.clear()
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(self.window, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        _reset_opengl_shader_caches()


class ArmPlayer:
    def __init__(self, arm, fontsize: int = 14):
        """
        Opens a window with sliders to control the joints of the arm. This is
        blocking code until the window is closed.

        :param SerialArm arm: The arm to be visualized.
        :param int fontsize: The font size of the text in the side panel.
        """
        if QApplication.instance() is None:
            self.app: QApplication = QApplication([])
        else:
            self.app: QApplication = QApplication.instance()

        viz_widget = self._create_vizualization_widget(arm)
        side_panel = self._create_side_panel_layout(arm)

        self.window = self._create_main_window(
            viz_widget, side_panel, fontsize, fraction_of_screen=0.7
        )

        # should this be in constructor? It could be called by user - Mat
        self.run()

    def run(self):
        self.window.show()
        self.window.raise_()
        signal.signal(signal.SIGINT, signal.SIG_DFL)  # kill with ctrl-c
        self.app.exec()

    def _create_main_window(
        self, viz_widget, side_panel_layout, fontsize: int, fraction_of_screen: float
    ):
        window = QMainWindow()
        window.setWindowTitle("Arm Player")

        font = window.font()
        font.setPointSize(fontsize)
        window.setFont(font)

        assert 0 < fraction_of_screen < 1, "fraction_of_screen must be between 0 and 1"
        screen_size = self.app.primaryScreen().size()
        screen_w, screen_h = screen_size.width(), screen_size.height()
        x = int(screen_w * (1 - fraction_of_screen)) // 2
        y = int(screen_h * (1 - fraction_of_screen)) // 2
        win_w = int(screen_w * fraction_of_screen)
        win_h = int(screen_h * fraction_of_screen)
        window.setGeometry(x, y, win_w, win_h)

        main_layout = QHBoxLayout()
        main_layout.addWidget(viz_widget, stretch=3)
        main_layout.addLayout(side_panel_layout, stretch=1)

        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        window.setCentralWidget(main_widget)

        return window

    def _create_vizualization_widget(self, arm):
        viz_widget = gl.GLViewWidget()
        viz_widget.setBackgroundColor("w")
        viz_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        grid = gl.GLGridItem(color=(0, 0, 0, 76.5))
        grid.scale(1, 1, 1)
        viz_widget.addItem(grid)

        self.arm = ArmMeshObject(arm)
        viz_widget.addItem(self.arm.mesh_object)
        return viz_widget

    def _create_side_panel_layout(self, arm):
        self.jt: list[str] = arm.jt
        self.jt_lims = self._get_joint_limits(arm)
        r_scale = 2  # slider increments by 1/2 deg for revelute joints
        p_scale = 100  # slider increments by 1/100 m for prismatic joints
        self.jt_scale = np.array([r_scale if jt == "r" else p_scale for jt in self.jt])

        panel = QVBoxLayout()

        self.sliders: list[QSlider] = []
        self.slider_textboxes: list[QLineEdit] = []
        for i in range(arm.n):
            joint_textbox = self._create_labeled_jt_textbox_layout(i, arm.jt[i])
            joint_slider = self._create_joint_slider_layout(
                self.jt_lims[i], self.jt_scale[i]
            )
            panel.addLayout(joint_textbox, stretch=0)
            panel.addWidget(joint_slider, stretch=0)
            panel.addSpacerItem(
                QSpacerItem(
                    20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
                )
            )
        panel.addSpacerItem(
            QSpacerItem(
                20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
            )
        )

        button = QPushButton()
        button.setText("Randomize")
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        button.pressed.connect(self._button_pressed)
        panel.addWidget(button)
        return panel

    def _get_joint_limits(self, arm):
        default_lim_r = 180  # degrees
        default_lim_p = 1.0  # meters
        if arm.qlim is None:
            jt_lims = np.array(
                [
                    [-default_lim_r if jt == "r" else -default_lim_p for jt in arm.jt],
                    [default_lim_r if jt == "r" else default_lim_p for jt in arm.jt],
                ],
                dtype=np.float64,
            ).T
        else:
            # expecting qlim for 'r' joints to be in radians
            jt_lims = np.array(arm.qlim, dtype=np.float64).T
            mask = [True if jt == "r" else False for jt in arm.jt]
            jt_lims[mask] = np.rad2deg(jt_lims[mask])
        assert jt_lims.shape == (arm.n, 2)
        return jt_lims

    def _create_labeled_jt_textbox_layout(self, idx, jt):
        # joint label
        t1 = QLabel()
        t1.setText(f"Joint {idx + 1}: ")
        t1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # textbox for joint position value
        box = QLineEdit()
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        box.setText("0.0")
        box.editingFinished.connect(self._update_textboxes)
        self.slider_textboxes.append(box)

        # joint units label
        t2 = QLabel()
        if jt == "r":
            t2.setText("(degrees)")
        else:
            t2.setText("(meters)")
        t2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        joint_layout = QHBoxLayout()
        joint_layout.addWidget(t1)
        joint_layout.addWidget(box)
        joint_layout.addWidget(t2)
        return joint_layout

    def _create_joint_slider_layout(self, joint_lims: NDArray, scale: float):
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(*(joint_lims * scale).astype(int))
        s.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        s.valueChanged.connect(self._update_sliders)
        self.sliders.append(s)
        return s

    # NOTE: The following 3 update functions are inefficient because all buttons
    # and sliders are updated when any one of them are changed. Could be optimized
    # by adding unique update functions for each item in the constructor above.
    # - Mat
    def _update_sliders(self):
        qs = np.zeros((self.arm.n,))
        for i, s in enumerate(self.sliders):
            q = s.value() / self.jt_scale[i]
            if self.jt[i] == "r":
                qs[i] = np.deg2rad(q)
            else:
                qs[i] = q
            self.slider_textboxes[i].setText(f"{q}")
        self.arm.update(qs)

    def _update_textboxes(self):
        qs = np.zeros((self.arm.n,))
        for i, b in enumerate(self.slider_textboxes):
            try:  # if the text box is empty or not a number, it will throw an error
                q = float(b.text())
                if q > self.jt_lims[i, 1]:
                    q = self.jt_lims[i, 1]
                elif q < self.jt_lims[i, 0]:
                    q = self.jt_lims[i, 0]
            except:  # if invalid text then just use the current slider value
                q = self.sliders[i].value() / self.jt_scale[i]
            self.sliders[i].setValue(int(q * self.jt_scale[i]))
            if self.jt[i] == "r":
                q = np.deg2rad(q)
            qs[i] = q
        self.arm.update(qs)

    def _button_pressed(self):
        qs = np.empty(self.arm.n)
        for i in range(self.arm.n):
            q = np.random.uniform(*self.jt_lims[i])
            if self.jt[i] == "r":
                qs[i] = np.radians(q)
            else:
                qs[i] = q
            self.sliders[i].setValue(int(q * self.jt_scale[i]))
        self._update_textboxes()


# TODO: add option for scale of joints, links, end-effector, and frames and backpropagate to add_arm
class ArmMeshObject:
    def __init__(
        self,
        arm,
        link_colors=None,
        joint_colors=None,
        q0=None,
        draw_frames=False,
        label_axes=False,
        gripper_stl=None,
        gripper_offset=None,
        gripper_scale=1.0,
    ):
        self.arm = arm
        self.n = arm.n
        self.dh = arm.dh
        self.draw_frames = draw_frames
        self.gripper_stl = gripper_stl
        self.gripper_scale = gripper_scale
        self.gripper_offset = (
            np.eye(4)
            if gripper_offset is None
            else np.asarray(gripper_offset, dtype=float).copy()
        )
        if self.gripper_offset.shape != (4, 4):
            raise ValueError("gripper_offset must be a 4x4 homogeneous transform")
        self.label_base = np.not_equal(self.arm.base, np.eye(4)).any() and label_axes
        self.label_tip = np.not_equal(self.arm.tip, np.eye(4)).any() and label_axes
        if isinstance(label_axes, bool):
            self.label_axes = np.array(
                [self.label_base, *[label_axes] * (self.n + 1), self.label_tip],
                dtype=bool,
            )
        else:
            self.label_axes = np.array([*label_axes], dtype=bool)
            self.label_base = self.label_axes[0]
            self.label_tip = self.label_axes[-1]
        assert len(self.label_axes) == self.n + 3

        if q0 is None:
            q0 = np.zeros(self.n)
        self.q0 = q0

        self.link_objects: list[LinkMeshObject] = []
        self.frame_objects: list[FrameViz] = []

        if link_colors is None:
            link_colors = [blue] * self.n

        if joint_colors is None:
            joint_colors = [red if jt == "r" else green for jt in arm.jt]

        dh_array = np.array(self.dh)
        arm_scale = np.max([np.max(dh_array[0:, 1:3]), 0.3])
        frame_scale = 1.5
        ee_scale = 2.0

        self.frame_objects.append(
            FrameViz(scale=arm_scale * frame_scale, axes_label="b")
        )
        self.frame_objects.append(
            FrameViz(scale=arm_scale * frame_scale, axes_label="0")
        )

        link_width = np.max([arm_scale, 0.10]) * 0.20
        joint_width = np.max([arm_scale, 0.10]) * 0.30
        joint_height = np.max([arm_scale, 0.10]) * 0.70

        for i in range(self.n):
            self.link_objects.append(
                LinkMeshObject(
                    self.dh[i],
                    jt=arm.jt[i],
                    link_width=link_width,
                    joint_width=joint_width,
                    joint_height=joint_height,
                    link_color=link_colors[i],
                    joint_color=joint_colors[i],
                )
            )
            self.frame_objects.append(
                FrameViz(scale=arm_scale * frame_scale, axes_label=f"{i+1}")
            )

        if self.gripper_stl is None:
            self.ee_object = EEMeshObject(scale=arm_scale * ee_scale)
        else:
            self.ee_object = GripperSTLMeshObject(
                self.gripper_stl,
                self.gripper_offset,
                scale=arm_scale * self.gripper_scale,
            )
        self.frame_objects.append(
            FrameViz(scale=arm_scale * frame_scale, axes_label="t")
        )

        self.mesh = np.zeros((0, 3, 3))
        self.colors = np.zeros((0, 3, 4))

        self.set_mesh(q0)

        self.mesh_object = gl.GLMeshItem(
            vertexes=self.mesh,
            vertexColors=self.colors,
            drawEdges=False,
            computeNormals=True,
            shader=ARM_SHADER,
        )

    def update(self, q=None):
        # it's highly possible that this could be done by using .translate and .rotate functions
        # to simplify the complexity of recalculating every vertex ever time. But "translate" and
        # "rotate" may both be relative motion (meaning you have to use resetTransform too)...
        # - Killpack
        # Mat: translate() and rotate() are relative to the global origin, so you
        # would need to use resetTransform, do rotate() first, then translate()
        if q is None:
            q = self.q0
        self.set_mesh(q)
        self.mesh_object.setMeshData(vertexes=self.mesh, vertexColors=self.colors)
        if self.draw_frames:
            self.update_frames(q)

    def update_frames(self, q):
        A = self.arm.fk(q, 0, base=True, tip=False)
        self.frame_objects[1].update(A)
        for i, frame_object in enumerate(self.frame_objects[2:-1]):
            A = self.arm.fk(q, i + 1, base=True, tip=False)
            frame_object.update(A)
        A = self.arm.fk(q, self.n, base=True, tip=True)
        self.frame_objects[-1].update(A)

    def set_mesh(self, q):
        meshes = []
        colors = []
        for i in range(self.n):
            A = self.arm.fk(q, i + 1, base=True, tip=False)
            R = A[:3, :3]
            p = A[:3, 3]
            meshes.append(self.link_objects[i].get_mesh(R, p))
            colors.append(self.link_objects[i].get_colors())
        A = self.arm.fk(q, i + 1, base=True, tip=True)
        R = A[:3, :3]
        p = A[:3, 3]

        meshes.append(self.ee_object.get_mesh(R, p))
        colors.append(self.ee_object.get_colors())

        self.mesh = np.vstack(meshes)
        self.colors = np.vstack(colors)


class LinkMeshObject:
    def __init__(
        self,
        dh,
        jt="r",
        link_width=0.1,
        joint_width=0.15,
        joint_height=0.25,
        link_color=None,
        joint_color=None,
    ):

        theta = dh[0]
        d = dh[1]
        a = dh[2]
        alpha = dh[3]

        lw = link_width

        w = joint_width
        h = joint_height

        le = np.sqrt(d**2 + a**2)

        self.link_points = np.array(
            [
                [0, lw / 2, 0],
                [0, 0, lw / 2],
                [0, -lw / 2, 0],
                [0, 0, -lw / 2],
                [-le, lw / 2, 0],
                [-le, 0, lw / 2],
                [-le, -lw / 2, 0],
                [-le, 0, -lw / 2],
            ]
        )

        v1 = np.array([-le, 0, 0])
        v2 = np.array([-a, d * np.sin(-alpha), -d * np.cos(-alpha)])

        axis = np.cross(v1, v2)
        n_axis = np.linalg.norm(axis)
        if np.abs(n_axis) < 1e-12:
            R = np.eye(3)
        else:
            axis = axis / np.linalg.norm(axis)
            ang = np.arccos(v1 @ v2 / (np.linalg.norm(v1) * np.linalg.norm(v2)))
            v = axis / np.linalg.norm(axis)
            V = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
            R = np.eye(3) + np.sin(ang) * V + (1 - np.cos(ang)) * V @ V

        self.link_points = self.link_points @ R.T

        if jt == "r":
            cylinder = gl.MeshData.cylinder(
                rows=10, cols=20, radius=[w / 2] * 2, length=h
            )
            vertices = cylinder.vertexes()
            faces = cylinder.faces()

            bottom_center = len(vertices)
            top_center = bottom_center + 1
            vertices = np.vstack(
                [vertices, [0.0, 0.0, 0.0], [0.0, 0.0, h]]
            )
            bottom_ring = np.arange(20, dtype=np.uint32)
            top_ring = bottom_ring + 10 * 20
            next_bottom_ring = np.roll(bottom_ring, -1)
            next_top_ring = np.roll(top_ring, -1)
            cap_faces = np.vstack(
                [
                    np.column_stack(
                        [
                            np.full(20, bottom_center, dtype=np.uint32),
                            next_bottom_ring,
                            bottom_ring,
                        ]
                    ),
                    np.column_stack(
                        [
                            np.full(20, top_center, dtype=np.uint32),
                            top_ring,
                            next_top_ring,
                        ]
                    ),
                ]
            )
            vertices[:, 2] -= h / 2
            self.joint_points = vertices[np.vstack([faces, cap_faces])]
        else:
            self.joint_points = np.array(
                [
                    [0.5 * w, -0.5 * w, -0.5 * h],
                    [-0.5 * w, -0.5 * w, -0.5 * h],
                    [-0.5 * w, -0.5 * w, 0.5 * h],
                    [0.5 * w, -0.5 * w, 0.5 * h],
                    [0.5 * w, 0.5 * w, -0.5 * h],
                    [-0.5 * w, 0.5 * w, -0.5 * h],
                    [-0.5 * w, 0.5 * w, 0.5 * h],
                    [0.5 * w, 0.5 * w, 0.5 * h],
                ]
            )

        Rz = np.array(
            [
                [np.cos(theta), -np.sin(theta), 0],
                [np.sin(theta), np.cos(theta), 0],
                [0, 0, 1],
            ]
        )

        Rx = np.array(
            [
                [1, 0, 0],
                [0, np.cos(alpha), -np.sin(alpha)],
                [0, np.sin(alpha), np.cos(alpha)],
            ]
        )

        self.joint_points = self.joint_points @ Rz @ Rx + v2

        if link_color is None:
            link_color = np.array([0, 0, 0.35, 1])
        elif not isinstance(link_color, (np.ndarray)):
            link_color = np.array(link_color)
        self.link_colors = np.zeros((12, 3, 4)) + link_color

        if joint_color is None:
            joint_color = np.array([0.35, 0, 0.0, 1])
        elif not isinstance(joint_color, (np.ndarray)):
            joint_color = np.array(joint_color)
        self.joint_colors = np.zeros((len(self.joint_points), 3, 4)) + joint_color
        if jt != "r":
            self.joint_colors[6:8, :, :] = np.zeros((2, 3, 4)) + grey

    @staticmethod
    def points_to_mesh(link_points, joint_points):

        link_mesh = np.array(
            [
                [link_points[0], link_points[4], link_points[5]],
                [link_points[0], link_points[1], link_points[5]],
                [link_points[1], link_points[5], link_points[6]],
                [link_points[1], link_points[2], link_points[6]],
                [link_points[2], link_points[6], link_points[7]],
                [link_points[2], link_points[7], link_points[3]],
                [link_points[3], link_points[7], link_points[4]],
                [link_points[3], link_points[0], link_points[4]],
                [link_points[0], link_points[2], link_points[3]],
                [link_points[0], link_points[1], link_points[2]],
                [link_points[5], link_points[4], link_points[7]],
                [link_points[5], link_points[6], link_points[7]],
            ]
        )

        joint_mesh = np.array(
            [
                [joint_points[0], joint_points[1], joint_points[2]],
                [joint_points[0], joint_points[2], joint_points[3]],
                [joint_points[0], joint_points[3], joint_points[4]],
                [joint_points[3], joint_points[4], joint_points[7]],
                [joint_points[2], joint_points[3], joint_points[6]],
                [joint_points[3], joint_points[6], joint_points[7]],
                [joint_points[0], joint_points[1], joint_points[5]],
                [joint_points[0], joint_points[4], joint_points[5]],
                [joint_points[1], joint_points[2], joint_points[6]],
                [joint_points[1], joint_points[5], joint_points[6]],
                [joint_points[4], joint_points[5], joint_points[6]],
                [joint_points[4], joint_points[6], joint_points[7]],
            ]
        )

        return np.vstack((link_mesh, joint_mesh))

    def get_colors(self):
        return np.vstack((self.link_colors, self.joint_colors))

    def get_mesh(self, R, p):
        lp = self.link_points @ R.T + p
        jp = self.joint_points @ R.T + p

        if jp.ndim == 3:
            link_mesh = self.points_to_mesh(lp, np.zeros((8, 3)))[:12]
            return np.vstack((link_mesh, jp))
        return self.points_to_mesh(lp, jp)


class FrameViz:
    # NOTE: This class could likely be changed to use the AxisViz class to reduce
    # code duplication. - Mat

    def __init__(
        self,
        A=np.eye(4),
        scale=1,
        colors=[red, green, blue],
        frame_label=None,
        axes_label=None,
    ):
        height = 0.35 * scale
        radius = height / 20
        self.frame_label_pos = np.array([0, 0, -0.05])
        self.axis_label_poss = np.eye(3) * height
        # gives mesh for cylinder along positive z-axis starting at origin
        cylinder_mesh = gl.MeshData.cylinder(
            rows=10, cols=20, radius=[radius] * 2, length=height
        )
        self.faces = cylinder_mesh.faces()
        z_pts = cylinder_mesh.vertexes().copy()
        y_pts = z_pts @ np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
        x_pts = z_pts @ np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]])
        self.pts = [x_pts, y_pts, z_pts]
        self.axes = [
            gl.GLMeshItem(meshdata=cylinder_mesh, smooth=True, color=colors[i])
            for i in range(3)
        ]
        self.frame_label = frame_label
        if self.frame_label is not None:
            self.frame_label = GLTextItem.GLTextItem(text=frame_label, color=(0, 0, 0))
        self.axis_labels = axes_label
        if self.axis_labels is not None:
            self.axis_labels = [
                GLTextItem.GLTextItem(text=f"x_{axes_label}", color=(0, 0, 0)),
                GLTextItem.GLTextItem(text=f"y_{axes_label}", color=(0, 0, 0)),
                GLTextItem.GLTextItem(text=f"z_{axes_label}", color=(0, 0, 0)),
            ]
        self.update(A)

    def update(self, A: NDArray):
        for pts, axis in zip(self.pts, self.axes):
            axis.setMeshData(vertexes=pts @ A[:3, :3].T + A[:3, 3], faces=self.faces)
        if self.frame_label is not None:
            p = A[:3, 3] + A[:3, :3] @ self.frame_label_pos
            self.frame_label.setData(pos=p)
        if self.axis_labels is not None:
            for pos, label in zip(self.axis_label_poss, self.axis_labels):
                p = A[:3, 3] + A[:3, :3] @ pos
                label.setData(pos=p)


class AxisViz:
    def __init__(
        self,
        axis: NDArray,
        pos_offset=np.zeros(3),
        scale=1,
        color=np.zeros(4),
        label=None,
    ):
        height = 0.35 * scale
        radius = height / 20

        axis = np.array(axis, dtype=np.float64)
        assert axis.shape == (3,)
        axis /= np.linalg.norm(axis)  # ensure unit vector
        z = np.array([0, 0, 1.0])
        if np.equal(z, axis).all():
            R = np.eye(3)
        elif np.equal(-z, axis).all():
            R = np.array([[1.0, 0, 0], [0, -1, 0], [0, 0, -1]])
        else:
            v = np.cross(z, axis)
            c = z @ axis
            skew_v = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
            R = np.eye(3) + skew_v + (skew_v @ skew_v) / (1 + c)

        # gives mesh for cylinder along positive z-axis starting at origin
        cylinder_mesh = gl.MeshData.cylinder(
            rows=10, cols=20, radius=[radius] * 2, length=height
        )
        pts = cylinder_mesh.vertexes()
        cylinder_mesh.setVertexes(pts @ R.T + pos_offset)
        self.axis = gl.GLMeshItem(meshdata=cylinder_mesh, smooth=True, color=color)
        self.label = label
        if label is not None:
            self.label = GLTextItem.GLTextItem(
                pos=height * R[:, 2] + pos_offset, text=label, color=(0, 0, 0)
            )


class EEMeshObject:
    def __init__(self, scale=1, w=0.05, o1=0.05, o2=0.15, o3=0.3, o4=0.2, o5=0.1):
        # TODO: can replace the triangle with a fun STL
        # see - https://stackoverflow.com/questions/71052955/is-there-any-way-to-insert-a-3d-image-of-stl-obj-fbx-and-dae-formats-in-pyq

        w = w * scale
        o1 = o1 * scale
        o2 = o2 * scale
        o3 = o3 * scale
        o4 = o4 * scale
        o5 = o5 * scale

        self.points = np.array(
            [
                [-o1, o2, w / 2],
                [-o1, -o2, w / 2],
                [o3, 0, w / 2],
                [-o1, o2, -w / 2],
                [-o1, -o2, -w / 2],
                [o3, 0, -w / 2],
            ]
        )
        self.colors = np.zeros((8, 3, 4)) + red
        self.colors[1, :, :] = np.zeros((3, 4)) + dark_blue

    @staticmethod
    def points_to_mesh(p):
        mesh = np.array(
            [
                [p[0], p[1], p[2]],
                [p[3], p[4], p[5]],
                [p[0], p[1], p[3]],
                [p[1], p[4], p[3]],
                [p[1], p[2], p[5]],
                [p[1], p[4], p[5]],
                [p[0], p[2], p[5]],
                [p[0], p[3], p[5]],
            ]
        )
        return mesh

    def get_mesh(self, R, p):
        points = self.points @ R.T + p
        mesh = self.points_to_mesh(points)
        return mesh

    def get_colors(self):
        return self.colors


class GripperSTLMeshObject:
    """Triangle mesh loaded from an ASCII or binary STL file."""

    def __init__(self, stl_path, gripper_offset=None, scale=1.0, color=None):
        """
        :param str | pathlib.Path stl_path: Path to an ASCII or binary STL file.
        :param NDArray | None gripper_offset: 4x4 transform from the arm tip
            frame to the STL mesh frame.
        :param float scale: Positive scaling factor applied to STL coordinates.
        :param NDArray | None color: RGB or RGBA mesh color. Defaults to grey.
        """
        self.gripper_offset = (
            np.eye(4)
            if gripper_offset is None
            else np.asarray(gripper_offset, dtype=float).copy()
        )
        if self.gripper_offset.shape != (4, 4):
            raise ValueError("gripper_offset must be a 4x4 homogeneous transform")
        if scale <= 0:
            raise ValueError("scale must be positive")

        mesh_color = np.asarray(grey if color is None else color, dtype=float)
        if mesh_color.shape == (3,):
            mesh_color = np.append(mesh_color, 1.0)
        if mesh_color.shape != (4,):
            raise ValueError("color must contain three RGB or four RGBA values")

        self.vertices, self.faces = self._load_stl(stl_path)
        self.vertices *= scale
        self.colors = np.broadcast_to(
            mesh_color,
            (len(self.faces), 3, 4),
        ).copy()

    @staticmethod
    def _load_stl(filename):
        """Return indexed vertices and triangular faces from an STL file."""
        path = Path(filename)
        if not path.is_file():
            raise FileNotFoundError(f"STL file not found: {path}")

        data = path.read_bytes()
        if len(data) >= 84:
            triangle_count = struct.unpack_from("<I", data, 80)[0]
            expected_size = 84 + triangle_count * 50
            if triangle_count > 0 and len(data) == expected_size:
                return GripperSTLMeshObject._load_stl_binary(data)

        try:
            text = data.decode("ascii")
        except UnicodeDecodeError as error:
            raise ValueError(
                f"STL file is neither valid binary nor ASCII: {path}"
            ) from error
        return GripperSTLMeshObject._load_stl_ascii(text, path)

    @staticmethod
    def _load_stl_binary(data):
        """Load triangles from binary STL bytes using little-endian fields."""
        triangle_count = struct.unpack_from("<I", data, 80)[0]
        vertices = np.empty((triangle_count * 3, 3), dtype=np.float32)
        triangle_record = struct.Struct("<12fH")

        offset = 84
        for triangle_index in range(triangle_count):
            record = triangle_record.unpack_from(data, offset)
            first_vertex = triangle_index * 3
            vertices[first_vertex : first_vertex + 3] = np.asarray(
                record[3:12]
            ).reshape(3, 3)
            offset += triangle_record.size

        faces = np.arange(triangle_count * 3).reshape(-1, 3)
        return vertices, faces

    @staticmethod
    def _load_stl_ascii(text, path="<ASCII STL>"):
        """Load triangles from decoded ASCII STL text."""
        vertices = []
        for line in text.splitlines():
            fields = line.split()
            if fields and fields[0].lower() == "vertex":
                if len(fields) != 4:
                    raise ValueError(f"Invalid vertex record in ASCII STL: {path}")
                vertices.append([float(value) for value in fields[1:]])

        if not vertices or len(vertices) % 3 != 0:
            raise ValueError(
                f"ASCII STL must contain complete triangular facets: {path}"
            )

        vertex_array = np.asarray(vertices, dtype=np.float32)
        faces = np.arange(len(vertex_array)).reshape(-1, 3)
        return vertex_array, faces

    def get_mesh(self, R, p):
        """Return mesh triangles transformed into the visualization frame."""
        R_offset = self.gripper_offset[:3, :3]
        p_offset = self.gripper_offset[:3, 3]
        transformed = (self.vertices @ R_offset.T + p_offset) @ np.asarray(
            R
        ).T + np.asarray(p)
        return transformed[self.faces]

    def get_colors(self):
        """Return one RGBA color at each triangle vertex."""
        return self.colors
