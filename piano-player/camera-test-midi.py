import cv2
import numpy as np

# CAMERA SETTINGS
CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30
WINDOW_NAME = 'C950 Camera'

# ROI AND CALIBRATION SETTINGS (your current values)
NUMBER_OF_NOTES = 65
GROUP_SIZE = 5
NUMBER_OF_GROUPS = 13
ROI_START_X = 100
ROI_START_Y = 350
ROI_SIZE = 8
ROI_HEIGHT = 6  # NEW: vertical height of detection area, in pixels
NOTE_SPACING = 14
INITIAL_X_OFFSET = 0
INITIAL_Y_OFFSET = 0
INITIAL_SIZE_ADJUSTMENT = 0
INITIAL_SPACING_ADJUSTMENT = 0
INITIAL_GROUP_OFFSETS = [
    [-59,   0,  10,   2],  # Group  1 - notes 65-61
    [-47,   0,   8,   4],  # Group  2 - notes 60-56
    [-29,   0,  11,   4],  # Group  3 - notes 55-51
    [ -6,   0,   8,   4],  # Group  4 - notes 50-46
    [ 15,   0,  10,   4],  # Group  5 - notes 45-41
    [ 37,   0,   8,   4],  # Group  6 - notes 40-36
    [ 56,   0,   9,   5],  # Group  7 - notes 35-31
    [ 79,   0,  10,   4],  # Group  8 - notes 30-26
    [ 99,   0,  11,   5],  # Group  9 - notes 25-21
    [126,   0,   9,   4],  # Group 10 - notes 20-16
    [148,   0,  11,   5],  # Group 11 - notes 15-11
    [171,   0,  12,   4],  # Group 12 - notes 10-6
    [198,   0,   8,   5],  # Group 13 - notes 5-1
]

global_x = INITIAL_X_OFFSET
global_y = INITIAL_Y_OFFSET
global_size = INITIAL_SIZE_ADJUSTMENT
global_spacing = INITIAL_SPACING_ADJUSTMENT
group_offsets = [offsets.copy() for offsets in INITIAL_GROUP_OFFSETS]
selected_group = 0
entering_group = False
group_input = ''

# HOLE DETECTION AND MIDI SETTINGS (preserved)
MIDI_FIRST_NOTE = 36
MIDI_VELOCITY = 95
ON_THRESHOLD = 180
OFF_THRESHOLD = 210
DEBOUNCE_FRAMES = 2
MIDI_PORT = '128:0'  # Reference; port is discovered by name below

detection_enabled = False
muted = False
on_threshold = ON_THRESHOLD
off_threshold = OFF_THRESHOLD
note_active = [False] * NUMBER_OF_NOTES
pending_count = [0] * NUMBER_OF_NOTES
last_brightness = [None] * NUMBER_OF_NOTES

try:
    import rtmidi
except ImportError as exc:
    raise SystemExit('Missing MIDI library. Run: sudo apt install -y python3-rtmidi') from exc


class MidiOutput:
    def __init__(self):
        self.out = rtmidi.MidiOut(rtmidi.API_LINUX_ALSA)
        ports = self.out.get_ports()
        print('Available MIDI output ports:', ports)
        matches = [i for i, name in enumerate(ports) if 'FLUID Synth' in name]
        if not matches:
            raise RuntimeError('No FluidSynth MIDI port found. Check: aconnect -l')
        self.out.open_port(matches[0])
        print('Connected to', ports[matches[0]])

    def send(self, midi_note, velocity, is_on):
        self.out.send_message([0x90 if is_on else 0x80, midi_note, velocity if is_on else 0])

    def close(self):
        self.out.close_port()


