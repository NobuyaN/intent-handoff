import sys
import time
import rclpy

from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from sensor_msgs.msg import JointState
from std_srvs.srv import SetBool

from moveit_msgs.srv import GetMotionPlan, GetPlanningScene
from moveit_msgs.action import ExecuteTrajectory
from moveit_msgs.msg import (
    Constraints,
    JointConstraint,
    DisplayTrajectory,
    MoveItErrorCodes,
    PlanningSceneComponents,
)


START_POSE_RADIANS = [
    (0.43752584, -0.24472938, 0.30905879, 0.33088925, 0.11788642, 0.55317456, 0.47457147),
    (-0.13167116, -0.11488558, -0.21735357, 0.45080626, -0.03440911, 0.54582298, -0.48244271),
    (0.00329614, -0.26822230, -0.00083794, 0.43854401, -0.00032789, 0.68816298, -0.16096060),
]

JOINT_NAMES = [f"joint{i}" for i in range(1, 8)]
CONTROLLER = "xarm7_traj_controller"


class ResetPlanner(Node):
    def __init__(self, node_name="reset_planner", **node_kwargs):
        super().__init__(node_name, **node_kwargs)
        self.plan_client = self.create_client(GetMotionPlan, "/plan_kinematic_path")
        self.scene_client = self.create_client(GetPlanningScene, "/get_planning_scene")
        self.servo_client = self.create_client(SetBool, "/servo_server/pause_servo")
        self.display_pub = self.create_publisher(DisplayTrajectory, "/display_planned_path", 10)
        self.execution_client = ActionClient(self, ExecuteTrajectory, "/execute_trajectory")

    def destroy_node(self):
        self.execution_client.destroy()
        return super().destroy_node()

    def wait_for_future(self, future, timeout, description):
        rclpy.spin_until_future_complete(
            self, future, timeout_sec=timeout
        )

        if not future.done():
            raise RuntimeError(f"{description} timed out")

        if future.exception() is not None:
            raise RuntimeError(
                f"{description}: {future.exception()}"
            )

        return future.result()

    def read_joint_state(self):
        received = []

        def callback(msg):
            received.append(msg)

        sub = self.create_subscription(
            JointState, "/joint_states", callback, 10
        )

        try:
            deadline = time.monotonic() + 5.0

            while not received and time.monotonic() < deadline:
                rclpy.spin_once(self, timeout_sec=0.1)

            if not received:
                raise RuntimeError("No fresh joint states")

            msg = received[-1]
            positions = dict(zip(msg.name, msg.position))

            if not all(name in positions for name in JOINT_NAMES):
                raise RuntimeError("Missing xArm7 joints")

            return positions

        finally:
            self.destroy_subscription(sub)

    def pause_servo(self):
        client = self.servo_client

        if not client.wait_for_service(timeout_sec=5.0):
            raise RuntimeError("Servo pause service unavailable")

        request = SetBool.Request()
        request.data = True

        response = self.wait_for_future(
            client.call_async(request), 5.0, "Servo pause"
        )

        if not response.success:
            raise RuntimeError(
                f"Servo pause failed: {response.message}"
            )

        print("Servo paused successfully")

    def check_table(self):
        client = self.scene_client

        if not client.wait_for_service(timeout_sec=5.0):
            raise RuntimeError("Planning scene unavailable")

        request = GetPlanningScene.Request()
        request.components.components = (
            PlanningSceneComponents.WORLD_OBJECT_GEOMETRY
        )

        response = self.wait_for_future(
            client.call_async(request), 5.0, "Planning scene retrieval"
        )

        tables = [
            obj for obj in response.scene.world.collision_objects
            if obj.id == "experiment_table"
        ]

        if len(tables) != 1 or not tables[0].primitives:
            raise RuntimeError("Table collision box missing")

        table = tables[0]
        actual_size = list(table.primitives[0].dimensions)
        expected_size = [1.80, 0.76, 0.04]

        if any(
            abs(a - b) > 0.005
            for a, b in zip(actual_size, expected_size)
        ) or len(actual_size) != 3:
            raise RuntimeError("Table dimensions do not match")

        center = table.pose.position
        expected_center = (0.835, 0.0, -0.02)

        if any(
            abs(a - b) > 0.01
            for a, b in zip(
                (center.x, center.y, center.z),
                expected_center
            )
        ):
            raise RuntimeError("Table position does not match")

        if table.header.frame_id not in ("world", "link_base"):
            raise RuntimeError("Unexpected table reference frame")

        print("Table collision geometry verified")

    def reset(self, pose_id, execute=False, *, confirm_execution=None):
        """Return MotionPlanResponse on success, None on declined execution.

        pose_id is 1, 2, or 3. Planning is the default. execute=True retains
        interactive confirmation unless a callback accepting pose_id and returning
        a boolean is supplied. Failures raise RuntimeError to the caller.
        This method spins the node synchronously; do not call it in a ROS callback.
        """
        if type(pose_id) is not int or pose_id not in (1, 2, 3):
            raise ValueError("pose_id must be 1, 2, or 3")
        pose_id -= 1
        chosen_pose = START_POSE_RADIANS[pose_id]
        print(f"Selected starting position: {pose_id + 1}")
        print(f"Physical execution: {execute}")

        # 1. Prepare physical execution
        if execute:
            self.pause_servo()
            self.check_table()

            time.sleep(0.5)
            self.read_joint_state()
            print("Fresh robot joint states received")

        # 2. Connect to MoveIt planning service
        client = self.plan_client
        display_pub = self.display_pub

        if not client.wait_for_service(timeout_sec=10.0):
            raise RuntimeError("MoveIt planning unavailable")

        # 3. Construct planning request
        req = GetMotionPlan.Request()
        plan = req.motion_plan_request

        plan.group_name = "xarm7"
        plan.start_state.is_diff = True
        plan.num_planning_attempts = 5
        plan.allowed_planning_time = 5.0
        plan.max_velocity_scaling_factor = 0.1
        plan.max_acceleration_scaling_factor = 0.1

        goal = Constraints()

        for i, angle in enumerate(chosen_pose):
            goal.joint_constraints.append(
                JointConstraint(
                    joint_name=JOINT_NAMES[i],
                    position=angle,
                    tolerance_above=0.01,
                    tolerance_below=0.01,
                    weight=1.0
                )
            )

        plan.goal_constraints = [goal]

        # 4. Ask MoveIt to generate trajectory
        print("Planning reset trajectory...")

        response = self.wait_for_future(
            client.call_async(req), 35.0, "Motion planning"
        )

        result = response.motion_plan_response

        if result.error_code.val != MoveItErrorCodes.SUCCESS:
            raise RuntimeError(
                f"Planning failed: {result.error_code.val}"
            )

        trajectory = result.trajectory
        joint_traj = trajectory.joint_trajectory

        if not joint_traj.points:
            raise RuntimeError("Planned trajectory is empty")

        print("Planning successful!")

        # 5. Visualize in RViz
        display = DisplayTrajectory()
        display.trajectory_start = result.trajectory_start
        display.trajectory.append(trajectory)

        display_pub.publish(display)
        time.sleep(2.0)

        if not execute:
            print("Planning-only test completed")
            return result

        # 6. Connect to trajectory execution action
        action_client = self.execution_client

        if not action_client.wait_for_server(timeout_sec=10.0):
            raise RuntimeError("Execution server unavailable")

        last = joint_traj.points[-1].time_from_start
        duration = last.sec + last.nanosec * 1e-9

        print(f"Planned duration: {duration:.2f} seconds")
        print("Review this trajectory in RViz.")
        print("Verify the real robot's path is clear.")

        if confirm_execution is not None:
            confirmed = confirm_execution(pose_id + 1)
        else:
            confirmed = input(
                f"Type EXECUTE to move xArm7 to Pose {pose_id + 1}: "
            ) == "EXECUTE"
        if not confirmed:
            print("Physical execution canceled")
            return None

        # 7. Check fresh joints after confirmation, immediately before execution
        current = self.read_joint_state()

        first_point = dict(zip(
            joint_traj.joint_names,
            joint_traj.points[0].positions
        ))

        max_start_error = max(
            abs(current[name] - first_point[name])
            for name in JOINT_NAMES
        )

        if max_start_error > 0.05:
            raise RuntimeError(
                "Robot moved or planned start state is stale"
            )

        print(f"Start-state error: {max_start_error:.4f} rad")

        # 8. Send trajectory to MoveIt
        execute_goal = ExecuteTrajectory.Goal()
        execute_goal.trajectory = trajectory
        execute_goal.controller_names = [CONTROLLER]

        goal_handle = self.wait_for_future(
            action_client.send_goal_async(execute_goal),
            10.0,
            "Execution goal submission"
        )

        if not goal_handle.accepted:
            raise RuntimeError("Execution goal rejected")

        print("Physical robot executing trajectory...")

        # 9. Wait for action completion
        result_future = goal_handle.get_result_async()

        try:
            execution = self.wait_for_future(
                result_future,
                max(30.0, duration * 2.0 + 15.0),
                "Trajectory execution"
            )
        except RuntimeError:
            print("Execution timeout/error. Requesting cancellation.")
            cancel_future = goal_handle.cancel_goal_async()
            try:
                self.wait_for_future(
                    cancel_future, 5.0, "Execution cancellation"
                )
            except RuntimeError:
                print("Cancellation not confirmed!")
            raise

        if (
            execution.status != GoalStatus.STATUS_SUCCEEDED
            or execution.result.error_code.val
                != MoveItErrorCodes.SUCCESS
        ):
            raise RuntimeError(
                "Trajectory execution failed: "
                f"status={execution.status}, "
                f"error={execution.result.error_code.val}"
            )

        print("MoveIt reports execution successful!")

        # 10. Verify actual final joint angles
        actual = self.read_joint_state()

        errors = [
            abs(actual[name] - target)
            for name, target in zip(JOINT_NAMES, chosen_pose)
        ]

        print("Final joint errors (radians):")
        for name, error in zip(JOINT_NAMES, errors):
            print(f"  {name}: {error:.5f}")

        if max(errors) > 0.05:
            raise RuntimeError(
                "Robot did not reach the requested pose tolerance"
            )

        print("RESET COMPLETE: final joint positions verified")

        return result


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("1", "2", "3"):
        raise SystemExit(
            "Usage: python3 plan_reset.py <1|2|3> [--execute]"
        )

    if any(arg != "--execute" for arg in sys.argv[2:]):
        raise SystemExit("Unknown command-line option")

    pose_id = int(sys.argv[1])
    execute = "--execute" in sys.argv[2:]
    rclpy.init()
    node = ResetPlanner()
    try:
        node.reset(pose_id, execute=execute)
    except (RuntimeError, KeyboardInterrupt) as error:
        print(f"RESET NOT VERIFIED: {error}")
        print("Check robot state before any new command.")
        return 1
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
