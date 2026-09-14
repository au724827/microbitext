
radioChannel = 1

from microbit import *
import machine
import struct
import radio
import random
import music
import time

uart.init()

id_number = "0"
device_name = ""
message_number = 0
recipient_index = 0
known_recipients = 0
known_recipient_list = []
encryptable = False
auto_encryptable = False
allow_recipient = False
output_message = []
last_ping_received = 0
reset_microbit_time = 0
known_pk_names = []
asym_enabled = False
choosing_pk_target = False
pk_target_index = 0
chosen_pk_id = 0
encryption_pending = False
PING_INACTIVITY_TIMEOUT = 15000
ENCRYPTION_TIMEOUT = 10000

def show_inner_dot_animation():
    frames = (
        "00000:09000:00000:00000:00000",
        "00000:00900:00000:00000:00000",
        "00000:00090:00000:00000:00000",
        "00000:00000:00090:00000:00000",
        "00000:00000:00000:00090:00000",
        "00000:00000:00000:00900:00000",
        "00000:00000:00000:09000:00000",
        "00000:00000:09000:00000:00000",
    )
    display.show(Image(frames[time.ticks_ms() // 120 % 8]))

# Built-in images stored in the same compact format used for radio images.
# "AKARO" = 00000,01010,00000,10001,01110
# "AKAOR" = 00000,01010,00000,01110,10001
led_images = ["AKARO", "AKAOR"]

send_image_base = (
    (0, 0, 1, 0, 0),
    (0, 1, 1, 1, 0),
    (1, 0, 1, 0, 1),
    (0, 0, 1, 0, 0),
    (0, 0, 1, 0, 0),
)
send_image_offsets = (3, 2, 1, 0, -1, -2, -3, -4, -5)

message_complete = False
message_sender = 0
message_recipient = ""
code_string = ""
packed_received_image = ""

known = False
last_known_ping = 0
choosing_content = False
choosing_recipient = False
encrypting_message = False
sending_message = False
ready_to_send = False
code = []
should_beep = False

radio.config(
    group=radioChannel,
    data_rate=radio.RATE_1MBIT,
    queue=10,
    channel=42
)
radio.on()

def write_to_computer(message):
    print("#" + str(message) + "&")

def microbit_friendly_name():
    codebook = (
        ("z", "v", "g", "p", "t"),
        ("u", "o", "i", "e", "a"),
        ("z", "v", "g", "p", "t"),
        ("u", "o", "i", "e", "a"),
        ("z", "v", "g", "p", "t"),
    )
    _, n = struct.unpack("II", machine.unique_id())
    name = []
    ld = 1
    d = 5

    for i in range(5):
        h = (n % d) // ld
        n -= h
        d *= 5
        ld *= 5
        name.insert(0, codebook[i][h])

    return "".join(name)

device_name = microbit_friendly_name()
write_to_computer("dummy_" + device_name)

def send_message(message_to_send):
    radio.send(device_name + "_" + str(message_to_send))

def get_image(image_index):
    return Image(matrix_to_image(unpack_image(led_images[image_index])))

def build_send_image(frame_index):
    image = [[0] * 5 for _ in range(5)]
    offset = send_image_offsets[frame_index]

    for y in range(5):
        shifted_y = y + offset
        if 0 <= shifted_y < 5:
            image[shifted_y] = send_image_base[y]

    return image

def matrix_to_image(matrix):
    return ":".join("".join(str(x * 9) for x in row) for row in matrix)

def show_standby():
    display.show(int(id_number) + 1)

def show_error():
    display.show(Image.NO)
    sleep(1500)
    show_standby()

def set_recipients():
    global known_recipient_list
    my_id = int(id_number)
    known_recipient_list = [i for i in range(known_recipients) if i != my_id]
    return known_recipient_list

def send_animation():
    for i in range(9):
        display.show(Image(matrix_to_image(build_send_image(i))))
        sleep(100)
    display.clear()

def create_encryption(message_list):
    for j in range(5):
        if int(code[j]):
            for k in range(5):
                message_list[k][j] = 1 - message_list[k][j]
    return message_list

def set_column(column_index, value):
    for row in range(5):
        display.set_pixel(column_index, row, value)

def encrypt_image(image_list):
    sleep(500)
    for j in range(5):
        set_column(j, 9)
        sleep(400)
        set_column(j, 0)
        for k in range(5):
            display.set_pixel(j, k, int(image_list[k][j]) * 9)
        sleep(100)

def random_encrypt_animation():
    display.clear()
    for _ in range(2):
        for j in range(5):
            for k in range(5):
                display.set_pixel(k, j, random.randint(0, 1) * 9)
        sleep(500)
    display.clear()

def display_code_input(code):
    display.clear()
    for i in range(len(code)):
        if int(code[i]):
            for j in range(5):
                display.set_pixel(i, j, 9)
        else:
            display.set_pixel(i, 2, 9)

def pack_image(matrix):
    return "".join(
        chr(v + 65) if v <= 25 else str(v - 26)
        for v in (int("".join(map(str, row)), 2) for row in matrix)
    )

def unpack_image(payload):
    return [
        [
            int(bit)
            for bit in "{:05b}".format(
                int(c) + 26 if c.isdigit() else ord(c) - 65
            )
        ]
        for c in payload
    ]

def show_ciphertext(packed_c1, packed_c2, sender):
    write_to_computer("ct_" + packed_c1 + "_" + packed_c2)
    display.show(Image(matrix_to_image(unpack_image(packed_c1))))
    sleep(1800)
    display.show(Image(matrix_to_image(unpack_image(packed_c2))))
    sleep(1800)
    display.show(Image.ARROW_W)
    sleep(700)
    display.show(sender + 1)
    sleep(1500)
    show_standby()

def check_serial():
    global known_pk_names, encryption_pending

    if not uart.any():
        return

    sleep(100)
    raw_message = uart.readline()

    try:
        command = raw_message.decode().strip()
    except:
        command = str(raw_message)

    if command.startswith("b'"):
        command = command[2:-1].replace("\\r", "").replace("\\n", "")
    if command.startswith("__"):
        command = command[2:]
    command = command.strip("_")
    parts = command.split("_")

    if parts[0] == "ping":
        write_to_computer("dummy_" + device_name)

    if parts[0] == "pks":
        if len(parts) > 1 and parts[1]:
            known_pk_names = [int(value) for value in parts[1].split(",") if value]
        else:
            known_pk_names = []

    if parts[0] == "sendct" and len(parts) == 4:
        encryption_pending = False
        send_message(
            "sendct_" + parts[1] + "_" + parts[2] + "_" + parts[3]
        )
        send_animation()

    if parts[0] == "senderr":
        encryption_pending = False
        show_error()

def abort_menus():
    global output_message, code_string, ready_to_send, encrypting_message
    global choosing_content, choosing_recipient, choosing_pk_target
    global message_number, recipient_index, pk_target_index
    output_message = []
    code_string = ""
    ready_to_send = False
    encrypting_message = False
    choosing_content = False
    choosing_recipient = False
    choosing_pk_target = False
    message_number = 0
    recipient_index = 0
    pk_target_index = 0

def handle_radio(message, in_menu=False):
    global known, id_number, known_recipients, last_known_ping, last_ping_received
    global encryptable, auto_encryptable, allow_recipient, should_beep, asym_enabled
    global output_message, code_string, packed_received_image
    global message_sender, message_complete

    parts = message.split("_")
    count = len(parts)
    code = parts[1] if count > 1 else ""
    mine = parts[0] == device_name

    if mine:
        known = True

    if parts[0] == "ping":
        last_ping_received = time.ticks_ms()

    elif parts[0] == "settings" and count == 6:
        encryptable = parts[1] == "1"
        auto_encryptable = parts[2] == "1"
        allow_recipient = parts[3] == "1"
        should_beep = parts[4] == "1"
        asym_enabled = parts[5] == "1"

    elif parts[0] == "known" and count == 2:
        known_recipients = int(parts[1])

    elif parts[0] == "image" and count == 3:
        if parts[2] not in led_images:
            led_images.append(parts[2])

    elif parts[0] == "removeImg" and count == 2:
        if parts[1] in led_images:
            led_images.remove(parts[1])

    elif parts[0] == "reintroduce":
        known = False
        last_known_ping = time.ticks_ms() - ((10 - int(id_number)) * 100)
        id_number = "0"
        abort_menus()
        display.clear()

    elif mine and code == "number" and count == 4:
        id_number = parts[2]
        known_recipients = int(parts[3])
        show_standby()

    elif mine and code == "receivect" and count == 5:
        show_ciphertext(parts[2], parts[3], int(parts[4]))

    elif code == "complete":
        output_message = [[], [], [], [], []]

    elif code == "receive" and count >= 4 and (mine or not allow_recipient):
        if in_menu:
            abort_menus()
            show_standby()
            return

        packed_received_image = parts[2]
        message_sender = int(parts[3])
        code_string = parts[4] if encryptable and count > 4 else ""

        if mine or message_sender != int(id_number):
            message_complete = True

def check_radio():
    message = radio.receive()
    if message:
        handle_radio(message, True)

# The keys live in the browser, so a send is only over once it has answered.
def wait_for_encryption():
    global encryption_pending
    encryption_pending = True
    started = time.ticks_ms()

    while encryption_pending and time.ticks_ms() - started < ENCRYPTION_TIMEOUT:
        check_serial()
        check_radio()

    if encryption_pending:
        encryption_pending = False
        show_error()

last_state_a = False
last_state_b = False
buttons_latched = False

# Only true on the press itself, so holding both buttons cannot confirm
# several menu steps in a row.
def both_buttons_pressed():
    global buttons_latched
    pressed = button_a.is_pressed() and button_b.is_pressed()

    if not pressed:
        buttons_latched = False
        return False

    if buttons_latched:
        return False

    buttons_latched = True
    return True

def button_a_was_released():
    global last_state_a
    current_state = button_a.is_pressed()
    released = last_state_a and not current_state
    last_state_a = current_state
    return released

def button_b_was_released():
    global last_state_b
    current_state = button_b.is_pressed()
    released = last_state_b and not current_state
    last_state_b = current_state
    return released

def reset_button_states():
    global last_state_a, last_state_b, buttons_latched
    last_state_a = button_a.is_pressed()
    last_state_b = button_b.is_pressed()
    buttons_latched = last_state_a and last_state_b
    button_a.was_pressed()
    button_b.was_pressed()

def input_code():
    reset_button_states()
    current_input = []

    while len(current_input) < 5:
        if button_a_was_released():
            display.clear()
            display.show("A")
            current_input.append("0")
            sleep(500)
            display.clear()
            display_code_input(current_input)
            continue

        if button_b_was_released():
            display.clear()
            display.show("B")
            current_input.append("1")
            sleep(500)
            display.clear()
            display_code_input(current_input)
            continue

    return current_input

while True:
    check_serial()

    message = radio.receive()

    if message:
        handle_radio(message)

    if known and time.ticks_ms() - last_ping_received > PING_INACTIVITY_TIMEOUT:
        machine.reset()

    if message_complete:
        reset_button_states()

        if should_beep:
            for i, pitch in enumerate((6, 8, 10, 12)):
                music.pitch(pitch * 100)
                sleep(150)
            music.stop()

        output_message = unpack_image(packed_received_image)
        code = list(code_string)

        display.show(Image(matrix_to_image(output_message)))

        sleep(int(id_number) * 50)
        send_message("complete")

        if encryptable:
            code = input_code()
            output_message = create_encryption(output_message)
            encrypt_image(output_message)

        sleep(4000)
        display.show(Image.ARROW_W)
        sleep(1000)
        display.show(int(message_sender) + 1)
        reset_microbit_time = True

    if reset_microbit_time:
        sleep(2000)
        display.clear()
        show_standby()
        output_message = []
        code = []
        code_string = ""
        message_sender = 0
        packed_received_image = []
        message_complete = False
        reset_microbit_time = False

    if not known and time.ticks_ms() - last_known_ping > 1000:
        send_message("hello")
        last_known_ping = time.ticks_ms()

    if not known:
        show_inner_dot_animation()
        continue

    if both_buttons_pressed():
        output_message = []
        code = []
        display.show(Image("99999:99099:90909:90009:99999"))
        sleep(1000)
        display.show(get_image(0))
        choosing_content = True
        reset_button_states()

    while choosing_content:
        check_radio()

        if both_buttons_pressed():
            output_message = [[], [], [], [], []]
            selected_image = unpack_image(led_images[message_number])

            for i in range(5):
                for j in range(5):
                    output_message[i].append(selected_image[i][j])

            if asym_enabled:
                if not known_pk_names:
                    show_error()
                    choosing_content = False
                else:
                    display.show(Image.DIAMOND)
                    sleep(1000)
                    pk_target_index = 0
                    display.show(known_pk_names[pk_target_index])
                    choosing_pk_target = True
                    choosing_content = False
            elif encryptable:
                display.show(Image("00000:09000:90999:09009:00000"))
                sleep(1000)
                display.clear()
                encrypting_message = True
                choosing_content = False

            elif allow_recipient:
                display.show(Image.ARROW_E)
                sleep(1000)
                known_recipient_list = set_recipients()
                display.show(known_recipient_list[0] + 1)
                choosing_recipient = True
                choosing_content = False

            else:
                sending_message = True
                choosing_content = False

            reset_button_states()
            break

        if button_a_was_released():
            message_number = (
                len(led_images) - 1
                if message_number == 0
                else message_number - 1
            )

        if button_b_was_released():
            message_number = (
                0
                if message_number == len(led_images) - 1
                else message_number + 1
            )

        display.show(get_image(message_number))

    while choosing_pk_target:
        check_radio()
        check_serial()

        if not known_pk_names:
            choosing_pk_target = False
            show_error()
            break

        if pk_target_index >= len(known_pk_names):
            pk_target_index = 0

        if both_buttons_pressed():
            chosen_pk_id = known_pk_names[pk_target_index]
            known_recipient_list = set_recipients()
            if not known_recipient_list:
                show_error()
                choosing_pk_target = False
                break

            display.show(Image.ARROW_E)
            sleep(1000)
            recipient_index = 0
            display.show(known_recipient_list[recipient_index] + 1)
            choosing_recipient = True
            choosing_pk_target = False
            reset_button_states()
            break

        if button_a_was_released():
            pk_target_index = (
                len(known_pk_names) - 1
                if pk_target_index == 0
                else pk_target_index - 1
            )

        if button_b_was_released():
            pk_target_index = (
                0
                if pk_target_index == len(known_pk_names) - 1
                else pk_target_index + 1
            )

        display.show(known_pk_names[pk_target_index])

    while encrypting_message:
        check_radio()

        code = (
            [str(random.randint(0, 1)) for _ in range(5)]
            if auto_encryptable
            else input_code()
        )

        random_encrypt_animation()
        output_message = create_encryption(output_message)
        display.clear()
        display.show(get_image(message_number))
        encrypt_image(output_message)
        code_string = "".join(code)
        code = []
        ready_to_send = True

        while ready_to_send:
            check_radio()

            if both_buttons_pressed():
                if allow_recipient:
                    display.show(Image.ARROW_E)
                    sleep(1000)
                    known_recipient_list = set_recipients()
                    display.show(known_recipient_list[0] + 1)
                    choosing_recipient = True
                else:
                    sending_message = True

                encrypting_message = False
                ready_to_send = False
                reset_button_states()
                break

    while choosing_recipient:
        check_radio()
        check_serial()

        if both_buttons_pressed():
            sending_message = True
            choosing_recipient = False
            reset_button_states()
            break

        if button_a_was_released():
            recipient_index = (
                len(known_recipient_list) - 1
                if recipient_index == 0
                else recipient_index - 1
            )

        if button_b_was_released():
            recipient_index = (
                0
                if recipient_index == len(known_recipient_list) - 1
                else recipient_index + 1
            )

        display.show(known_recipient_list[recipient_index] + 1)

    while sending_message:
        message_recipient = (
            str(known_recipient_list[recipient_index])
            if allow_recipient or asym_enabled
            else "-1"
        )

        if asym_enabled:
            write_to_computer(
                "encrypt_"
                + str(pack_image(output_message))
                + "_"
                + str(chosen_pk_id)
                + "_"
                + message_recipient
            )
            display.show(Image("99999:09090:00900:09090:99999"))
            wait_for_encryption()
        else:
            send_animation()
            sleep(500)
            send_message(
                "send_"
                + message_recipient
                + "_"
                + str(pack_image(output_message))
                + ("_" + code_string if encryptable else "")
            )

        sending_message = False
        abort_menus()
        show_standby()
