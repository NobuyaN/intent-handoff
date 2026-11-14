import argparse
import json
from pathlib import Path

import cv2
import numpy as np

# find CAMERA_INDEX: v4l2-ctl --list-devices
# supported resolutions: v4l2-ctl -d /dev/video0 --list-formats-ext

CAMERA_INDEX = 0
MIN_BALL_AREA = 80  # Original pixels: approximately the old 400 at 2x zoom.
ZOOM = 2.0
TEXT_BLUE = (255, 0, 0)  # OpenCV draws in BGR order.


def draw_label(image, text, position):
    # White outline keeps blue lettering legible on dark backgrounds.
    cv2.putText(image, text, position, cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (255, 255, 255), 4)
    cv2.putText(image, text, position, cv2.FONT_HERSHEY_SIMPLEX,
                0.6, TEXT_BLUE, 2)


def detected_hsv(hsv, contour, color_mask):
    """Representative HSV of matching pixels, accounting for hue wraparound."""
    region = np.zeros(color_mask.shape, dtype=np.uint8)
    cv2.drawContours(region, [contour], -1, 255, cv2.FILLED)
    pixels = hsv[(region != 0) & (color_mask != 0)].astype(np.float64)
    # Red can straddle 179/0; an ordinary hue median could incorrectly yield green.
    angles = pixels[:, 0] * (2 * np.pi / 180)
    reference = np.arctan2(np.sin(angles).mean(), np.cos(angles).mean()) * 180 / (2 * np.pi)
    unwrapped = reference + (pixels[:, 0] - reference + 90) % 180 - 90
    hue = int(np.rint(np.median(unwrapped))) % 180
    saturation, value = np.rint(np.median(pixels[:, 1:], axis=0)).astype(int)
    return hue, int(saturation), int(value)


def makeMask(hsv, lower, upper):
    return cv2.inRange(
        hsv,
        lower,
        upper
    )


colors = {
    "Red": [
        (np.array([0, 100, 100]), np.array([8, 255, 255])),
        (np.array([172, 100, 100]), np.array([179, 255, 255]))
    ],
    "Green": [
        (np.array([30, 180, 100]), np.array([60, 255, 255]))
    ],
    "Blue": [
        (np.array([100, 200, 70]), np.array([140, 255, 255]))
    ]
}

def load_calibration(path):
    return calibration_from_data(json.loads(Path(path).read_text()))


def calibration_from_data(data):
    if data.get("frame_id") != "link_base" or data.get("units") != "m":
        raise ValueError("Calibration must use link_base and meters")
    pixels = np.asarray(data["image_points_px"], dtype=np.float64)
    xy = np.asarray(data["robot_points_m"], dtype=np.float64)
    if (pixels.ndim != 2 or pixels.shape[1] != 2 or len(pixels) < 4
            or xy.shape != pixels.shape or not np.isfinite(pixels).all()
            or not np.isfinite(xy).all()):
        raise ValueError("Need >=4 finite matching [u,v] and [X,Y] points")
    for points in (pixels, xy):
        if np.linalg.matrix_rank(points - points.mean(axis=0)) < 2:
            raise ValueError("Calibration points must not be collinear")
    matrix, _ = cv2.findHomography(pixels, xy, method=0)
    if matrix is None or not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix) < 3:
        raise ValueError("Degenerate calibration")
    size = data["left_image_size"]
    if len(size) != 2 or any(type(v) is not int or v <= 0 for v in size):
        raise ValueError("left_image_size must be [width, height]")
    if not np.isfinite(float(data["plane_z_m"])):
        raise ValueError("Specify the fixed detection height plane_z_m")
    return matrix, tuple(size), cv2.convexHull(pixels.astype(np.float32))


def robot_xy(u, v, calibration):
    matrix, _, hull = calibration
    if cv2.pointPolygonTest(hull, (float(u), float(v)), False) < 0:
        return None
    point = matrix @ np.array([u, v, 1.0])
    if abs(point[2]) < 1e-12:
        return None
    xy = point[:2] / point[2]
    return xy if np.isfinite(xy).all() else None


