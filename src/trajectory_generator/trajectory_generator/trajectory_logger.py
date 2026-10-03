import rclpy
from rclpy.node import Node
from rclpy.time import Time

from tf2_ros import Buffer, TransformListener

from experiment_interfaces.msg import TrialState

import csv
from datetime import datetime
from pathlib import Path

class TrajectoryLogger(Node):
    def __init__(self):
        super().__init__("trajectory_logger")
        self.get_logger().info("Trajectory logger initialized")

        self.tf_buffer = Buffer()
        self.is_recording = False
        self.file = None
        self.writer = None

        self.tf_listener = TransformListener(
            self.tf_buffer,
            self
        )

        self.trial_sub = self.create_subscription(
            TrialState,
            "/trial_state",
            self.state_callback,
            10
        )
        
        self.timer = self.create_timer(
            0.05,
            self.log_pose
        )

    def start_new_csv(self, trial_id, target_label):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        data_dir = Path.home() / "intent_handoff_ws" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        filename = f"trial_{trial_id:03d}_{target_label}_{timestamp}.csv"
        file_dir = data_dir / filename

        self.get_logger().info(
            f"Saving trajectory to: {file_dir}"
        )

        self.file = open(
            file_dir, 
            "w", 
            newline = "", 
            encoding = "utf-8"
        )

        self.writer = csv.writer(self.file)

        self.writer.writerow([
            "time_s",
            "x",
            "y",
            "z"
        ])


    def state_callback(self, msg):
        if msg.state == "TELEOP" and not self.is_recording:
            self.start_new_csv(msg.trial_id, msg.target_label)
            self.start_time = self.get_clock().now()
            self.is_recording = True

            self.get_logger().info("Recording started")
        elif msg.state == "COMPLETE" and self.is_recording:
            self.is_recording = False

            if self.file is not None:
                self.file.close()
                self.file = None
                self.writer = None

            self.get_logger().info("Recording stopped")
            

    def log_pose(self):
        if not self.is_recording or self.writer is None:
            return
        
        try:
            transform = self.tf_buffer.lookup_transform(
                "g_base",
                "joint6_flange",
                Time()
            )

            x = transform.transform.translation.x
            y = transform.transform.translation.y
            z = transform.transform.translation.z

            self.get_logger().info(
                f"{x:.3f}, {y:.3f}, {z:.3f}",
            )

            elapsed_time = (
                self.get_clock().now() - self.start_time
            ).nanoseconds / 1e9

            self.writer.writerow([
                elapsed_time, 
                x, 
                y, 
                z
            ])

        except Exception as e:
            self.get_logger().warning(
                f"Could not record pose: {e}"
            )


def main(args=None):
    rclpy.init(args=args)

    node = TrajectoryLogger()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.file is not None:
            node.file.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()