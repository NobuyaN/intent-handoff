import cv2
import numpy as np

# find CAMERA_INDEX using v4l2-ctl --list-devices in terminal

CAMERA_INDEX = 0

def makeMask(hsv, lower, upper):
    return cv2.inRange(
        hsv,
        lower,
        upper
    )


cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)

if not cap.isOpened():
    print("Error: Webcam not opened.")
    exit()

cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"YUYV"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)

colors = {
    "Red": [
        (np.array([0, 100, 100]), np.array([10, 255, 255])),
        (np.array([170, 100, 100]), np.array([179, 255, 255]))
    ],
    "Green": [
        (np.array([35, 100, 100]), np.array([85, 255, 255]))
    ],
    "Blue": [
        (np.array([100, 100, 100]), np.array([140, 255, 255]))
    ]
}

while True:
    ret, frame = cap.read()

    if not ret:
        print("Could not read frame")
        break

    h, w = frame.shape[:2]
    left_frame = frame[:, :w // 2]

    cv2.imshow("ZED-M Left", left_frame)

    hsv = cv2.cvtColor(left_frame, cv2.COLOR_BGR2HSV)

    for name, bound in colors.items():

        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)

        for lower, upper in bound:
            mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower, upper))

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if contours:
            contour = max(contours, key=cv2.contourArea)

            if cv2.contourArea(contour) > 300:
                M = cv2.moments(contour)

                if M["m00"] == 0:
                    continue

                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])

                cv2.drawContours(frame, [contour], -1, (0, 255, 255), 2)
                cv2.circle(frame, (cx, cy), 5, (255, 255, 255), -1)

                cv2.putText(
                    frame,
                    f"{name}: ({cx}, {cy})",
                    (cx + 10, cy - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )

    cv2.imshow("Ball Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()