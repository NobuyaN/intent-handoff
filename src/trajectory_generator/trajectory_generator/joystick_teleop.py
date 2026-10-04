import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Joy
from geometry_msgs.msg import TwistStamped

class JoystickTeleop(Node):
    def __init__(self): 
        super().__init__("joystick_teleop")
        self.get_logger().info("Joystick teleop initialized")

        self.joystick_sub = self.create_subscription(
            Joy,
            "/joy",
            self.joy_callback,
            10
        )

        self.twist_pub = self.create_publisher(
            TwistStamped,
            "/teleop_twist",
            10
        )

    def joy_callback(self, msg):
        twist = TwistStamped()
        twist.header.stamp = self.get_clock().now().to_msg()
        twist.header.frame_id = "g_base"

        speed = 0.05

        twist.twist.linear.x = msg.axes[1] * speed 
        twist.twist.linear.y = msg.axes[0] * speed 
        twist.twist.linear.z = msg.axes[4] * speed

        self.twist_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)

    node = JoystickTeleop()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()