def draw_text(frame, text, x, y, color=(0, 255, 255), scale=0.45, thickness=1):
    cv2.putText(frame, str(text), (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, thickness, cv2.LINE_AA)


def get_effective_settings(group_index):
    offsets = group_offsets[group_index]
    x_adjust = global_x + offsets[0]
    y_adjust = global_y + offsets[1]
    size = max(1, ROI_SIZE + global_size + offsets[2])
    spacing = max(1, NOTE_SPACING + global_spacing + offsets[3])
    return x_adjust, y_adjust, size, spacing


def get_note_position(note_index):
    group_index = note_index // GROUP_SIZE
    local_index = note_index % GROUP_SIZE
    x_adjust, y_adjust, size, _ = get_effective_settings(group_index)
    base_spacing = max(1, NOTE_SPACING + global_spacing)
    x = (ROI_START_X + note_index * base_spacing + x_adjust
         + local_index * group_offsets[group_index][3])
    y = ROI_START_Y + y_adjust
    return int(x), int(y), int(size)


def get_detection_rectangle(note_index):
    """Preserve calibrated ROI width and center a shorter vertical detection strip."""
    x, y, width = get_note_position(note_index)
    height = min(ROI_HEIGHT, width)  # Keep within original ROI if size is adjusted
    top = y + (width - height) // 2
    return x, top, width, height


def print_calibration():
    print('\n' + '=' * 60)
    print('CALIBRATION VALUES - COPY INTO camera-test.py')
    print('=' * 60)
    print('\n# GLOBAL CALIBRATION SETTINGS')
    print(f'INITIAL_X_OFFSET = {global_x}')
    print(f'INITIAL_Y_OFFSET = {global_y}')
    print(f'INITIAL_SIZE_ADJUSTMENT = {global_size}')
    print(f'INITIAL_SPACING_ADJUSTMENT = {global_spacing}')
    print('\n# GROUP CALIBRATION SETTINGS')
    print('# Each entry: [X, Y, Size, Spacing]')
    print('INITIAL_GROUP_OFFSETS = [')
    for i, offsets in enumerate(group_offsets):
        first_note = NUMBER_OF_NOTES - i * GROUP_SIZE
        last_note = first_note - GROUP_SIZE + 1
        print(f'    [{offsets[0]:3d}, {offsets[1]:3d}, {offsets[2]:3d}, {offsets[3]:3d}],'
              f'  # Group {i+1:2d} - notes {first_note}-{last_note}')
    print(']')
    print('=' * 60 + '\n')


def adjust_selected(index, amount):
    global global_x, global_y, global_size, global_spacing
    if selected_group == 0:
        if index == 0:
            global_x += amount
        elif index == 1:
            global_y += amount
        elif index == 2:
            global_size = max(1 - ROI_SIZE, global_size + amount)
        elif index == 3:
            global_spacing = max(1 - NOTE_SPACING, global_spacing + amount)
    else:
        group_index = selected_group - 1
        group_offsets[group_index][index] += amount
        if index == 2:
            group_offsets[group_index][2] = max(
                1 - ROI_SIZE - global_size, group_offsets[group_index][2])
        if index == 3:
            group_offsets[group_index][3] = max(
                1 - NOTE_SPACING - global_spacing, group_offsets[group_index][3])


def reset_calibration():
    global global_x, global_y, global_size, global_spacing, group_offsets
    global_x = INITIAL_X_OFFSET
    global_y = INITIAL_Y_OFFSET
    global_size = INITIAL_SIZE_ADJUSTMENT
    global_spacing = INITIAL_SPACING_ADJUSTMENT
    group_offsets = [offsets.copy() for offsets in INITIAL_GROUP_OFFSETS]


def silence_all(midi):
    for i, active in enumerate(note_active):
        if active:
            midi.send(MIDI_FIRST_NOTE + i, 0, False)
        note_active[i] = False
        pending_count[i] = 0


def update_detection(gray, midi):
    for i in range(NUMBER_OF_NOTES):
        x, y, width, height = get_detection_rectangle(i)
        x1, y1 = max(0, x), max(0, y)
        x2 = min(gray.shape[1], x + width)
        y2 = min(gray.shape[0], y + height)
        if x1 >= x2 or y1 >= y2:
            last_brightness[i] = None
            if note_active[i]:
                midi.send(MIDI_FIRST_NOTE + i, 0, False)
                note_active[i] = False
            pending_count[i] = 0
            continue

        brightness = float(np.mean(gray[y1:y2, x1:x2]))
        last_brightness[i] = brightness
        if not detection_enabled:
            pending_count[i] = 0
            continue

        if note_active[i]:
            if brightness > off_threshold:
                pending_count[i] += 1
                if pending_count[i] >= DEBOUNCE_FRAMES:
                    midi.send(MIDI_FIRST_NOTE + i, 0, False)
                    note_active[i] = False
                    pending_count[i] = 0
                    print(f'OFF ROI {NUMBER_OF_NOTES-i:2d} MIDI {MIDI_FIRST_NOTE+i} brightness {brightness:.0f}')
            else:
                pending_count[i] = 0
        else:
            if brightness < on_threshold:
                pending_count[i] += 1
                if pending_count[i] >= DEBOUNCE_FRAMES:
                    note_active[i] = True
                    pending_count[i] = 0
                    if not muted:
                        midi.send(MIDI_FIRST_NOTE + i, MIDI_VELOCITY, True)
                    print(f'ON  ROI {NUMBER_OF_NOTES-i:2d} MIDI {MIDI_FIRST_NOTE+i} brightness {brightness:.0f}')
            else:
                pending_count[i] = 0


def main():
    global selected_group, entering_group, group_input
    global detection_enabled, muted, on_threshold, off_threshold

    camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
    if not camera.isOpened():
        raise SystemExit('Could not open camera')
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    camera.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
    print(f'Camera resolution: {int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))} x '
          f'{int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))}')
    print(f'Camera FPS: {camera.get(cv2.CAP_PROP_FPS)}')
    try:
        midi = MidiOutput()
    except Exception:
        camera.release()
        raise

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 1280, 720)
    print('\nKEYBOARD CONTROLS')
    print('G + group number + ENTER = select group (0 = ALL)')
    print('+/- move X | I/K move Y | W/S size | D/A spacing')
    print('P print calibration | R reset calibration | ESC exit')
    print('T toggle detection | M mute/unmute')
    print('[ / ] decrease/increase ON threshold')
    print('; / apostrophe decrease/increase OFF threshold')
    print('Detection starts OFF. Press T when ready.')
    print_calibration()

    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                print('Could not read camera')
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Read camera pixels BEFORE drawing any overlays.
            update_detection(gray, midi)

            for note_index in range(NUMBER_OF_NOTES):
                group_index = note_index // GROUP_SIZE
                x1, y1, width, height = get_detection_rectangle(note_index)
                x2, y2 = x1 + width, y1 + height
                if note_active[note_index]:
                    color, thickness = (0, 0, 255), 2
                elif selected_group == group_index + 1:
                    color, thickness = (0, 255, 255), 2
                else:
                    color, thickness = (0, 255, 0), 1
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                note_number = NUMBER_OF_NOTES - note_index
                label = str(note_number)
                text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)
                text_x = x1 + (width - text_size[0]) // 2
                text_y = y1 - 5 if note_number % 2 else y2 + 12
                draw_text(frame, label, text_x, text_y, color, 0.35)

            for group_index in range(NUMBER_OF_GROUPS):
                first_note = group_index * GROUP_SIZE
                last_note = first_note + GROUP_SIZE - 1
                first_x, first_y, first_size = get_note_position(first_note)
                last_x, last_y, last_size = get_note_position(last_note)
                bracket_left = min(first_x, last_x) - 2
                bracket_right = max(first_x + first_size, last_x + last_size) + 2
                bracket_y = max(first_y + first_size, last_y + last_size) + 32
                color = (0, 255, 255) if selected_group == group_index + 1 else (255, 200, 0)
                cv2.line(frame, (bracket_left, bracket_y), (bracket_right, bracket_y), color, 1)
                cv2.line(frame, (bracket_left, bracket_y - 6), (bracket_left, bracket_y), color, 1)
                cv2.line(frame, (bracket_right, bracket_y - 6), (bracket_right, bracket_y), color, 1)
                draw_text(frame, f'G{group_index+1}', (bracket_left + bracket_right)//2 - 12,
                          bracket_y + 15, color, 0.35)

            if entering_group:
                draw_text(frame, f'Select group (0-13): {group_input}_', 20, 30, (0,255,255), 0.65, 2)
            elif selected_group == 0:
                draw_text(frame, 'Selected Group: ALL', 20, 30, (0,255,255), 0.65, 2)
                draw_text(frame, f'X Offset: {global_x:+d}', 20, 55)
                draw_text(frame, f'Y Offset: {global_y:+d}', 20, 80)
                draw_text(frame, f'Square Size: {ROI_SIZE + global_size}', 20, 105)
                draw_text(frame, f'Note Spacing: {NOTE_SPACING + global_spacing}', 20, 130)
            else:
                group_index = selected_group - 1
                offsets = group_offsets[group_index]
                first_note = NUMBER_OF_NOTES - group_index * GROUP_SIZE
                last_note = first_note - GROUP_SIZE + 1
                draw_text(frame, f'Selected Group: {selected_group} (Notes {first_note}-{last_note})',
                          20, 30, (0,255,255), 0.65, 2)
                draw_text(frame, f'X Offset: {offsets[0]:+d}', 20, 55)
                draw_text(frame, f'Y Offset: {offsets[1]:+d}', 20, 80)
                draw_text(frame, f'Size Adjustment: {offsets[2]:+d}', 20, 105)
                draw_text(frame, f'Spacing Adjustment: {offsets[3]:+d}', 20, 130)

            draw_text(frame, 'G Select | +/- X | I/K Y | W/S Size | D/A Spacing', 20, 165)
            draw_text(frame, 'P Print | R Reset | ESC Exit', 20, 190)
            draw_text(frame, f'Detection: {"ON" if detection_enabled else "OFF"} (T) | '
                      f'Sound: {"MUTED" if muted else "ON"} (M) | '
                      f'ON < {on_threshold} | OFF > {off_threshold}',
                      20, 215, (0,255,255))
            draw_text(frame, '[ / ] ON threshold | ; / apostrophe OFF threshold', 20, 240)
            draw_text(frame, f'ROI detection height: {ROI_HEIGHT} pixels', 20, 290)
            if selected_group:
                idx = (selected_group - 1) * GROUP_SIZE
                vals = ' '.join(f'{NUMBER_OF_NOTES-i}:{last_brightness[i]:.0f}'
                                if last_brightness[i] is not None else f'{NUMBER_OF_NOTES-i}:--'
                                for i in range(idx, idx + GROUP_SIZE))
                draw_text(frame, f'Brightness: {vals}', 20, 265, (0,255,255))
            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKeyEx(1)
            if key == -1:
                continue

            if entering_group:
                if key in (10, 13):
                    if group_input.isdigit():
                        group_number = int(group_input)
                        if 0 <= group_number <= NUMBER_OF_GROUPS:
                            selected_group = group_number
                            print(f'Selected group: {"ALL" if group_number == 0 else group_number}')
                        else:
                            print('Invalid group number')
                    entering_group = False
                    group_input = ''
                elif key in (8, 127):
                    group_input = group_input[:-1]
                elif key == 27:
                    entering_group = False
                    group_input = ''
                elif ord('0') <= key <= ord('9') and len(group_input) < 2:
                    group_input += chr(key)
                continue

            if key == 27:
                break
            elif key in (ord('g'), ord('G')):
                entering_group = True
                group_input = ''
            elif key in (ord('+'), ord('=')):
                adjust_selected(0, +1)
            elif key == ord('-'):
                adjust_selected(0, -1)
            elif key in (ord('i'), ord('I'), 65362, 2490368):
                adjust_selected(1, -1)
            elif key in (ord('k'), ord('K'), 65364, 2621440):
                adjust_selected(1, +1)
            elif key in (ord('w'), ord('W')):
                adjust_selected(2, +1)
            elif key in (ord('s'), ord('S')):
                adjust_selected(2, -1)
            elif key in (ord('d'), ord('D')):
                adjust_selected(3, +1)
            elif key in (ord('a'), ord('A')):
                adjust_selected(3, -1)
            elif key in (ord('r'), ord('R')):
                silence_all(midi)
                reset_calibration()
                print('Calibration reset')
            elif key in (ord('p'), ord('P')):
                print_calibration()
            elif key in (ord('t'), ord('T')):
                detection_enabled = not detection_enabled
                silence_all(midi)
                print('Detection', 'ON' if detection_enabled else 'OFF')
            elif key in (ord('m'), ord('M')):
                muted = not muted
                silence_all(midi)
                print('Sound', 'MUTED' if muted else 'ON')
            elif key == ord('['):
                on_threshold = max(0, on_threshold - 5)
                print('ON threshold:', on_threshold)
            elif key == ord(']'):
                on_threshold = min(255, on_threshold + 5)
                print('ON threshold:', on_threshold)
            elif key == ord(';'):
                off_threshold = max(0, off_threshold - 5)
                print('OFF threshold:', off_threshold)
            elif key == ord("'"):
                off_threshold = min(255, off_threshold + 5)
                print('OFF threshold:', off_threshold)
    finally:
        print('\nFINAL CALIBRATION VALUES')
        print_calibration()
        silence_all(midi)
        midi.close()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
