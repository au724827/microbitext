# All microbits in a group should be on the same radio channel
radioChannel = 1 # If compiled through the web interface, this will be replaced with the value from the settings page.

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
wrong_message = False
pitch_list = [6, 8, 10, 12]
reset_microbit_time = False
last_ping_received = 0
PING_INACTIVITY_TIMEOUT = 15000


def show_inner_dot_animation():
    frames = [
        "00000:09000:00000:00000:00000",
        "00000:00900:00000:00000:00000",
        "00000:00090:00000:00000:00000",
        "00000:00000:00090:00000:00000",
        "00000:00000:00000:00090:00000",
        "00000:00000:00000:00900:00000",
        "00000:00000:00000:09000:00000",
        "00000:00000:09000:00000:00000",
    ]

    frame = time.ticks_ms() // 120 % len(frames)
    display.show(Image(frames[frame]))


led_images = [
    [
        [0, 0, 0, 0, 0],
        [0, 1, 0, 1, 0],
        [0, 0, 0, 0, 0],
        [1, 0, 0, 0, 1],
        [0, 1, 1, 1, 0],
    ],
    [
        [0, 0, 0, 0, 0],
        [0, 1, 0, 1, 0],
        [0, 0, 0, 0, 0],
        [0, 1, 1, 1, 0],
        [1, 0, 0, 0, 1],
    ],
]

send_image_base = [
    [0, 0, 1, 0, 0],
    [0, 1, 1, 1, 0],
    [1, 0, 1, 0, 1],
    [0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0],
]

send_image_offsets = [3, 2, 1, 0, -1, -2, -3, -4, -5]

message_complete = False
message_sender = 0
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
bit_by_bit_input = False

radio.config(group=radioChannel, data_rate=radio.RATE_1MBIT, queue=10, channel=42)
radio.on()


def microbit_friendly_name():
    length = 5
    letters = 5
    codebook = [
        ["z", "v", "g", "p", "t"],
        ["u", "o", "i", "e", "a"],
        ["z", "v", "g", "p", "t"],
        ["u", "o", "i", "e", "a"],
        ["z", "v", "g", "p", "t"],
    ]
    name = []

    _, n = struct.unpack("II", machine.unique_id())
    ld = 1
    d = letters

    for i in range(0, length):
        h = (n % d) // ld
        n -= h
        d *= letters
        ld *= letters
        name.insert(0, codebook[i][h])

    return "".join(name)


device_name = str(microbit_friendly_name())


def send_message(message_to_send):
    radio.send(device_name + "_" + str(message_to_send))


def get_image(image_index):
    return matrix_to_image(led_images[image_index])


def build_send_image(frame_index):
    image = [[0, 0, 0, 0, 0] for _ in range(5)]
    offset = send_image_offsets[frame_index]
    for y in range(5):
        shifted_y = y + offset
        if shifted_y < 0 or shifted_y > 4:
            continue
        for x in range(5):
            image[shifted_y][x] = send_image_base[y][x]
    return image


def matrix_to_image(matrix):
    rows = ["".join(str(int(x) * 9) for x in row) for row in matrix]
    return ":".join(rows)


def set_recipients():
    global known_recipient_list

    known_recipient_list = []
    for i in range(known_recipients):
        if i is not int(id_number):
            known_recipient_list.append(i)
    return known_recipient_list


def send_animation():
    for i in range(len(send_image_offsets)):
        display.show(Image(matrix_to_image(build_send_image(i))))
        sleep(100)
    display.clear()


def create_encryption(message_list):
    for j in range(5):
        if int(code[j]) > 0:
            for k in range(5):
                if message_list[k][j] > 0:
                    message_list[k][j] = 0
                else:
                    message_list[k][j] = 1
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
            led_strength = int(image_list[k][j])
            display.set_pixel(j, k, led_strength * 9)
        sleep(100)


def random_encrypt_animation():
    display.clear()
    for _ in range(2):
        for j in range(5):
            for k in range(5):
                if random.randint(0, 1) > 0:
                    display.set_pixel(k, j, 9)
                else:
                    display.set_pixel(k, j, 0)
        sleep(500)
    display.clear()


def display_code_input(code):
    display.clear()
    for i in range(len(code)):
        if int(code[i]) > 0:
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
            for bit in "{:05b}".format(int(c) + 26 if c.isdigit() else ord(c) - 65)
        ]
        for c in payload
    ]


def check_radio():
    global output_message, code_string, ready_to_send, encrypting_message, choosing_content

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
            global last_ping_received
            last_ping_received = time.ticks_ms()


def both_buttons_pressed():
    return button_a.is_pressed() and button_b.is_pressed()


last_state_a = False
last_state_b = False


def button_a_was_released():
    global last_state_a

    current_state = button_a.is_pressed()
    released = (last_state_a == True) and (current_state == False)

    last_state_a = current_state
    return released


def button_b_was_released():
    global last_state_b

    current_state = button_b.is_pressed()
    released = (last_state_b == True) and (current_state == False)

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


CLICK_MS = 450


