from launch import LaunchDescription
from launch.actions import OpaqueFunction, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from uf_ros_lib.moveit_configs_builder import MoveItConfigsBuilder


def launch_setup(context, *args, **kwargs):

    moveit_config = MoveItConfigsBuilder(
        context=context,
        controllers_name="controllers",
        robot_ip=LaunchConfiguration("robot_ip"),
        dof=LaunchConfiguration("dof"),
        robot_type="xarm",
        ros2_control_plugin="uf_robot_hardware/UFRobotSystemHardware",
    ).to_moveit_configs()

    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {"allow_trajectory_execution": True},
        ],
    )

    return [move_group]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            "robot_ip",
            default_value="192.168.1.211"
        ),
        DeclareLaunchArgument(
            "dof",
            default_value="7"
        ),
        OpaqueFunction(function=launch_setup),
    ])