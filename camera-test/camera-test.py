
import cv2

# =========================================================
# CAMERA SETTINGS
# =========================================================

CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30

WINDOW_NAME = "C950 Camera"

# =========================================================
# BASE ROI SETTINGS
# =========================================================

NUMBER_OF_NOTES = 65
GROUP_SIZE = 5
NUMBER_OF_GROUPS = 13

ROI_START_X = 100
ROI_START_Y = 350

ROI_SIZE = 8
NOTE_SPACING = 14

# =========================================================
# GLOBAL CALIBRATION SETTINGS
#
# These affect all 65 ROIs.
# =========================================================

INITIAL_X_OFFSET = 0
INITIAL_Y_OFFSET = 0
INITIAL_SIZE_ADJUSTMENT = 0
INITIAL_SPACING_ADJUSTMENT = 0

global_x = INITIAL_X_OFFSET
global_y = INITIAL_Y_OFFSET
global_size = INITIAL_SIZE_ADJUSTMENT
global_spacing = INITIAL_SPACING_ADJUSTMENT

# =========================================================
# GROUP CALIBRATION SETTINGS
#
# Each entry: [X offset, Y offset, Size, Spacing]
# =========================================================

INITIAL_GROUP_OFFSETS = [
    [-73,   0,   8,   3],  # Group  1 - notes 65-61
    [-57,   0,   8,   4],  # Group  2 - notes 60-56
    [-37,   0,   8,   5],  # Group  3 - notes 55-51
    [-14,   0,   9,   6],  # Group  4 - notes 50-46
    [ 13,   0,   9,   6],  # Group  5 - notes 45-41
    [ 39,   0,   9,   6],  # Group  6 - notes 40-36
    [ 65,   0,   9,   6],  # Group  7 - notes 35-31
    [ 93,   0,   9,   6],  # Group  8 - notes 30-26
    [120,   0,   9,   6],  # Group  9 - notes 25-21
    [152,   0,   9,   6],  # Group 10 - notes 20-16
    [180,   0,   9,   6],  # Group 11 - notes 15-11
    [210,   0,   9,   4],  # Group 12 - notes 10-6
    [239,   0,   9,   4],  # Group 13 - notes 5-1
]

group_offsets = [
    offsets.copy() for offsets in INITIAL_GROUP_OFFSETS
]

# 0 = entire row, 1-13 = individual group
selected_group = 0

entering_group = False
group_input = ""

# =========================================================
# CAMERA SETUP
# =========================================================

camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)

if not camera.isOpened():
    print("Could not open camera")
    raise SystemExit(1)

camera.set(
    cv2.CAP_PROP_FOURCC,
    cv2.VideoWriter_fourcc(*"MJPG")
)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
camera.set(cv2.CAP_PROP_FPS, CAMERA_FPS)

width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = camera.get(cv2.CAP_PROP_FPS)

print(f"Camera resolution: {width} x {height}")
print(f"Camera FPS: {fps}")

cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WINDOW_NAME, 1280, 720)

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def draw_text(frame, text, x, y, color=(0, 255, 255),
              scale=0.45, thickness=1):

    cv2.putText(
        frame,
        text,
        (int(x), int(y)),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA
    )


def get_effective_settings(group_index):

    offsets = group_offsets[group_index]

    x_adjust = global_x + offsets[0]
    y_adjust = global_y + offsets[1]

    size = max(
        1,
        ROI_SIZE + global_size + offsets[2]
    )

    spacing = max(
        1,
        NOTE_SPACING + global_spacing + offsets[3]
    )

    return x_adjust, y_adjust, size, spacing


def get_note_position(note_index):

    group_index = note_index // GROUP_SIZE
    local_index = note_index % GROUP_SIZE

    x_adjust, y_adjust, size, spacing = (
        get_effective_settings(group_index)
    )

    base_spacing = max(
        1,
        NOTE_SPACING + global_spacing
    )

    x = (
        ROI_START_X
        + note_index * base_spacing
        + x_adjust
        + local_index * group_offsets[group_index][3]
    )

    y = ROI_START_Y + y_adjust

    return int(x), int(y), int(size)


def print_calibration():

    print("\n" + "=" * 60)
    print("CALIBRATION VALUES - COPY INTO camera-test.py")
    print("=" * 60)

    print("\n# GLOBAL CALIBRATION SETTINGS")
    print(f"INITIAL_X_OFFSET = {global_x}")
    print(f"INITIAL_Y_OFFSET = {global_y}")
    print(f"INITIAL_SIZE_ADJUSTMENT = {global_size}")
    print(f"INITIAL_SPACING_ADJUSTMENT = {global_spacing}")

    print("\n# GROUP CALIBRATION SETTINGS")
    print("# Each entry: [X, Y, Size, Spacing]")
    print("INITIAL_GROUP_OFFSETS = [")

    for i, offsets in enumerate(group_offsets):

        first_note = NUMBER_OF_NOTES - i * GROUP_SIZE
        last_note = first_note - GROUP_SIZE + 1

        print(
            f"    [{offsets[0]:3d}, "
            f"{offsets[1]:3d}, "
            f"{offsets[2]:3d}, "
            f"{offsets[3]:3d}],"
            f"  # Group {i + 1:2d} - notes "
            f"{first_note}-{last_note}"
        )

    print("]")
    print("=" * 60 + "\n")


