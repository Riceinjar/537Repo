# Visualization Library Quick Reference

## Essential Imports
```python
from byu_robomanip.visualization import VizScene, PlanarMPL, ArmPlayer
import numpy as np
from byu_robomanip import kinematics as kin
from byu_robomanip import transforms as tr
```

## Quick Start - 3D Scene
```python
viz = VizScene()                                    # Create 3D scene
viz.add_frame(np.eye(4), label='world')            # Add coordinate frame
viz.add_arm(arm, q=[0, 0, 0])                     # Add robot arm
try:
    viz.hold()                                     # Keep window open
finally:
    viz.close_viz()                                # Clean shutdown
```

For a scene that will not be reused, put `hold()` and `close_viz()` in a
`try/finally` block. This remains safe if the user closes the window manually;
`close_viz()` is idempotent. In a notebook, this prevents an old OpenGL scene
from interfering with a later cell that creates another `VizScene`.

## VizScene Methods Quick Reference

### Robot Arms
```python
viz.add_arm(arm, q=None, draw_frames=True, joint_colors=None)
viz.add_arm(arm, gripper_stl="gripper.stl",
            gripper_offset=np.eye(4), gripper_scale=1.0)
viz.remove_arm(index=0)           # Remove specific arm
viz.remove_arm()                  # Remove all arms
```

### Coordinate Frames
```python
viz.add_frame(T, label='frame', axes_label='f')
viz.remove_frame(index=0)
```

### Markers & Obstacles
```python
viz.add_marker(pos, color=green, radius=0.1)
viz.add_obstacle(pos, color=yellow, rad=1.0)
viz.remove_marker()              # Remove all markers
```

### 3D Ellipses (NEW!)
```python
# Basic ellipse
viz.add_ellipse(position, orientation, size, color, alpha)

# With mesh structure
viz.add_ellipse(pos, orient, size, show_edges=True, edge_color=[0,0,0,1])

# Wireframe only
viz.add_ellipse(pos, orient, size, wireframe=True)
```

### Scene Management
```python
viz.update(qs=[q1, q2], As=[T1, T2], poss=[p1, p2])  # Update everything
viz.hold(seconds=5)               # Hold for 5 seconds
viz.wander(duration=10)           # Random arm motion
```

## Predefined Colors
```python
red, green, blue, yellow, white, grey
dark_red, dark_green, dark_blue
```

## Common Patterns

### Basic Robot Visualization
```python
viz = VizScene()
viz.add_arm(arm, q=joint_angles)
viz.hold()
viz.close_viz()
```

### Robot with Workspace
```python
viz = VizScene()
viz.add_arm(arm, draw_frames=True)
viz.add_ellipse([0,0,0.5], np.eye(3), [1,1,0.8], wireframe=True)  # Workspace
viz.hold()
viz.close_viz()
```

### Path Planning Scene
```python
viz = VizScene()
viz.add_arm(arm, q=start_config)
viz.add_obstacle(obstacle_pos, rad=0.2)                           # Obstacle
viz.add_marker(goal_pos, color=red)                               # Goal
viz.add_ellipse(goal_pos, np.eye(3), [0.1,0.1,0.1], color=blue) # Goal tolerance
viz.hold()
viz.close_viz()
```

### Uncertainty Visualization
```python
viz = VizScene()
viz.add_arm(arm, q=nominal_config)
ee_pos = arm.fk(nominal_config)[:3, 3]
viz.add_ellipse(ee_pos, np.eye(3), [0.05,0.03,0.02],             # Uncertainty ellipse
                color=[1,0,0,0.3], show_edges=True)
viz.hold()
viz.close_viz()
```

### Interactive Control
```python
# Method 1: 3D interactive
player = ArmPlayer(arm)  # Automatic window with sliders

# Method 2: 2D interactive  
planar = PlanarMPL(arm)
planar.play()
```

## Coordinate Frame Creation
```python
# Identity frame
T = np.eye(4)

# Translation only
T = tr.se3(p=[1, 0, 0])

# Rotation only
T = tr.se3(R=tr.rotz(np.pi/4))

# Combined
T = tr.se3(R=tr.rotx(np.pi/6), p=[0.5, 0.3, 0.8])
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Window doesn't appear | Call `viz.hold()` |
| Objects too small/large | Check coordinate scales (use -10 to 10 range) |
| Colors not working | Use 0-1 range: `[0.5, 0.8, 0.2, 0.7]` |
| Performance issues | Lower ellipse resolution: `resolution=20` |
| Import errors | From the repository root, run `python -m pip install -e .` |

## Mouse Controls (3D Window)
- **Left drag**: Rotate view
- **Right drag**: Pan view  
- **Scroll wheel**: Zoom in/out
- **Close window**: End visualization

## Animation Pattern
```python
viz = VizScene()
viz.add_arm(arm)

for t in np.linspace(0, 2*np.pi, 100):
    q = [np.sin(t), np.cos(t), 0]
    viz.update(qs=[q])
    viz.hold(0.05)  # 50ms delay

viz.close_viz()
```
