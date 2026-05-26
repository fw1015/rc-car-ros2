from setuptools import find_packages, setup

package_name = 'robot_sensors'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
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
            'tof_sensor_node = robot_sensors.tof_sensor_node:main',
            'ultrasound_sensor_node = robot_sensors.ultrasound_sensor_node:main'
        ],
    },
)
