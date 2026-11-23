"""Explicit joint-state capture and FollowJointTrajectory execution."""
import time
from .core import trajectory_values


def execute(command,profile,store,name=None,joint=None,delta=None,duration=3.,timeout=10.,
            action='/arm_controller/follow_joint_trajectory',state_topic='/joint_states',replace=False):
    import rclpy
    from rclpy.node import Node
    from rclpy.action import ActionClient
    from sensor_msgs.msg import JointState
    from trajectory_msgs.msg import JointTrajectoryPoint
    from control_msgs.action import FollowJointTrajectory
    rclpy.init();node=Node('arm_tools_client');deadline=time.monotonic()+timeout
    state=[];state_received=[None]
    def callback(msg):
        stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        age=node.get_clock().now().nanoseconds*1e-9-stamp
        if stamp>0 and -.1<=age<=1.:
            try:state[:]=[profile.capture(msg.name,msg.position)];state_received[0]=time.monotonic()
            except (ValueError,TypeError):state.clear()
    subscription=node.create_subscription(JointState,state_topic,callback,10)
    def wait(predicate):
        while not predicate() and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.02)
        return predicate()
    try:
        if command in ['teach','jog']:
            if not wait(lambda:bool(state)):raise TimeoutError('No complete, fresh joint state')
            if command=='teach':store.put(name,state[0],replace);return
            pose=profile.jog(state[0],joint,delta)
        else:pose=profile.validate(store.get(name))
        names,positions,seconds=trajectory_values(profile,pose,duration)
        client=ActionClient(node,FollowJointTrajectory,action)
        if not wait(client.server_is_ready):raise TimeoutError('Trajectory action unavailable')
        if command=='jog':
            if not state or state_received[0] is None or time.monotonic()-state_received[0]>1.:
                raise ValueError('Joint state expired before jog transmission')
            pose=profile.jog(state[0],joint,delta)
            names,positions,seconds=trajectory_values(profile,pose,duration)
        goal=FollowJointTrajectory.Goal();goal.trajectory.joint_names=names
        point=JointTrajectoryPoint();point.positions=positions
        point.time_from_start.sec=int(seconds);point.time_from_start.nanosec=int((seconds-int(seconds))*1e9)
        goal.trajectory.points=[point]
        ack=client.send_goal_async(goal)
        if not wait(ack.done):raise TimeoutError('No trajectory acknowledgement')
        handle=ack.result()
        if not handle.accepted:raise RuntimeError('Trajectory rejected')
        result=handle.get_result_async()
        if not wait(result.done):
            cancel=handle.cancel_goal_async();limit=time.monotonic()+2
            while not cancel.done() and time.monotonic()<limit:rclpy.spin_once(node,timeout_sec=.02)
            raise TimeoutError('Trajectory timed out; cancellation requested')
        response=result.result()
        if response.status!=4 or response.result.error_code!=0:raise RuntimeError('Trajectory failed')
    finally:
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