def input_image_bit_by_bit():
    while button_a.is_pressed() or button_b.is_pressed():
        sleep(10)
    reset_button_states()
    sleep(80)
    reset_button_states()
    display.clear()
    m = [[0, 0, 0, 0, 0] for _ in range(5)]
    p = 0
    ls = None
    sx = 0
    st = 0
    at = 0
    att = 0
    pa = 0
    bk = True
    bt = time.ticks_ms()
    nd = True
    while True:
        check_radio()
        n = time.ticks_ms()
        if p < 25 and time.ticks_diff(n, bt) >= 450:
            bk = not bk
            bt = n
            nd = True
        if pa and at < 3 and time.ticks_diff(n, pa) >= CLICK_MS:
            if p < 25:
                m[p // 5][p % 5] = 0
                p += 1
                ls = "A"
                sx = 0
                st = n
            pa = 0
            at = 0
            nd = True
        b = None
        if button_a_was_released():
            b = "A"
        elif button_b_was_released():
            b = "B"
        if b == "A":
            pa = 0
            at = (at + 1) if time.ticks_diff(n, att) < CLICK_MS else 1
            att = n
            if at >= 3 and p > 0:
                p -= 1
                m[p // 5][p % 5] = 0
                at = 0
                ls = None
                nd = True
            elif p < 25 and at < 3:
                pa = n
        elif b == "B":
            pa = 0
            at = 0
            if ls == "B" and time.ticks_diff(n, st) < CLICK_MS:
                sx += 1
                if sx >= 2 and p > 0:
                    p -= 1
                    m[p // 5][p % 5] = 0
                    ls = None
                    sx = 0
                    nd = True
            elif p < 25:
                m[p // 5][p % 5] = 1
                p += 1
                ls = "B"
                sx = 0
                st = n
                nd = True
        if p >= 25 and both_buttons_pressed():
            while button_a.is_pressed() or button_b.is_pressed():
                sleep(10)
            reset_button_states()
            return m
        if nd:
            for r in range(5):
                for c in range(5):
                    i = r * 5 + c
                    v = 0
                    if p >= 25 or i < p:
                        v = 9 if m[r][c] else 1
                    elif bk:
                        v = 5
                    display.set_pixel(c, r, v)
            nd = False
        sleep(20)


while True:
    if uart.any():
        print("#dummy&") # Indicate that this is a dummy micro:bit, so that the computer doesn't try to send messages to it
		
	
    message = radio.receive()
    if message:
        if device_name in message:
            known = True
            if "number" in message:
                id_number = message.split("_")[2]
                known_recipients = int(message.split("_")[3])
                display.show(int(id_number) + 1)
            if "receive" in message:
                messageComponents = message.split("_")

                packed_received_image = str(messageComponents[2])
                message_sender = int(messageComponents[3])
                code_string = messageComponents[4] if encryptable else ""

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
            unpackedNewImage = unpack_image(packedNewImage)
            if not unpackedNewImage in led_images:
                led_images.append(unpackedNewImage)
        if "removeImg" in message:
            packedImageToRemove = message.split("_")[1]
            unpackedImageToRemove = unpack_image(packedImageToRemove)
            if unpackedImageToRemove in led_images:
                led_images.remove(unpackedImageToRemove)
        if "settings" in message:
            encryptable = message.split("_")[1] == "1"
            auto_encryptable = message.split("_")[2] == "1"
            allow_recipient = message.split("_")[3] == "1"
            should_beep = message.split("_")[4] == "1"
            bit_by_bit_input = message.split("_")[5] == "1"

        if "complete" in message:
            output_message = [[], [], [], [], []]
        if "receive" in message and not allow_recipient:
            messageComponents = message.split("_")

            packed_received_image = str(messageComponents[2])
            message_sender = int(messageComponents[3])

            if encryptable:
                code_string = messageComponents[4]

            if message_sender != int(id_number):
                message_complete = True
        if "ping" in message:
            last_ping_received = time.ticks_ms()

    if known and (time.ticks_ms() - last_ping_received) > PING_INACTIVITY_TIMEOUT:
        machine.reset()  # Reset the micro:bit if no ping has been received for a certain duration

    if message_complete:
        reset_button_states()

        if should_beep:
            for i, pitch in enumerate(pitch_list):
                if wrong_message:
                    music.pitch(pitch_list[(len(pitch_list) - 1) - i] * 100)
                else:
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
        wrong_message = False
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
        display.show(
            Image("99999:" "99099:" "90909:" "90009:" "99999")
        )
        sleep(1000)
        display.show(Image(get_image(0)))
        choosing_content = True
        reset_button_states()

    custom_draw_index = len(led_images)
    custom_draw_preview = Image("00900:" "09990:" "99999:" "00900:" "00900")
    ls = -1
    while choosing_content:
        check_radio()

        if both_buttons_pressed():
            if bit_by_bit_input and message_number == custom_draw_index:
                output_message = input_image_bit_by_bit()
            else:
                output_message = [[], [], [], [], []]
                for i in range(5):
                    for j in range(5):
                        output_message[i].append(led_images[message_number][i][j])
            if encryptable:
                display.show(Image("00000:" "09000:" "90999:" "09009:" "00000"))
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

        max_index = custom_draw_index if bit_by_bit_input else len(led_images) - 1
        if button_a_was_released():
            message_number = max_index if message_number == 0 else message_number - 1

        if button_b_was_released():
            message_number = 0 if message_number == max_index else message_number + 1

        if bit_by_bit_input and message_number == custom_draw_index:
            if ls != custom_draw_index:
                display.show(custom_draw_preview)
                ls = custom_draw_index
        elif ls != message_number:
            display.show(Image(get_image(message_number)))
            ls = message_number
        sleep(50)

    while encrypting_message:
        check_radio()
        code = (
            [str(random.randint(0, 1)) for _ in range(5)]
            if auto_encryptable
            else input_code()
        )

        original_message = [row[:] for row in output_message]
        random_encrypt_animation()
        output_message = create_encryption(output_message)
        display.clear()
        display.show(Image(matrix_to_image(original_message)))
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

        send_message(
            "send_"
            + (str(known_recipient_list[recipient_index]) if allow_recipient else "-1")
            + "_"
            + str(pack_image(output_message))
            + ("_" + code_string if encryptable else "")
        )

        recipient_index = 0
        message_number = 0
        display.show(int(id_number) + 1)
        sending_message = False
