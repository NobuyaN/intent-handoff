import rclpy
from rclpy.node import Node

from geometry_msgs.msg import TwistStamped
from std_msgs.msg import String
from std_srvs.srv import Trigger

class TrialManager(Node):
    def __init__(self):
        super().__init__("trial_manager")
        self.get_logger().info("Trial manager initialized: IDLE")

        self.state = "IDLE"
        self.start_time = None

        self.start_service = self.create_service(
            Trigger,
            "/start_trial",
            self.start_trial_callback
        )

        self.twist_sub = self.create_subscription(
            TwistStamped,
            "/teleop_twist",
            self.twist_callback,
            10
        )

        self.state_pub = self.create_publisher(
            String,
            "/trial_state",
            10
        )

    def twist_callback(self, msg):
        moving = (
            abs(msg.twist.linear.x) > 0.001 or 
            abs(msg.twist.linear.y) > 0.001 or 
            abs(msg.twist.linear.z) > 0.001 
        )

        if self.state == "ARMED" and moving:
            self.state = "TELEOP"

            msg = String()
            msg.data = self.state
            self.state_pub.publish(msg)

            self.get_logger().info("State: TELEOP")

    def start_trial_callback(self, req, res):
        self.state = "ARMED"

        res.success = True
        res.message = "Trial armed"

        msg = String()
        msg.data = self.state
        self.state_pub.publish(msg)

        self.get_logger().info("State: ARMED")

        return res


def main(args=None):
    rclpy.init(args=args)

    node = TrialManager()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()