def main():
    parser = argparse.ArgumentParser(description="Fixed-plane ball positions in link_base; see camera_ZED.md")
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--camera-index", type=int, default=CAMERA_INDEX)
    parser.add_argument("--min-area", type=float, default=MIN_BALL_AREA)
    parser.add_argument("--min-circularity", type=float, default=0.0,
                        help="Optional shape filter, 0 disables it")
    parser.add_argument("--zoom", type=float, default=ZOOM)
    parser.add_argument("--show-masks", action="store_true")
    parser.add_argument("--collect-calibration", type=Path,
                        help="New JSON file; c captures a detected ball, s saves")
    parser.add_argument("--calibration-color", choices=list(colors), default="Red")
    parser.add_argument("--plane-z", type=float, help="Fixed ball-center Z in link_base, meters")
    args = parser.parse_args()
    if not np.isfinite(args.zoom) or args.zoom < 1:
        parser.error("--zoom must be finite and >= 1")
    if not np.isfinite(args.min_area) or args.min_area < 0:
        parser.error("--min-area must be finite and nonnegative")
    if not 0 <= args.min_circularity <= 1:
        parser.error("--min-circularity must be between 0 and 1")
    if args.collect_calibration:
        if args.calibration or args.plane_z is None or not np.isfinite(args.plane_z):
            parser.error("Collection requires --plane-z and no --calibration")
        if args.collect_calibration.exists():
            parser.error("Collection output already exists; choose a new filename")
    collected = dict(frame_id="link_base", units="m", plane_z_m=args.plane_z,
                     image_points_px=[], robot_points_m=[])
    calibration = load_calibration(args.calibration) if args.calibration else None


    cap = cv2.VideoCapture(args.camera_index, cv2.CAP_V4L2)

    if not cap.isOpened():
        raise RuntimeError("Camera not opened")

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"YUYV"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    first_frame = True
    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("Could not read frame")
                break

            h, w = frame.shape[:2]
            if w % 2:
                raise ValueError("Expected side-by-side stereo images with even width")
            left_frame = frame[:, :w // 2]

            h, w = left_frame.shape[:2]
            if first_frame:
                print(f"Actual left image: {w}x{h}; verify input is side-by-side stereo")
                first_frame = False
            if calibration and calibration[1] != (w, h):
                raise ValueError("Image size differs from calibration; recalibrate")

            crop_w = max(1, int(w / args.zoom))
            crop_h = max(1, int(h / args.zoom))

            x1 = (w - crop_w) // 2
            y1 = (h - crop_h) // 2

            cropped = left_frame[y1:y1 + crop_h, x1:x1 + crop_w]

            zoomed_frame = cv2.resize(cropped, (w, h))

            hsv = cv2.cvtColor(cropped, cv2.COLOR_BGR2HSV)

            title = "link_base XY [m]" if calibration else "UNCALIBRATED: left-image (u,v) [px]"
            draw_label(zoomed_frame, title, (10, 25))
            detections = {}
            for index, (name, bound) in enumerate(colors.items()):

                mask = np.zeros(hsv.shape[:2], dtype=np.uint8)

                for lower, upper in bound:
                    mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower, upper))

                if args.show_masks:
                    cv2.imshow(f"{name} mask", mask)
                contours, _ = cv2.findContours(
                    mask,
                    cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE
                )

                # No stale positions: only the current frame can produce coordinates.
                candidates = []
                for contour in contours:
                    area = cv2.contourArea(contour)
                    perimeter = cv2.arcLength(contour, True)
                    if area > args.min_area and perimeter > 0:
                        if 4 * np.pi * area / perimeter ** 2 >= args.min_circularity:
                            candidates.append(contour)
                label = f"{name}: not detected"
                if candidates:
                    contour = max(candidates, key=cv2.contourArea)
                    M = cv2.moments(contour)
                    if M["m00"] > 0:
                        cx, cy = M["m10"] / M["m00"], M["m01"] / M["m00"]
                        u, v = x1 + cx, y1 + cy
                        detections[name] = (u, v)
                        display_contour = contour.astype(np.float64)
                        display_contour[:, :, 0] = (display_contour[:, :, 0] + 0.5) * w / crop_w - 0.5
                        display_contour[:, :, 1] = (display_contour[:, :, 1] + 0.5) * h / crop_h - 0.5
                        cv2.drawContours(zoomed_frame, [np.rint(display_contour).astype(np.int32)],
                                         -1, (0, 255, 255), 2)
                        center = (round((cx + 0.5) * w / crop_w - 0.5),
                                  round((cy + 0.5) * h / crop_h - 0.5))
                        cv2.circle(zoomed_frame, center, 5, (255, 255, 255), -1)
                        if calibration:
                            xy = robot_xy(u, v, calibration)
                            label = (f"{name}: X={xy[0]:.3f} Y={xy[1]:.3f} m"
                                     if xy is not None else f"{name}: outside calibrated workspace")
                        else:
                            label = f"{name}: u={u:.1f} v={v:.1f} px"
                        hsv_value = detected_hsv(hsv, contour, mask)
                        label += f" HSV={hsv_value}"
                draw_label(zoomed_frame, label, (10, 55 + index * 28))

            cv2.imshow("Ball Detection", zoomed_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                if args.collect_calibration:
                    print("Exiting; unsaved calibration points are discarded. Use s to save.")
                break
            if args.collect_calibration and key == ord('c'):
                point = detections.get(args.calibration_color)
                if point is None:
                    print("Calibration ball not detected; no point captured")
                    continue
                # Freeze this frame's detector centroid before asking for measured XY.
                try:
                    values = [float(v) for v in input(
                        f"Captured {args.calibration_color} pixel {point}. Enter measured link_base X Y [m]: "
                    ).split()]
                    if len(values) != 2 or not np.isfinite(values).all():
                        raise ValueError()
                except (ValueError, EOFError):
                    print("Invalid X Y; point discarded")
                    continue
                collected["image_points_px"].append(list(point))
                collected["robot_points_m"].append(values)
                collected["left_image_size"] = [w, h]
                print(f"Captured {len(collected['image_points_px'])} points. c: add, s: save, q: quit")
            if args.collect_calibration and key == ord('s'):
                try:
                    calibration_from_data(collected)
                except (ValueError, KeyError) as error:
                    print(f"Cannot save yet: {error}")
                    continue
                with args.collect_calibration.open("x") as output:
                    json.dump(collected, output, indent=2)
                print(f"Saved {args.collect_calibration}")
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
