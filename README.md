# ROS 2 Arm Tools

English · [日本語](docs/README.ja.md)

Teach, store and replay named joint poses, and jog individual joints.
The tools use ROS JointState and FollowJointTrajectory interfaces instead of
PyLoT's Robot facade or fixed motor IDs. They use the robot's existing driver
and ros2_control rather than opening motor ports directly.

## Configure a robot

Use `config/example_arm.yaml` as a template for your robot's joint names and
limits. Revolute joints use radians; prismatic joints use metres. The example
limits are illustrative, not calibrated values for a real robot. Include every
joint controlled by the selected controller. For a gripper on another controller,
use a separate profile and action name.

```yaml
joints:
  shoulder: {type: revolute, min: -1.0, max: 1.0}
  slide: {type: prismatic, min: 0.0, max: 0.1}
```

## Teach, replay and jog

```bash
ros2-arm-tools --profile my_arm.yaml --file poses.yaml teach ready
ros2-arm-tools --file poses.yaml list
ros2-arm-tools --file poses.yaml show ready
ros2-arm-tools --profile my_arm.yaml --file poses.yaml move ready --duration 3 --timeout 10
ros2-arm-tools --profile my_arm.yaml jog shoulder 0.02 --duration 1
```

`teach` records the latest `/joint_states` values. Manage torque on the robot
side when physically guiding the arm; this tool does not change torque settings.
`jog` performs one adjustment by adding a delta to newly acquired joint state.
Its delta is in radians for revolute joints or metres for prismatic joints.
There is no fallback that moves from an assumed zero position if state is missing.

Teaching and jogging require complete, valid, fresh state for every configured
joint. Out-of-range values, NaN/inf and unknown joints are rejected. Replay
revalidates poses against the current profile. Populate JointState's
`header.stamp`. The default action is `/arm_controller/follow_joint_trajectory`;
change it with `--action`. The client waits for the result and requests cancellation
on timeout. Use `--states` to select the joint-state topic. Duration must be
greater than zero and at most 86,400 seconds.

Storage uses file locking and atomic rename, rejects corrupt files and requires
`--replace` to teach over an existing pose. Its format is
`{schema_version: 1, poses: {NAME: {JOINT: SI_VALUE}}}`.
Legacy Luna arm pose files are not imported automatically.

## Capture-only ROS node

```bash
ros2 run arm_tools arm_tools_node --ros-args -p profile:=/absolute/my_arm.yaml \
  -p file:=/absolute/poses.yaml -p pose_name:=ready
ros2 service call /arm_tools/record std_srvs/srv/Trigger '{}'
```

The persistent node supports recording and `/arm_tools/list` only; it sends no
motion commands on startup. `profile` is required. Integration tests use synthetic
JointState data and a test trajectory server to verify saved values, joint names,
transmitted positions and result handling. They do not move a real arm.

## Installation and checks

Requires Python 3.10+. Run these commands from the repository root.
The core works in a regular Python environment without ROS.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python -m arm_tools.cli demo
```

For ROS 2 Jazzy, place the repository in a regular workspace's `src` directory
and build it in a ROS environment:

```bash
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select arm_tools
source install/setup.bash
```

Adapt `config/params.yaml` to your inputs and outputs. Parameters are read at startup.
Start the node with
`ros2 launch arm_tools arm_tools.launch.py params_file:=/absolute/path/to/params.yaml`.
CI runs core tests and the synthetic demo on Python 3.10 and 3.12. ROS integration
tests run when ROS is available and are skipped otherwise. These checks do not
certify model, physical-sensor or real-arm performance.

## License and source

This repository is currently private. Apache-2.0. See
[PROVENANCE.md](PROVENANCE.md) for the source commit, files and extraction changes.
There is no dependency on the original monorepo.
