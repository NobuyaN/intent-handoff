import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseArray, Pose

from visualization_msgs.msg import Marker, MarkerArray

class TargetManager(Node):
    def __init__(self):
        super().__init__("target_manager")  
        self.get_logger().info("Target Manager node started")

        self.publisher = self.create_publisher(
            PoseArray, 
            "/target_position",
            10)

        self.marker_publisher = self.create_publisher(
            MarkerArray,
            "/target_marker",
            10
        )

        self.timer = self.create_timer(
            1.0,
            self.publish_timer_callback
        )

        self.targets = [
            [0.2, 0.1, 0.15], # red
            [0.3, 0.2, 0.15], # green
            [0.1, -0.1, 0.15] # blue 
        ]


    def publish_timer_callback(self):

        msg = PoseArray()
        msg.header.frame_id = "base_link"

        for target in self.targets:

            pose = Pose()

            pose.position.x = target[0]
            pose.position.y = target[1]
            pose.position.z = target[2]
            pose.orientation.x = 0.0
            pose.orientation.y = 0.0
            pose.orientation.z = 0.0
            pose.orientation.w = 1.0

            msg.poses.append(pose)

        self.publisher.publish(msg)

        marker_array = MarkerArray()

        colors = [
            (1.0, 0.0, 0.0), # red
            (0.0, 1.0, 0.0), # green
            (0.0, 0.0, 1.0) # blue
        ]

        for i, position in enumerate(self.targets):

            marker = Marker()

            marker.header.frame_id = "base_link"
            marker.id = i
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD

            marker.pose.position.x = position[0]
            marker.pose.position.y = position[1]
            marker.pose.position.z = position[2]
            marker.pose.orientation.x = 0.0
            marker.pose.orientation.y = 0.0
            marker.pose.orientation.z = 0.0
            marker.pose.orientation.w = 1.0

            marker.scale.x = 0.04
            marker.scale.y = 0.04
            marker.scale.z = 0.04

            marker.color.r = colors[i][0] 
            marker.color.g = colors[i][1] 
            marker.color.b = colors[i][2] 

            marker_array.markers.append(marker)

        self.marker_publisher.publish(marker_array)


def main(args=None):
    rclpy.init(args=args)

    node = TargetManager()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
