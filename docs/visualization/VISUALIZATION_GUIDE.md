# BYU Robotics Visualization Library Guide

A comprehensive guide to using `byu_robomanip.visualization` for robotics
simulations, arm visualization, and 3D scene management.

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Core Classes](#core-classes)
4. [3D Visualization with VizScene](#3d-visualization-with-vizscene)
5. [2D Planar Visualization](#2d-planar-visualization)
6. [Interactive Arm Control](#interactive-arm-control)
7. [Predefined Colors](#predefined-colors)
8. [Common Patterns](#common-patterns)
9. [Troubleshooting](#troubleshooting)
10. [Complete Examples](#complete-examples)

## Overview

The visualization library provides three main components for robotics visualization:

- **VizScene**: 3D OpenGL-based visualization using PySide6 and pyqtgraph
- **PlanarMPL**: 2D matplotlib-based visualization for planar robot arms
- **ArmPlayer**: Interactive arm control with sliders for joint manipulation

### Dependencies

```python
import numpy as np
from byu_robomanip.visualization import VizScene, PlanarMPL, ArmPlayer
from byu_robomanip import transforms as tr  # For rotation matrices
from byu_robomanip import kinematics as kin  # For robot arms
```

Install the package and its required dependencies from the repository root with
`python -m pip install -e .`. The visualization stack uses `PySide6`,
`pyqtgraph`, `matplotlib`, `numpy`, and `PyOpenGL`.

## Getting Started

### Basic 3D Scene Setup

```python
from byu_robomanip.visualization import VizScene
import numpy as np

# Create 3D visualization
viz = VizScene()

# Add world coordinate frame
viz.add_frame(np.eye(4), label='world', axes_label='w')

# Keep window open and always release the scene afterward
try:
    viz.hold()  # Blocks until window closed
finally:
    viz.close_viz()  # Clean shutdown
```

### Quick Robot Visualization

```python
from byu_robomanip import kinematics as kin
from byu_robomanip import transforms as tr

# Define robot
dh = [[0, 0, 0.4, 0], [0, 0, 0.4, 0], [0, 0, 0.4, 0]]
arm = kin.SerialArm(dh, jt=['r', 'r', 'r'])

# Visualize
viz = VizScene()
viz.add_arm(arm, q=[0, np.pi/4, -np.pi/2])
try:
    viz.hold()
finally:
    viz.close_viz()
```

## Core Classes

### VizScene - 3D Visualization Engine

The main class for 3D robotics visualization using OpenGL rendering.

#### Initialization
```python
viz = VizScene()
# Creates a 3D window with grid, proper lighting, and camera controls
```

#### Key Features
- Hardware-accelerated OpenGL rendering
- Mouse controls: rotate (left drag), pan (right drag), zoom (wheel)
- Automatic camera distance adjustment
- Transparent/translucent object support
- Real-time updates for animations

### PlanarMPL - 2D Matplotlib Visualization

For 2D planar robot arms with matplotlib backend.

```python
planar_viz = PlanarMPL(arm, q0=[0, 0, 0], trace=True)
planar_viz.show()
```

### ArmPlayer - Interactive Control Interface

Opens a window with sliders for interactive joint control.

```python
player = ArmPlayer(arm, fontsize=14)
# Automatically opens interactive window with joint sliders
```

## 3D Visualization with VizScene

### Robot Arms

#### Basic Arm Visualization
```python
viz.add_arm(arm, q=[0, np.pi/4, -np.pi/2])
```

#### Advanced Arm Options
```python
viz.add_arm(
    arm,
    draw_frames=True,           # Show coordinate frames at each joint
    label_axes=True,            # Label frame axes (x, y, z)
    joint_colors=[[1,0,0,1], [0,1,0,1], [0,0,1,1]]  # Custom joint colors
)
```

#### Custom STL Gripper

An ASCII or binary STL mesh can replace the default end effector. The offset
maps the arm tip frame to the STL mesh frame.

```python
gripper_offset = tr.se3(R=tr.rotz(np.pi/2), p=[0, 0, 0.05])
viz.add_arm(
    arm,
    q=[0, np.pi/4, -np.pi/2],
    gripper_stl="models/gripper.stl",
    gripper_offset=gripper_offset,
    gripper_scale=1.0,
)
```

The course repository does not currently include a redistributable gripper
model. To use an STL gripper, provide a local STL path with `--stl`; without
that option, the example displays the default end effector.

#### Multiple Arms
```python
# Add multiple arms
viz.add_arm(arm1, q=q1)
viz.add_arm(arm2, q=q2)

# Update all arms simultaneously
viz.update(qs=[q1_new, q2_new])

# Remove specific arm
viz.remove_arm(index=0)  # Remove first arm
viz.remove_arm()         # Remove all arms
```

### Coordinate Frames

#### Basic Frame
```python
# Identity frame at origin
viz.add_frame(np.eye(4), label='world')

# Transformed frame
T = tr.se3(R=tr.rotz(np.pi/4), t=[1, 0, 0])
viz.add_frame(T, label='rotated', axes_label='r')
```

#### Frame Management
```python
# Add multiple frames
transforms = [T1, T2, T3]
for i, T in enumerate(transforms):
    viz.add_frame(T, label=f'frame_{i}')

# Update frame positions
viz.update(As=[T1_new, T2_new, T3_new])

# Remove frames
viz.remove_frame(index=0)  # Remove specific frame
viz.remove_frame()         # Remove all frames
```

### Individual Axes

For single directional vectors:

```python
# Add unit vector along custom direction
axis_direction = np.array([1, 1, 0])  # 45° in xy plane
viz.add_axis(
    axis=axis_direction,
    pos_offset=[0, 0, 1],    # Start position
    scale=2.0,               # Length and thickness
    label='custom_axis'
)
```

### Markers and Points

#### Spherical Markers
```python
# Default green marker
viz.add_marker([1, 0, 0])

# Custom color and size
viz.add_marker(
    pos=[2, 1, 0.5],
    color=[1, 0, 0, 0.7],    # Semi-transparent red
    radius=0.2
)

# Multiple markers
positions = [[1,0,0], [0,1,0], [0,0,1]]
for pos in positions:
    viz.add_marker(pos)

# Update marker positions
viz.update(poss=[[1.1,0,0], [0,1.1,0], [0,0,1.1]])
```

### Obstacles and Environment

#### Spherical Obstacles
```python
# Default yellow obstacle
viz.add_obstacle([2, 2, 0])

# Custom obstacle
viz.add_obstacle(
    pos=[-1, 1, 0],
    color=[0.8, 0.4, 0, 0.6],  # Orange with transparency
    rad=0.5
)
```

### 3D Ellipses (NEW!)

Perfect for uncertainty regions, workspaces, and safety margins:

#### Basic Ellipse
```python
viz.add_ellipse(
    position=[0, 0, 0],              # Center position
    orientation=np.eye(3),           # No rotation
    size=[1.0, 0.5, 0.3],           # Radii [rx, ry, rz]
    color=[1, 0, 0],                # Red
    alpha=0.7                       # 70% opacity
)
```

#### Advanced Ellipse Options
```python
# Rotated ellipse with custom edges
R = tr.rotx(np.pi/4) @ tr.rotz(np.pi/6)
viz.add_ellipse(
    position=[2, 0, 1],
    orientation=R,
    size=[0.8, 1.2, 0.4],
    color=[0, 1, 0, 0.5],           # Semi-transparent green
    show_edges=True,                # Show mesh structure
    edge_color=[0, 0, 0, 1],        # Black edges
    resolution=80                   # High quality mesh
)

# Wireframe only (great for boundaries)
viz.add_ellipse(
    position=[1, 2, 0],
    orientation=tr.roty(np.pi/3),
    size=[1.5, 0.8, 0.6],
    color=[0, 0, 1],
    wireframe=True                  # No solid surface
)
```

#### Ellipse Applications
```python
# End effector uncertainty
uncertainty_pos = arm.fk([q1, q2, q3])[:3, 3]
viz.add_ellipse(uncertainty_pos, np.eye(3), [0.1, 0.05, 0.03], 
                color=[1,0,0,0.3], show_edges=True)

# Workspace boundary
viz.add_ellipse([0, 0, 0.5], tr.roty(np.pi/6), [1.2, 0.8, 0.6],
                color=[0,1,0], wireframe=True)

# Safety margin around obstacle
viz.add_ellipse(obstacle_pos, np.eye(3), [0.6, 0.6, 0.8],
                color=[1,1,0,0.4], edge_color=[1,0.5,0,0.8])
```

#### Ellipse API and Scene Management

The complete method signature is:

```python
viz.add_ellipse(
    position, orientation, size, scale=1.0, color=blue, alpha=1.0,
    resolution=50, show_edges=True, edge_color=None, wireframe=False
)
```

`position` is a three-element world-coordinate center, `orientation` is a
3x3 rotation matrix, and `size` contains the positive local radii
`[rx, ry, rz]`. The `scale` parameter uniformly scales the radii. Colors use
RGB or RGBA values from 0 to 1; `alpha` overrides the color alpha channel.
Use `resolution=20`--`30` for many ellipses and higher values for smoother
meshes. `wireframe=True` draws only the mesh edges.

Ellipses can be removed individually by their order of addition or all at
once:

```python
viz.remove_ellipse(0)  # Remove the first ellipse
viz.remove_ellipse()    # Remove all stored obstacles and ellipses
```

Ellipses are stored in the scene's `obstacles` list, so removing all ellipses
also removes spherical obstacles created with `add_obstacle()`.

### Scene Management

#### Real-time Updates
```python
# Animate robot motion
for t in np.linspace(0, 2*np.pi, 100):
    q = [np.sin(t), np.cos(t), t/2]
    viz.update(qs=[q])  # Update first arm
    viz.hold(0.05)      # 50ms delay
```

#### Automatic Motion
```python
# Let arms wander randomly
viz.wander(
    index=[0, 1],           # Which arms to animate
    speed=0.1,              # Joint velocity scale
    duration=10.0,          # Run for 10 seconds
    accel=0.001             # Acceleration magnitude
)
```

#### Camera and View Control
```python
# Camera automatically adjusts to fit all objects
# Manual zoom: mouse wheel
# Rotate view: left mouse drag
# Pan: right mouse drag

# Window stays open until manually closed. For a scene that will not be
# reused, protect the hold with finally so cleanup also runs on interruption.
try:
    viz.hold()
finally:
    viz.close_viz()

# For a timed hold on a separate scene, use the same pattern:
viz = VizScene()
try:
    viz.hold(seconds=5.0)
finally:
    viz.close_viz()
```

## 2D Planar Visualization

### Basic Planar Arm

```python
# 2D arm visualization with matplotlib
planar_viz = PlanarMPL(
    arm,
    q0=[0, 0, 0],          # Initial configuration
    trace=True             # Show end effector trace
)

# Update arm configuration
planar_viz.update([np.pi/4, -np.pi/2, np.pi/3])

# Show plot
planar_viz.show()
```

### Interactive 2D Control

```python
# Launch interactive sliders for 2D arm
planar_viz.play()  # Adds sliders and real-time control
```

## Interactive Arm Control

### ArmPlayer Interface

```python
# Launch interactive 3D arm control
player = ArmPlayer(arm, fontsize=14)
# Window opens automatically with:
# - 3D arm visualization
# - Joint sliders for each DOF
# - Real-time position/angle display
# - Automatic collision detection display
```

The `ArmPlayer` provides:
- Individual joint sliders (-π to π range)
- Real-time end effector position display
- Automatic 3D camera controls
- Professional GUI layout

## Predefined Colors

The library includes convenient color constants:

```python
# Basic colors (RGB with alpha=1.0)
red    = [0.7, 0, 0, 1]
green  = [0, 0.7, 0, 1]
blue   = [0, 0, 0.7, 1]

# Dark variants
dark_red   = [0.3, 0, 0, 1]
dark_green = [0, 0.3, 0, 1]
dark_blue  = [0, 0, 0.3, 1]

# Other colors
white  = [1, 1, 1, 1]
grey   = [0.3, 0.3, 0.3, 1]
yellow = [0.87, 0.93, 0.37, 1]

# Usage
viz.add_marker([0, 0, 0], color=red)
viz.add_ellipse([1, 0, 0], np.eye(3), [0.5, 0.5, 0.5], color=blue)
```

## Common Patterns

### Robot Workspace Visualization

```python
def visualize_workspace(arm, samples=1000):
    viz = VizScene()
    
    # Add robot at home position
    viz.add_arm(arm, q=[0]*arm.n)
    
    # Sample random configurations and mark reachable points
    for _ in range(samples):
        q_random = np.random.uniform(-np.pi, np.pi, arm.n)
        T_ee = arm.fk(q_random)
        pos = T_ee[:3, 3]
        viz.add_marker(pos, color=green, radius=0.02)
    
    viz.hold()
    viz.close_viz()
```

### Path Planning Visualization

```python
def visualize_path(arm, path, obstacles=None):
    viz = VizScene()
    
    # Add obstacles
    if obstacles:
        for obs_pos, obs_size in obstacles:
            viz.add_obstacle(obs_pos, rad=obs_size)
    
    # Add path points
    for i, q in enumerate(path):
        T = arm.fk(q)
        pos = T[:3, 3]
        color = [i/len(path), 1-i/len(path), 0, 0.7]  # Color gradient
        viz.add_marker(pos, color=color)
    
    # Animate path
    for q in path:
        viz.update(qs=[q])
        viz.hold(0.1)
    
    viz.close_viz()
```

### Uncertainty Visualization

```python
def visualize_uncertainty(arm, q_nominal, covariance_xyz):
    viz = VizScene()
    
    # Add nominal robot
    viz.add_arm(arm, q=q_nominal)
    
    # Add uncertainty ellipse at end effector
    T_nominal = arm.fk(q_nominal)
    pos = T_nominal[:3, 3]
    
    # Convert covariance to ellipse radii (simplified)
    eigenvals = np.linalg.eigvals(covariance_xyz)
    radii = 2 * np.sqrt(eigenvals)  # 2-sigma bounds
    
    viz.add_ellipse(
        position=pos,
        orientation=np.eye(3),
        size=radii,
        color=[1, 0, 0, 0.3],
        show_edges=True
    )
    
    viz.hold()
    viz.close_viz()
```

### Multi-Robot Coordination

```python
def multi_robot_scene(arms, configurations):
    viz = VizScene()
    
    # Add multiple robots with different colors
    colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1]]
    
    for i, (arm, q) in enumerate(zip(arms, configurations)):
        joint_colors = [colors[i % len(colors)]] * arm.n
        viz.add_arm(arm, q=q, joint_colors=joint_colors)
    
    # Add shared workspace
    viz.add_ellipse([0, 0, 0], np.eye(3), [2, 2, 1], 
                   color=[0.5, 0.5, 0.5, 0.1], wireframe=True)
    
    viz.hold()
    viz.close_viz()
```

## Troubleshooting

### Common Issues

#### "ModuleNotFoundError: No module named 'PySide6'"
```bash
python -m pip install -e .
```

#### Window doesn't appear or immediately closes
```python
# Make sure to call hold() to keep window open
viz.hold()  # Blocks until window closed

# Or hold for specific time
viz.hold(seconds=10)

# Always clean up
viz.close_viz()
```

#### Arm not visible or very small/large
```python
# Check DH parameters and joint values
print("Arm reach:", arm.reach)  # Should be reasonable scale

# Camera automatically adjusts, but check for extreme coordinates
T = arm.fk(q)
print("End effector position:", T[:3, 3])
```

#### Colors not showing correctly
```python
# Ensure color values are 0-1 range
color = [0.5, 0.8, 0.2, 0.7]  # Good: all values 0-1

# Convert if using 0-255 range
color_255 = [128, 204, 51, 179]
color = [c/255.0 for c in color_255]
```

#### Performance issues with many objects
```python
# Reduce ellipse resolution for better performance
viz.add_ellipse(pos, orient, size, resolution=20)  # Default is 50

# Remove unnecessary objects
viz.remove_marker()  # Remove all markers
viz.remove_frame()   # Remove all frames

# Use wireframe for complex shapes
viz.add_ellipse(pos, orient, size, wireframe=True)
```

### Best Practices

1. **Always clean up**: Wrap a final `viz.hold()` in `try/finally` and call
   `viz.close_viz()` when the scene will not be reused. This is especially
   important in Jupyter notebooks, where the Qt application remains alive.
2. **Reasonable scales**: Keep coordinates in range [-10, 10] for best results
3. **Color consistency**: Use predefined colors for consistency
4. **Performance**: Lower resolution for animations, higher for final renders
5. **Memory management**: Remove unused objects with `remove_*()` methods

## Complete Examples

### Basic Robot Visualization
```python
import numpy as np
from byu_robomanip.visualization import VizScene
from byu_robomanip import kinematics as kin
from byu_robomanip import transforms as tr

# Create 3-DOF robot
dh = [[0, 0, 0.4, 0], [0, 0, 0.4, 0], [0, 0, 0.4, 0]]
arm = kin.SerialArm(dh, jt=['r', 'r', 'r'])

# Create visualization
viz = VizScene()

# Add world frame
viz.add_frame(np.eye(4), label='world', axes_label='w')

# Add robot with frames
viz.add_arm(arm, draw_frames=True, label_axes=True)

# Add target position
target_pos = [0.8, 0.6, 0.2]
viz.add_marker(target_pos, color=red, radius=0.05)

# Add workspace boundary
viz.add_ellipse([0, 0, 0.6], np.eye(3), [1.2, 1.2, 0.8],
               color=green, wireframe=True)

# Keep window open
viz.hold()
viz.close_viz()
```

### Advanced Multi-Object Scene
```python
import numpy as np
from byu_robomanip.visualization import VizScene
from byu_robomanip import kinematics as kin
from byu_robomanip import transforms as tr

def create_complex_scene():
    # Setup robot
    dh = [[0, 0, 0.3, np.pi/2], [0, 0, 0.4, 0], [0, 0, 0.3, 0]]
    arm = kin.SerialArm(dh, jt=['r', 'r', 'r'])
    
    # Create scene
    viz = VizScene()
    
    # Add base coordinate frame
    viz.add_frame(np.eye(4), label='base', axes_label='0')
    
    # Add robot
    q = [np.pi/6, -np.pi/4, np.pi/3]
    viz.add_arm(arm, q=q, draw_frames=True)
    
    # Add obstacles
    obstacles = [
        ([0.5, 0.5, 0.3], 0.15),
        ([-0.3, 0.8, 0.4], 0.12),
        ([0.8, -0.2, 0.2], 0.18)
    ]
    
    for pos, radius in obstacles:
        viz.add_obstacle(pos, rad=radius)
        # Add safety margin
        viz.add_ellipse(pos, np.eye(3), [radius+0.1]*3, 
                       color=[1,1,0,0.2], edge_color=[1,0.5,0,0.5])
    
    # Add goal region
    goal_pos = [0.6, 0.3, 0.8]
    goal_orient = tr.rotx(np.pi/4)
    viz.add_ellipse(goal_pos, goal_orient, [0.15, 0.15, 0.1],
                   color=[0,0,1,0.4], show_edges=True)
    
    # Add uncertainty at current end effector
    T_ee = arm.fk(q)
    ee_pos = T_ee[:3, 3]
    viz.add_ellipse(ee_pos, np.eye(3), [0.05, 0.03, 0.02],
                   color=[1,0,0,0.6], edge_color=[0.5,0,0,1])
    
    # Add path visualization
    path_points = [
        ee_pos,
        ee_pos + [0.1, 0.05, 0.1],
        ee_pos + [0.2, 0.1, 0.2],
        goal_pos
    ]
    
    for i, point in enumerate(path_points):
        alpha = 0.3 + 0.7 * i / len(path_points)  # Fade in along path
        viz.add_marker(point, color=[0, 1, 1, alpha], radius=0.03)
    
    # Add table surface
    viz.add_ellipse([0, 0, -0.1], np.eye(3), [1.5, 1.0, 0.02],
                   color=[0.6, 0.4, 0.2, 0.8], show_edges=True)
    
    print("Complex robotics scene created!")
    print("- Robot with coordinate frames")
    print("- Obstacles with safety margins")
    print("- Goal region (blue ellipse)")
    print("- End effector uncertainty (red)")
    print("- Planned path (cyan markers)")
    print("- Table surface (brown)")
    
    viz.hold()
    viz.close_viz()

if __name__ == "__main__":
    create_complex_scene()
```

This comprehensive visualization library provides all the tools needed for professional robotics simulation, analysis, and presentation. The combination of 3D rendering, real-time updates, and extensive customization options makes it suitable for everything from homework assignments to research publications.
