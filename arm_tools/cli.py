import argparse
import json
import math
from pathlib import Path
import tempfile
import yaml
from .core import ArmProfile
from .store import PoseStore


def main(argv=None):
    p=argparse.ArgumentParser(description='Teach named joint poses and jog within configured limits')
    p.add_argument('--profile');p.add_argument('--file',default='~/.ros/arm_poses.yaml')
    sub=p.add_subparsers(dest='command',required=True);sub.add_parser('demo');sub.add_parser('list')
    for cmd in ['show','teach','move','jog']:
        s=sub.add_parser(cmd)
        if cmd!='jog':s.add_argument('name')
        else:s.add_argument('joint');s.add_argument('delta',type=float)
        if cmd=='teach':s.add_argument('--replace',action='store_true')
        if cmd in ['teach','move','jog']:
            s.add_argument('--timeout',type=float,default=10.);s.add_argument('--states',default='/joint_states')
        if cmd in ['move','jog']:
            s.add_argument('--duration',type=float,default=3.);s.add_argument('--action',default='/arm_controller/follow_joint_trajectory')
    a=p.parse_args(argv)
    try:
        if a.command=='demo':
            profile=ArmProfile({'joint1':{'min':-1.,'max':1.}})
            pose=profile.jog({'joint1':0.},'joint1',.1)
            with tempfile.TemporaryDirectory() as d:
                store=PoseStore(Path(d)/'poses.yaml');store.put('taught',pose);assert store.get('taught')==pose
            print(pose);return 0
        store=PoseStore(a.file)
        if a.command=='list':print(json.dumps(store.all(),indent=2));return 0
        if a.command=='show':print(json.dumps(store.get(a.name),indent=2));return 0
        if not a.profile:raise ValueError('--profile is required for teaching or motion')
        profile=ArmProfile.load(a.profile)
        if not math.isfinite(a.timeout) or a.timeout<=0:raise ValueError('Timeout must be positive')
        duration=getattr(a,'duration',3.)
        if not math.isfinite(duration) or duration<=0:raise ValueError('Duration must be positive')
        from .ros import execute
        execute(a.command,profile,store,getattr(a,'name',None),getattr(a,'joint',None),getattr(a,'delta',None),
                duration,a.timeout,getattr(a,'action','/arm_controller/follow_joint_trajectory'),a.states,getattr(a,'replace',False))
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,ImportError,yaml.YAMLError) as e:p.exit(2,str(e)+'\n')
    return 0


if __name__=='__main__':raise SystemExit(main())
