import cv2

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Could not open camera")
    exit()

while True:
    ret, frame = camera.read()

    if not ret:
        print("Could not read camera")
        break

    # Draw a rectangle on the image
    cv2.rectangle(frame, (100, 100), (300, 300), (0, 255, 0), 1)

    cv2.imshow("C950 Camera", frame)

    if cv2.waitKey(1) == 27:  # ESC key
        break

camera.release()
cv2.destroyAllWindows()