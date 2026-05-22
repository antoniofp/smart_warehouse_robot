import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'maze_nav'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # LÍNEA AGREGADA: Le dice a ROS 2 dónde instalar los archivos launch
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='manuel',
    maintainer_email='you@example.com',
    description='Navegacion autonoma para laberinto con Lyapunov y A*',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'wall_follower = maze_nav.wall_follower:main',
            'global_planner = maze_nav.global_planner:main',
            'explore_bridge = maze_nav.explore_bridge:main',
            'tf_to_pose = maze_nav.tf_to_pose:main',
        ],
    },
)
