from glob import glob
from setuptools import setup,find_packages
setup(name='arm_tools',version='0.1.0',description='Named joint poses, teaching and bounded joint jogging',python_requires='>=3.10',
      packages=find_packages(exclude=['test']),install_requires=['PyYAML'],extras_require={'test': ['pytest']},
      license='Apache-2.0',maintainer='PyLoT Robotics',maintainer_email='163533636+PyLoT-Robotics@users.noreply.github.com',
      data_files=[('share/ament_index/resource_index/packages',['resource/arm_tools']),
                  ('share/arm_tools',['package.xml']),('share/arm_tools/config',glob('config/*')),
                  ('share/arm_tools/launch',glob('launch/*.py'))],
      entry_points={'console_scripts':['ros2-arm-tools = arm_tools.cli:main','arm_tools_node = arm_tools.node:main']})
