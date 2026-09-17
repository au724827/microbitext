
radioChannel = 1

from microbit import *
import machine
import struct
import radio
import random
import music
import time

uart.init()
print("#dummy&")

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
PING_INACTIVITY_TIMEOUT = 15000

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

def check_radio():
    global output_message, code_string
    global ready_to_send, encrypting_message, choosing_content
    global last_ping_received

    radio_message = radio.receive()

    if radio_message:
        if device_name in radio_message:
            display.clear()
            display.show(int(id_number) + 1)
            output_message = []
            code_string = ""
            ready_to_send = False
            encrypting_message = False
            choosing_content = False

        if (
            "settings" in radio_message
            or "known" in radio_message
            or "image" in radio_message
            or "removeImg" in radio_message
            or "reintroduce" in radio_message
        ):
            machine.reset()

        if "ping" in radio_message:
            last_ping_received = time.ticks_ms()

last_state_a = False
last_state_b = False

def both_buttons_pressed():
        return button_a.is_pressed() and button_b.is_pressed()



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
    global last_state_a, last_state_b
    last_state_a = button_a.is_pressed()
    last_state_b = button_b.is_pressed()
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
    if uart.any():
        print("#dummy&")

    message = radio.receive()

    if message:
        if device_name in message:
            known = True

            if "number" in message:
                parts = message.split("_")
                id_number = parts[2]
                known_recipients = int(parts[3])
                display.show(int(id_number) + 1)

            if "receive" in message:
                parts = message.split("_")
                packed_received_image = parts[2]
                message_sender = int(parts[3])
                code_string = parts[4] if encryptable else ""
                message_complete = True

        if "reintroduce" in message:
            known = False
            last_known_ping = time.ticks_ms() - ((10 - int(id_number)) * 100)
            id_number = "0"
            display.clear()

        if "known" in message:
            known_recipients = int(message.split("_")[1])

        if "image" in message:
            packedNewImage = message.split("_")[2]
            if packedNewImage not in led_images:
                led_images.append(packedNewImage)

        if "removeImg" in message:
            packedImageToRemove = message.split("_")[1]
            if packedImageToRemove in led_images:
                led_images.remove(packedImageToRemove)

        if "settings" in message:
            encryptable = message.split("_")[1] == "1"
            auto_encryptable = message.split("_")[2] == "1"
            allow_recipient = message.split("_")[3] == "1"
            should_beep = message.split("_")[4] == "1"

        if "complete" in message:
            output_message = [[], [], [], [], []]

        if "receive" in message and not allow_recipient:
            parts = message.split("_")
            packed_received_image = parts[2]
            message_sender = int(parts[3])

            if encryptable:
                code_string = parts[4]

            if message_sender != int(id_number):
                message_complete = True

        if "ping" in message:
            last_ping_received = time.ticks_ms()

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
        else:
            sleep(4000)
            display.show(Image.ARROW_W)
            sleep(1000)
            display.show(int(message_sender) + 1)
            reset_microbit_time = True

    if reset_microbit_time:
        sleep(2000)
        display.clear()
        display.show(int(id_number) + 1)
        output_message = []
        code = []
        code_string = ""
        message_sender = 0
        packed_received_image = []
        message_complete = False
        reset_microbit_time = False
        last_recorded_message = time.ticks_ms()

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

            if encryptable:
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
        send_animation()
        sleep(500)

        message_recipient = (
            str(known_recipient_list[recipient_index])
            if allow_recipient
            else "-1"
        )

        send_message(
            "send_"
            + message_recipient
            + "_"
            + str(pack_image(output_message))
            + ("_" + code_string if encryptable else "")
        )

        recipient_index = 0
        message_number = 0
        display.show(int(id_number) + 1)
        sending_message = False