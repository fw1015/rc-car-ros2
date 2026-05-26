from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'robot_movement'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py'))
    ],
    install_requires=[
        'setuptools',
        'gpiozero'
    ],
    zip_safe=True,
    maintainer='fwann',
    maintainer_email='fwann@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'servo_node = robot_movement.servo_node:main',
            'esc_node = robot_movement.esc_node:main'
        ],
    },
)