def adjust_selected(index, amount):

    global global_x, global_y, global_size, global_spacing

    if selected_group == 0:

        if index == 0:
            global_x += amount

        elif index == 1:
            global_y += amount

        elif index == 2:
            global_size = max(
                1 - ROI_SIZE,
                global_size + amount
            )

        elif index == 3:
            global_spacing = max(
                1 - NOTE_SPACING,
                global_spacing + amount
            )

    else:

        group_index = selected_group - 1

        group_offsets[group_index][index] += amount

        if index == 2:
            minimum = 1 - ROI_SIZE - global_size
            group_offsets[group_index][2] = max(
                minimum,
                group_offsets[group_index][2]
            )

        if index == 3:
            minimum = 1 - NOTE_SPACING - global_spacing
            group_offsets[group_index][3] = max(
                minimum,
                group_offsets[group_index][3]
            )


def reset_calibration():

    global global_x, global_y, global_size, global_spacing
    global group_offsets

    global_x = INITIAL_X_OFFSET
    global_y = INITIAL_Y_OFFSET
    global_size = INITIAL_SIZE_ADJUSTMENT
    global_spacing = INITIAL_SPACING_ADJUSTMENT

    group_offsets = [
        offsets.copy() for offsets in INITIAL_GROUP_OFFSETS
    ]


# =========================================================
# STARTUP INSTRUCTIONS
# =========================================================

print("\nKEYBOARD CONTROLS")
print("G + group number + ENTER = select group")
print("G + 0 + ENTER = select all groups")
print("+ / - = move right / left")
print("I / K = move up / down")
print("W / S = increase / decrease square size")
print("D / A = increase / decrease spacing")
print("R = reset all calibration")
print("P = print calibration")
print("ESC = exit")

print_calibration()

# =========================================================
# MAIN LOOP
# =========================================================

