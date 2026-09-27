import rclpy
from rclpy.node import Node

from geometry_msgs.msg import TwistStamped
from experiment_interfaces.msg import TrialState
from std_srvs.srv import Trigger

import random

class TrialManager(Node):
    def __init__(self):
        super().__init__("trial_manager")
        self.get_logger().info("Trial manager initialized: IDLE")

        self.state = "IDLE"
        self.start_time = None
        self.trial_id = 0
        self.target_label = ""

        self.target_labels = [
            "red",
            "green",
            "blue"
        ]

        self.start_service = self.create_service(
            Trigger,
            "/start_trial",
            self.start_trial_callback
        )

        self.stop_service = self.create_service(
            Trigger,
            "/stop_trial",
            self.stop_trial_callback
        )

        self.twist_sub = self.create_subscription(
            TwistStamped,
            "/teleop_twist",
            self.twist_callback,
            10
        )

        self.state_pub = self.create_publisher(
            TrialState,
            "/trial_state",
            10
        )

    def publish_state(self):
        msg = TrialState()
        msg.state = self.state
        msg.trial_id = self.trial_id
        msg.target_label = self.target_label

        self.state_pub.publish(msg)


    def twist_callback(self, msg):
        moving = (
            abs(msg.twist.linear.x) > 0.001 or 
            abs(msg.twist.linear.y) > 0.001 or 
            abs(msg.twist.linear.z) > 0.001 
        )

        if self.state == "ARMED" and moving:
            self.state = "TELEOP"

            self.publish_state()
            
            self.get_logger().info("State: TELEOP")

    def start_trial_callback(self, req, res):
        self.state = "ARMED"
        self.trial_id += 1
        self.target_label = random.choice(self.target_labels)

        res.success = True
        res.message = "Trial armed"

        self.publish_state()

        self.get_logger().info(
            f"Trial: {self.trial_id} | "    
            f"Target: {self.target_label} | "    
            f"State: ARMED"
        )

        return res


    def stop_trial_callback(self, req, res):
        self.state = "COMPLETE"

        res.success = True
        res.message = "Trial completed"

        self.publish_state()

        self.get_logger().info("State: COMPLETE")

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