import cv2
import numpy as np

CAMERA_INDEX = 4

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

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    for name, bound in colors.items():

        if name == "Red":
            mask1 = makeMask(
                hsv, 
                bound[0][0], 
                bound[0][1]
            )

            mask2 = makeMask(
                hsv, 
                bound[1][0], 
                bound[1][1]
            )

            mask_red = cv2.bitwise_or(mask1, mask2)

        

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()