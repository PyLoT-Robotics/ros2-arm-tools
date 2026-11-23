"""Validated joint profiles, captured poses and bounded jog targets."""
import math
from pathlib import Path
import yaml


def finite(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('Joint values must be finite numbers')
    return float(value)


class ArmProfile:
    def __init__(self,joints):
        if not isinstance(joints,dict) or not joints:raise ValueError('A nonempty joint profile is required')
        self.joints={}
        for name,spec in joints.items():
            if not isinstance(name,str) or not name.strip() or not isinstance(spec,dict):raise ValueError('Invalid joint definition')
            low,high=finite(spec['min']),finite(spec['max'])
            kind=spec.get('type','revolute')
            if low>=high or kind not in ['revolute','prismatic']:raise ValueError('Invalid limits or joint type')
            self.joints[name]={'min':low,'max':high,'type':kind}

    @classmethod
    def load(cls,path):
        data=yaml.safe_load(Path(path).read_text())
        if not isinstance(data,dict):raise ValueError('Profile must be a mapping')
        return cls(data['joints'])

    def validate(self,pose):
        if not isinstance(pose,dict) or set(pose)!=set(self.joints):raise ValueError('Pose must contain exactly the configured joints')
        result={}
        for name,spec in self.joints.items():
            value=finite(pose[name])
            if not spec['min']<=value<=spec['max']:raise ValueError('Joint out of range: '+name)
            result[name]=value
        return result

    def capture(self,names,positions):
        if len(names)!=len(positions) or len(set(names))!=len(names):raise ValueError('Malformed JointState')
        values=dict(zip(names,positions))
        if not set(self.joints)<=set(values):raise ValueError('Missing joint state; no zero-position fallback')
        return self.validate({name:values[name] for name in self.joints})

    def jog(self,current,joint,delta):
        target=self.validate(current)
        if joint not in target:raise ValueError('Unknown joint: '+joint)
        target[joint]+=finite(delta)
        return self.validate(target)


def trajectory_values(profile,pose,duration):
    duration=finite(duration)
    if not 0<duration<=86400:raise ValueError('Duration must be in (0,86400] seconds')
    pose=profile.validate(pose)
    return list(profile.joints),[pose[name] for name in profile.joints],duration
