from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'web_interface'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/web_control.launch.py']),
        (os.path.join('share', package_name, 'templates'), glob('web_interface/templates/*.html')),
        (os.path.join('share', package_name, 'static/css'), glob('web_interface/static/*.css')),
        (os.path.join('share', package_name, 'static/js'), glob('web_interface/static/*.js'))
    ],
    install_requires=[
        'setuptools',
        'flask',
        'flask_socketio',
        'eventlet'
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
            'web_server_node = web_interface.web_server_node:main'
        ],
    },
)
