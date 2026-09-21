import rclpy
from rclpy.node import Node

class TargetManager(Node):
    def __init__(self):
        super().__init__("target_manager")  
        self.get_logger().info("Target Manager node started")


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
