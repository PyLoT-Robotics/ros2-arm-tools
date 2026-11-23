"""Capture-only teaching node: no torque changes and no motion on startup."""
import json
import yaml
import time
from .core import ArmProfile
from .store import PoseStore


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import JointState
    from std_srvs.srv import Trigger

    class Teacher(Node):
        def __init__(self):
            super().__init__('arm_tools')
            path=self.declare_parameter('profile','').value
            if not path:raise ValueError('Set profile to a joint-limit YAML file')
            self.profile=ArmProfile.load(path)
            self.store=PoseStore(self.declare_parameter('file','~/.ros/arm_poses.yaml').value)
            self.pose_name=self.declare_parameter('pose_name','taught').value
            self.replace=self.declare_parameter('replace_existing',False).value
            topic=self.declare_parameter('joint_states_topic','/joint_states').value
            self.current=None;self.received=0.;self.stamp=0.
            self.create_subscription(JointState,topic,self.states,10)
            self.create_service(Trigger,'~/record',self.record)
            self.create_service(Trigger,'~/list',self.list_poses)

        def states(self,msg):
            try:self.current=self.profile.capture(msg.name,msg.position)
            except (ValueError,TypeError):self.current=None
            self.received=time.monotonic();self.stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9

        def record(self,request,response):
            try:
                age=self.get_clock().now().nanoseconds*1e-9-self.stamp
                if self.current is None or self.stamp<=0 or not -.1<=age<=1. or time.monotonic()-self.received>1.:
                    raise ValueError('No complete fresh joint state')
                self.store.put(self.pose_name,self.current,self.replace)
                response.success=True;response.message=self.pose_name
            except (OSError,ValueError,TypeError,yaml.YAMLError) as e:response.success=False;response.message=str(e)
            return response

        def list_poses(self,request,response):
            try:response.message=json.dumps(self.store.all());response.success=True
            except (OSError,ValueError,TypeError,yaml.YAMLError) as e:response.message=str(e);response.success=False
            return response

    rclpy.init(args=args);node=None
    try:node=Teacher();rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        if node:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
