import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped

import sys
import select
import termios
import tty

class KeyboardTeleop(Node):
    def __init__(self):
        super().__init__("keyboard_teleop")
        self.get_logger().info("Keyboard Teleop node started")

        self.publisher = self.create_publisher(
            TwistStamped,
            "/teleop_twist",
            10
        )

        self.timer = self.create_timer(
            0.05,
            self.keyboard_teleop_callback
        )

    def keyboard_teleop_callback(self):

        # temporary code replacing gamepad /joy topic
        key = self.get_key()

        if key == "":
            return 

        msg = TwistStamped()

        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "g_base"

        speed = 0.05

        if key == "w":
            msg.twist.linear.x = speed

        elif key == "s":
            msg.twist.linear.x = -speed

        elif key == "d":
            msg.twist.linear.y = speed

        elif key == "a":
            msg.twist.linear.y = -speed

        elif key == "r":
            msg.twist.linear.z = speed

        elif key == "f":
            msg.twist.linear.z = -speed

        else:
            return

        self.publisher.publish(msg)


    def get_key(self):
        # not my code, have no idea whats happening
        settings = termios.tcgetattr(sys.stdin)

        try:
            tty.setraw(sys.stdin.fileno())

            ready, _, _= select.select(
                [sys.stdin],
                [],
                [],
                0.01
            )

            if ready:
                return sys.stdin.read(1)

            return ""

        finally:    
            termios.tcsetattr(
                sys.stdin,
                termios.TCSADRAIN,
                settings
            )


def main(args=None):
    rclpy.init(args=args)

    node = KeyboardTeleop()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()