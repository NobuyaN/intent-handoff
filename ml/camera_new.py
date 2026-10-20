import cv2

cap = cv2.VideoCapture(5, cv2.CAP_V4L2)

if not cap.isOpened():
    print("Error: Webcam not opened.")
    exit()

while True:
    ret, frame = cap.read()

    if not ret:
        print("Could not read frame")
        break

    cv2.imshow("webcam", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


cap.release()
cv2.destroyAllWindows()


