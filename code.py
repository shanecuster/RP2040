import time
from adafruit_macropad import MacroPad

# 1. Initialize
macropad = MacroPad()
macropad.pixels.brightness = 0.2

# 2. System76 Color Wave Engine (Now with Layer Shifting)
def get_s76_color(index, time_val, layer_shift=0.0):
    speed = 0.1
    offset = index * 0.15
    # We add the layer_shift to the position calculation
    pos = ((time_val * speed) + offset + layer_shift) % 1.0

    if pos < 0.25:
        mix = pos / 0.25
        return (255, int(60 * (1 - mix)), int(150 * mix))
    elif pos < 0.5:
        mix = (pos - 0.25) / 0.25
        return (int(255 * (1 - mix)), int(255 * mix), int(150 * (1 - mix) + 255 * mix))
    elif pos < 0.75:
        mix = (pos - 0.5) / 0.25
        return (0, int(255 * (1 - mix)), 255)
    else:
        mix = (pos - 0.75) / 0.25
        return (int(255 * mix), int(60 * mix), int(255 * (1 - mix)))

# 3. Multi-Layer Setup
current_layer = 0

layers = [
    {
        "name": "LAYER ONE",
        "keys": [
            ("FOOT", "GUI+RETURN"),  ("OVER", "GUI+W"),      ("DOLP", "GUI+E"),
            ("COPY", "CONTROL+C"),   ("PAST", "CONTROL+SHIFT+V"), ("ALL", "CONTROL+A"),
            ("SPOT", "GUI+S"),       ("DISC", "GUI+SHIFT+D"),     ("OBSI", "GUI+O"),
            ("BTOP", "GUI+SHIFT+B"), ("BITW", "GUI+SHIFT+Y"),     ("MAIL", "GUI+SHIFT+T")
        ]
    },
    {
        "name": "LAYER TWO",
        "keys": [
            ("ZEN", "GUI+Z"),        ("CHRM", "GUI+SHIFT+G"),     ("PRSA", "GUI+SHIFT+P"),
            ("CALC", "GUI+SHIFT+N"), ("NONE", "NONE"),            ("KATE", "GUI+SHIFT+K"),
            ("NONE", "NONE"),        ("NONE", "NONE"),            ("NONE", "NONE"),
            ("PREV", "PREV"),        ("PLAY", "PLAY"),            ("NEXT", "NEXT")
        ]
    }
]

# Setup Display
text_lines = macropad.display_text(title="SHANE MACROS")
text_lines[0].text = layers[current_layer]["name"]
text_lines.show()

# Trackers
last_encoder_position = macropad.encoder
last_action = time.monotonic()
is_sleeping = False

# Knob hold trackers
knob_press_time = 0
knob_is_pressed = False
knob_handled = False

while True:
    current_time = time.monotonic()
    event = macropad.keys.events.get()
    current_encoder_position = macropad.encoder
    action_detected = False

    # 4. Run Animation based on Layer
    if not is_sleeping:
        # Layer 0 gets 0.0 shift, Layer 1 gets 0.5 shift (halfway across the color wheel)
        shift_amount = 0.0 if current_layer == 0 else 0.5

        for i in range(12):
            macropad.pixels[i] = get_s76_color(i, current_time, shift_amount)

    # 5. Handle Key Presses
    if event:
        action_detected = True
        if event.pressed:
            idx = event.key_number
            label, action = layers[current_layer]["keys"][idx]

            if action != "NONE":
                text_lines[0].text = f"{layers[current_layer]['name']}: {label}"

                if not is_sleeping:
                    macropad.pixels[idx] = (255, 255, 255) # Flash white

                if action == "PLAY": macropad.consumer_control.send(macropad.ConsumerControlCode.PLAY_PAUSE)
                elif action == "NEXT": macropad.consumer_control.send(macropad.ConsumerControlCode.SCAN_NEXT_TRACK)
                elif action == "PREV": macropad.consumer_control.send(macropad.ConsumerControlCode.SCAN_PREVIOUS_TRACK)
                else:
                    keycodes = [getattr(macropad.Keycode, k) for k in action.split('+')]
                    macropad.keyboard.send(*keycodes)

    # 6. Handle Knob Turns (Volume)
    if current_encoder_position != last_encoder_position:
        action_detected = True
        if current_encoder_position > last_encoder_position:
            macropad.consumer_control.send(macropad.ConsumerControlCode.VOLUME_INCREMENT)
        else:
            macropad.consumer_control.send(macropad.ConsumerControlCode.VOLUME_DECREMENT)
        last_encoder_position = current_encoder_position

    # 7. Handle Knob Long-Press Logic
    current_switch_state = macropad.encoder_switch

    if current_switch_state:
        if not knob_is_pressed:
            knob_is_pressed = True
            knob_press_time = current_time
            knob_handled = False

        elif not knob_handled and (current_time - knob_press_time > 0.5):
            current_layer = (current_layer + 1) % len(layers)
            text_lines[0].text = layers[current_layer]["name"]
            macropad.pixels.fill((255, 255, 255))
            time.sleep(0.15)
            knob_handled = True
            action_detected = True

    else:
        if knob_is_pressed:
            knob_is_pressed = False
            if not knob_handled:
                macropad.consumer_control.send(macropad.ConsumerControlCode.MUTE)
                text_lines[0].text = f"{layers[current_layer]['name']}: MUTE"
                macropad.pixels.fill((255, 0, 0))
                time.sleep(0.2)
                text_lines[0].text = layers[current_layer]["name"]
                action_detected = True

    # 8. Auto-Sleep Logic
    if action_detected:
        last_action = current_time
        if is_sleeping:
            macropad.display.brightness = 1.0
            is_sleeping = False

    if not is_sleeping and (current_time - last_action > 60):
        macropad.pixels.fill((0, 0, 0))
        macropad.display.brightness = 0.0
        is_sleeping = True