while True:

    ret, frame = camera.read()

    if not ret:
        print("Could not read camera")
        break

    # -----------------------------------------------------
    # DRAW NOTE ROIs
    # -----------------------------------------------------

    for note_index in range(NUMBER_OF_NOTES):

        group_index = note_index // GROUP_SIZE

        x1, y1, size = get_note_position(note_index)

        x2 = x1 + size
        y2 = y1 + size

        # Highlight selected group
        if selected_group == group_index + 1:
            color = (0, 255, 255)  # Yellow
            thickness = 2
        else:
            color = (0, 255, 0)    # Green
            thickness = 1

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            thickness
        )

        # Number 65 on left, 1 on right
        note_number = NUMBER_OF_NOTES - note_index
        label = str(note_number)

        text_size, _ = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            1
        )

        text_x = x1 + (size - text_size[0]) // 2

        if note_number % 2:
            text_y = y1 - 5
        else:
            text_y = y2 + 12

        draw_text(
            frame,
            label,
            text_x,
            text_y,
            color,
            0.35
        )

    # -----------------------------------------------------
    # DRAW GROUP BRACKETS AND GROUP NUMBERS
    # -----------------------------------------------------

    for group_index in range(NUMBER_OF_GROUPS):

        first_note = group_index * GROUP_SIZE
        last_note = first_note + GROUP_SIZE - 1

        first_x, first_y, first_size = (
            get_note_position(first_note)
        )

        last_x, last_y, last_size = (
            get_note_position(last_note)
        )

        bracket_left = min(first_x, last_x) - 2
        bracket_right = max(
            first_x + first_size,
            last_x + last_size
        ) + 2

        bracket_y = max(
            first_y + first_size,
            last_y + last_size
        ) + 32

        is_selected = selected_group == group_index + 1

        color = (
            (0, 255, 255) if is_selected
            else (255, 200, 0)
        )

        # Horizontal bracket
        cv2.line(
            frame,
            (bracket_left, bracket_y),
            (bracket_right, bracket_y),
            color,
            1
        )

        # Bracket ends
        cv2.line(
            frame,
            (bracket_left, bracket_y - 6),
            (bracket_left, bracket_y),
            color,
            1
        )

        cv2.line(
            frame,
            (bracket_right, bracket_y - 6),
            (bracket_right, bracket_y),
            color,
            1
        )

        # Group number
        center_x = (bracket_left + bracket_right) // 2

        draw_text(
            frame,
            f"G{group_index + 1}",
            center_x - 12,
            bracket_y + 15,
            color,
            0.35
        )

    # -----------------------------------------------------
    # DISPLAY SELECTED GROUP SETTINGS
    # -----------------------------------------------------

    if entering_group:

        draw_text(
            frame,
            f"Select group (0-13): {group_input}_",
            20, 30,
            (0, 255, 255),
            0.65, 2
        )

    elif selected_group == 0:

        draw_text(
            frame,
            "Selected Group: ALL",
            20, 30,
            (0, 255, 255),
            0.65, 2
        )

        draw_text(
            frame,
            f"X Offset: {global_x:+d}",
            20, 55
        )

        draw_text(
            frame,
            f"Y Offset: {global_y:+d}",
            20, 80
        )

        draw_text(
            frame,
            f"Square Size: {ROI_SIZE + global_size}",
            20, 105
        )

        draw_text(
            frame,
            f"Note Spacing: {NOTE_SPACING + global_spacing}",
            20, 130
        )

    else:

        group_index = selected_group - 1
        offsets = group_offsets[group_index]

        first_note = NUMBER_OF_NOTES - group_index * GROUP_SIZE
        last_note = first_note - GROUP_SIZE + 1

        draw_text(
            frame,
            f"Selected Group: {selected_group} "
            f"(Notes {first_note}-{last_note})",
            20, 30,
            (0, 255, 255),
            0.65, 2
        )

        draw_text(
            frame,
            f"X Offset: {offsets[0]:+d}",
            20, 55
        )

        draw_text(
            frame,
            f"Y Offset: {offsets[1]:+d}",
            20, 80
        )

        draw_text(
            frame,
            f"Size Adjustment: {offsets[2]:+d}",
            20, 105
        )

        draw_text(
            frame,
            f"Spacing Adjustment: {offsets[3]:+d}",
            20, 130
        )

    # -----------------------------------------------------
    # KEYBOARD HELP
    # -----------------------------------------------------

    draw_text(
        frame,
        "G Select | +/- X | I/K Y | W/S Size | D/A Spacing",
        20, 165
    )

    draw_text(
        frame,
        "P Print | R Reset | ESC Exit",
        20, 190
    )

    # -----------------------------------------------------
    # SHOW CAMERA IMAGE
    # -----------------------------------------------------

    cv2.imshow(WINDOW_NAME, frame)

    key = cv2.waitKeyEx(1)

    if key == -1:
        continue

    # -----------------------------------------------------
    # GROUP SELECTION INPUT MODE
    # -----------------------------------------------------

    if entering_group:

        # Enter
        if key in (10, 13):

            if group_input.isdigit():

                group_number = int(group_input)

                if 0 <= group_number <= NUMBER_OF_GROUPS:

                    selected_group = group_number

                    print(
                        f"Selected group: "
                        f"{'ALL' if group_number == 0 else group_number}"
                    )

                else:
                    print("Invalid group number")

            entering_group = False
            group_input = ""

        # Backspace
        elif key in (8, 127):
            group_input = group_input[:-1]

        # ESC cancels group selection
        elif key == 27:
            entering_group = False
            group_input = ""

        # Accept digits only
        elif ord("0") <= key <= ord("9"):
            if len(group_input) < 2:
                group_input += chr(key)

        continue

    # -----------------------------------------------------
    # NORMAL KEYBOARD CONTROLS
    # -----------------------------------------------------

    if key == 27:
        break

    elif key in (ord("g"), ord("G")):
        entering_group = True
        group_input = ""
        continue

    elif key in (ord("+"), ord("=")):
        adjust_selected(0, +1)

    elif key == ord("-"):
        adjust_selected(0, -1)

    elif key in (ord("i"), ord("I"), 65362, 2490368):
        adjust_selected(1, -1)

    elif key in (ord("k"), ord("K"), 65364, 2621440):
        adjust_selected(1, +1)

    elif key in (ord("w"), ord("W")):
        adjust_selected(2, +1)

    elif key in (ord("s"), ord("S")):
        adjust_selected(2, -1)

    elif key in (ord("d"), ord("D")):
        adjust_selected(3, +1)

    elif key in (ord("a"), ord("A")):
        adjust_selected(3, -1)

    elif key in (ord("r"), ord("R")):
        reset_calibration()
        print("Calibration reset")

    elif key in (ord("p"), ord("P")):
        print_calibration()
        continue

    else:
        continue

    # Print changes to terminal
    if selected_group == 0:

        print(
            f"ALL: X={global_x:+d} Y={global_y:+d} "
            f"Size={global_size:+d} "
            f"Spacing={global_spacing:+d}"
        )

    else:

        offsets = group_offsets[selected_group - 1]

        print(
            f"Group {selected_group}: "
            f"X={offsets[0]:+d} "
            f"Y={offsets[1]:+d} "
            f"Size={offsets[2]:+d} "
            f"Spacing={offsets[3]:+d}"
        )

# =========================================================
# CLEANUP
# =========================================================

print("\nFINAL CALIBRATION VALUES")
print_calibration()

camera.release()
cv2.destroyAllWindows()
