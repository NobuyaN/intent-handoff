import os 
import yaml

from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder

def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)

    try:
        with open(absolute_file_path, "r") as file:
            return yaml.safe_load(file)
    except EnvironmentError:
        return None


def generate_launch_description():
    moveit_config = MoveItConfigsBuilder(
        "firefighter", 
        package_name="mycobot_280_moveit2"
    ).to_moveit_configs()

    servo_yaml = load_yaml("moveit_servo", "config/servo.yaml")
    servo_params = {"moveit_servo": servo_yaml}

    rviz_config_file = (
        get_package_share_directory("moveit_servo") + "/config/demo_rviz_config.rviz"
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["d", rviz_config_file],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
        ],
    )

    servo_node = Node(
        package="moveit_servo",
        executable="servo_node_main",
        parameters=[
            servo_params,
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
        ],
        output="screen",
    )

    return LaunchDescription(
        [
            rviz_node,
            servo_node,
        ]
    )



