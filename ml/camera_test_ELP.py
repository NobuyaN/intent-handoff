import cv2

cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)

if not cap.isOpened():
    raise RuntimeError("Could not open ELP camera")

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

print("Width:", cap.get(cv2.CAP_PROP_FRAME_WIDTH))
print("Height:", cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print("FPS:", cap.get(cv2.CAP_PROP_FPS))

while True:
    ret, frame = cap.read()

    if not ret:
        print("Failed to capture frame")
        break

    color_ranges = {
        "red": [()]
    }


    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mask1 = 

    cv2.imshow("ELP Camera", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()