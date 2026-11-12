#later change to Class-based node

import time
import rclpy
import random
import sys

from rclpy.node import Node
from moveit_msgs.srv import GetMotionPlan
from moveit_msgs.msg import (
    Constraints,
    JointConstraint,
    DisplayTrajectory,
    MoveItErrorCodes
)


START_POSE_RADIANS = [
    (0.43752584, -0.24472938, 0.30905879, 0.33088925, 0.11788642, 0.55317456, 0.47457147),
    (-0.13167116, -0.11488558, -0.21735357, 0.45080626, -0.03440911, 0.54582298, -0.48244271),
    (0.00329614, -0.26822230, -0.00083794, 0.43854401, -0.00032789, 0.68816298, -0.16096060)
]


def main():
    pose_id = int(sys.argv[1]) - 1
    assert 0 <= pose_id < 3, "Choose pose 1, 2, or 3"

    chosen_pose = START_POSE_RADIANS[pose_id]
    print(f"Selected starting position: {pose_id + 1}")
    # chosen_pose = random.choice(START_POSE_RADIANS)

    rclpy.init()
    node = Node("reset_planning_test")

    client = node.create_client(
        GetMotionPlan,
        "/plan_kinematic_path"
    )

    display_pub = node.create_publisher(
        DisplayTrajectory,
        "/display_planned_path",
        10
    )

    if not client.wait_for_service(timeout_sec=10.0):
        print("MoveIt planning service not available")
        node.destroy_node()
        rclpy.shutdown()
        
        return

    req = GetMotionPlan.Request()
    plan = req.motion_plan_request

    plan.group_name = "xarm7"
    plan.start_state.is_diff = True
    plan.num_planning_attempts = 5
    plan.allowed_planning_time = 5.0
    plan.max_velocity_scaling_factor = 0.1
    plan.max_acceleration_scaling_factor = 0.1

    goal = Constraints()

    for i, pose in enumerate(chosen_pose):
        # xarm7_ros2_controljoint#
        constraint = JointConstraint(
            joint_name=f"joint{i+1}",
            position=pose,
            tolerance_above=0.01,
            tolerance_below=0.01,
            weight=1.0
        )

        goal.joint_constraints.append(constraint)

    plan.goal_constraints = [goal]

    print("Planning to recorded starting position...")

    future = client.call_async(req)

    rclpy.spin_until_future_complete(
        node,
        future,
        timeout_sec=35.0
    )

    if not future.done():
        print("Motion planning not done")
    elif future.exception() is not None:
        print(f"Service error: {future.exception()}")
    else:
        result = future.result().motion_plan_response

        if result.error_code.val == MoveItErrorCodes.SUCCESS:
            print("Planning successful")

            display = DisplayTrajectory()
            display.trajectory_start = result.trajectory_start
            display.trajectory.append(result.trajectory)

            display_pub.publish(display)
            time.sleep(2.0)

        else:
            print(
                "Planning failed, error code:",
                result.error_code.val
            )
        
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()















