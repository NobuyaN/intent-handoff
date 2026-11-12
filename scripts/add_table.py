
import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Pose
from shape_msgs.msg import SolidPrimitive
from moveit_msgs.msg import CollisionObject, PlanningScene
from moveit_msgs.srv import ApplyPlanningScene

FRAME_ID = "link_base"

TABLE_SIZE_X = 1.80
TABLE_SIZE_Y = 0.76
TABLE_SIZE_Z = 0.04

TABLE_CENTER_X = 0.835
TABLE_CENTER_Y = 0.0
TABLE_CENTER_Z = -0.02


def main():
    values = [
        TABLE_SIZE_X, TABLE_SIZE_Y, TABLE_SIZE_Z,
        TABLE_CENTER_X, TABLE_CENTER_Y, TABLE_CENTER_Z
    ]

    if any(v is None for v in values):
        raise SystemExit("Enter all measured table values first.")

    if any(v <= 0 for v in values[:3]):
        raise SystemExit("Table dimensions must be positive.")

    rclpy.init()
    node = Node("table_scene_setup")

    try:
        # Connect to MoveIt's planning-scene service
        client = node.create_client(
            ApplyPlanningScene,
            "/apply_planning_scene"
        )

        if not client.wait_for_service(timeout_sec=10.0):
            print("Planning scene service unavailable")
            return

        # Define the table as a collision object
        table = CollisionObject()
        table.header.frame_id = FRAME_ID
        table.id = "experiment_table"

        # Create rectangular box geometry
        box = SolidPrimitive()
        box.type = SolidPrimitive.BOX
        box.dimensions = [
            TABLE_SIZE_X,
            TABLE_SIZE_Y,
            TABLE_SIZE_Z
        ]

        # Position the center of the box
        pose = Pose()
        pose.position.x = TABLE_CENTER_X
        pose.position.y = TABLE_CENTER_Y
        pose.position.z = TABLE_CENTER_Z
        pose.orientation.w = 1.0

        table.primitives.append(box)
        table.primitive_poses.append(pose)
        table.operation = CollisionObject.ADD

        # Apply only this change to the existing scene
        scene = PlanningScene()
        scene.is_diff = True
        scene.robot_state.is_diff = True
        scene.world.collision_objects.append(table)

        request = ApplyPlanningScene.Request()
        request.scene = scene

        future = client.call_async(request)

        rclpy.spin_until_future_complete(
            node,
            future,
            timeout_sec=10.0
        )

        if not future.done():
            print("Planning scene update timed out")
        elif future.exception() is not None:
            print(f"Service error: {future.exception()}")
        elif future.result().success:
            print("Table added to MoveIt planning scene!")
        else:
            print("MoveIt rejected the scene update")

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
