"""Locked atomic pose library. Refuses corrupt files and implicit replacement."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import re
import tempfile
import yaml
from .core import finite


class PoseStore:
    def __init__(self,path):self.path=Path(path).expanduser()

    @contextmanager
    def locked(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.with_name(self.path.name+'.lock').open('a') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX)
            try:yield
            finally:fcntl.flock(stream,fcntl.LOCK_UN)

    def _read(self):
        if not self.path.exists():return {}
        data=yaml.safe_load(self.path.read_text())
        if not isinstance(data,dict) or data.get('schema_version')!=1 or not isinstance(data.get('poses'),dict):raise ValueError('Invalid pose library; refusing overwrite')
        for name,pose in data['poses'].items():self.validate(name,pose)
        return data['poses']

    @staticmethod
    def validate(name,pose):
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',name):raise ValueError('Invalid pose name')
        if not isinstance(pose,dict) or not pose or any(not isinstance(k,str) or not k.strip() for k in pose):raise ValueError('Invalid joint mapping')
        for value in pose.values():finite(value)

    def all(self):
        with self.locked():return self._read()

    def get(self,name):return self.all()[name]

    def put(self,name,pose,replace=False):
        self.validate(name,pose)
        with self.locked():
            poses=self._read()
            if name in poses and not replace:raise ValueError('Pose exists; use --replace')
            poses[name]={k:float(v) for k,v in pose.items()}
            temporary=None
            try:
                with tempfile.NamedTemporaryFile(mode='w',dir=self.path.parent,delete=False) as stream:
                    temporary=Path(stream.name)
                    yaml.safe_dump({'schema_version':1,'poses':poses},stream,sort_keys=False)
                    stream.flush();os.fsync(stream.fileno())
                os.replace(temporary,self.path)
            finally:
                if temporary and temporary.exists():temporary.unlink()
