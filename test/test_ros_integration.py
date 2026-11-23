"""Optional isolated DDS tests with synthetic publishers; no hardware access."""
import os
import signal
import subprocess
import sys
import time
import json
import pytest
rclpy=pytest.importorskip('rclpy')
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

class Harness:
    def __init__(self,package,domain,parameters):
        self.context=Context();rclpy.init(context=self.context,domain_id=domain)
        self.node=Node(package+'_test',context=self.context)
        self.executor=SingleThreadedExecutor(context=self.context);self.executor.add_node(self.node)
        self.env=dict(os.environ,ROS_DOMAIN_ID=str(domain))
        args=[sys.executable,'-c',f'from {package}.node import main; main()','--ros-args']
        for key,value in parameters.items():args+=['-p',f'{key}:={value}']
        self.process=subprocess.Popen(args,env=self.env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)

    def wait(self,predicate,publish=None,timeout=8.):
        end=time.monotonic()+timeout
        while not predicate() and time.monotonic()<end:
            assert self.process.poll() is None,self.process.stdout.read().decode()
            if publish:publish()
            self.executor.spin_once(timeout_sec=.025)
        assert predicate()

    def call(self,name):
        from std_srvs.srv import Trigger
        client=self.node.create_client(Trigger,name);self.wait(client.service_is_ready)
        future=client.call_async(Trigger.Request());self.wait(future.done)
        return future.result()

    def close(self):
        try:os.killpg(self.process.pid,signal.SIGINT)
        except ProcessLookupError:pass
        try:self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid,signal.SIGKILL);self.process.wait(timeout=2)
        output=self.process.stdout.read().decode();self.process.stdout.close()
        self.executor.shutdown();self.node.destroy_node();rclpy.shutdown(context=self.context)
        assert self.process.returncode==0,output

def test_real_teaching_and_synthetic_trajectory_action(tmp_path):
    from sensor_msgs.msg import JointState
    from rclpy.action import ActionServer
    from control_msgs.action import FollowJointTrajectory
    from arm_tools.store import PoseStore
    profile=tmp_path/'profile.yaml';profile.write_text('joints: {joint1: {min: -1.0, max: 1.0}}')
    library=tmp_path/'poses.yaml';goals=[]
    h=Harness('arm_tools',83,{'profile':str(profile),'file':str(library)})
    try:
        pub=h.node.create_publisher(JointState,'/joint_states',10)
        def send():
            m=JointState();m.header.stamp=h.node.get_clock().now().to_msg();m.name=['joint1'];m.position=[.25];pub.publish(m)
        h.wait(lambda:pub.get_subscription_count()>0)
        for _ in range(5):send();h.executor.spin_once(timeout_sec=.03)
        result=h.call('/arm_tools/record');assert result.success,result.message
        assert PoseStore(library).get('taught')=={'joint1':.25}
        def execute(handle):
            goals.append(handle.request.trajectory);handle.succeed();return FollowJointTrajectory.Result(error_code=0)
        server=ActionServer(h.node,FollowJointTrajectory,'/arm_tools_test/follow_joint_trajectory',execute_callback=execute)
        child=subprocess.Popen([sys.executable,'-m','arm_tools.cli','--profile',str(profile),'--file',str(library),
            'move','taught','--action','/arm_tools_test/follow_joint_trajectory','--timeout','5'],env=h.env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        try:h.wait(lambda:child.poll() is not None,timeout=8.)
        finally:
            if child.poll() is None:child.kill();child.wait()
        output=child.communicate()[0].decode();assert child.returncode==0,output
        assert goals and goals[-1].joint_names==['joint1'] and list(goals[-1].points[0].positions)==[.25]
        child=subprocess.Popen([sys.executable,'-m','arm_tools.cli','--profile',str(profile),'--file',str(library),
            'jog','joint1','0.02','--action','/arm_tools_test/follow_joint_trajectory','--timeout','5'],
            env=h.env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        try:h.wait(lambda:child.poll() is not None,publish=send,timeout=8.)
        finally:
            if child.poll() is None:child.kill();child.wait()
        output=child.communicate()[0].decode();assert child.returncode==0,output
        assert list(goals[-1].points[0].positions)==pytest.approx([.27])
        server.destroy()
    finally:h.close()
