import machine
import time
import math
import neopixel
import uasyncio as asyncio

LONG_PRESS_TIME = 0.5 # s
DOUBLE_CLICK_TIME = 0.20 # s
ARGB_COUNT = 38
COLOURS = {
    0: (255, 0, 0), # Red
    1: (0, 128, 255), # Blue
    2: (255, 0, 255), # Purple
    3: (255, 32, 0) # Orange
}
BREATH_SCALE = 256
BREATH_TABLE = [int((math.sin(i / BREATH_SCALE * math.pi) ** 2) * BREATH_SCALE) for i in range(BREATH_SCALE+1)]
BREATH_DELAY = 20 # ms

btn = machine.Pin(0, machine.Pin.IN, machine.Pin.PULL_UP)
onboard_led = neopixel.NeoPixel(machine.Pin(16, machine.Pin.OUT), 1)
argb_led = neopixel.NeoPixel(machine.Pin(8, machine.Pin.OUT), ARGB_COUNT)

global_led_state = True
global_current_colour = 0
global_fade = False
global_breath_index = int(BREATH_SCALE/2)

def read_settings(filename="argb_settings.db"):
    try:
        with open(filename, "r") as f:
            lines = [line.strip() for line in f if line.strip()]
            
            if len(lines) < 3:
                raise ValueError("Settings file does not have enough lines")
                      
            led_state = lines[0].lower() == "true"
            current_colour = int(lines[1])
            fade = lines[2].lower() == "true"
            
            return led_state, current_colour, fade

    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return True, 0, False

def save_settings(led_state, current_colour, fade, filename="argb_settings.db"):
    try:
        with open(filename, "w") as f:
            f.write(f"{led_state}\n")
            f.write(f"{current_colour}\n")
            f.write(f"{fade}\n")
    except Exception as e:
        print(f"Error saving {filename}: {e}")
    
def flip(i):
    if i < len(COLOURS)-1:
        return i+1
    else:
        return 0

async def the_button():
    global global_current_colour
    global global_led_state
    global global_fade
    global global_breath_index
    
    pressed = False
    press_time = 0
    release_time = 0
    duration = 0
    click_pending = False

    while True:
        state = btn.value()
        now = time.ticks_ms()
        if pressed:
            duration = (now - press_time) / 1000
        
        # Button pressed
        if not state and not pressed:
            pressed = True
            press_time = now
            
        # Long press
        if pressed and duration >= LONG_PRESS_TIME:
            pressed = False
            global_led_state = not global_led_state
            duration = 0
            save_settings(global_led_state, global_current_colour, global_fade)
            while not btn.value():
                await asyncio.sleep(0.01)
            
        else:
            # Button released
            if state and pressed:
                pressed = False
                
                # short press. could be single or double
                if click_pending:
                    # second click within allowed double click time
                    if (now - release_time) <= (DOUBLE_CLICK_TIME * 1000):
                        if global_led_state:
                            global_fade = not global_fade
                            # reset the breath index so we start by fading out from
                            # full light
                            if not global_fade:
                                global_breath_index = int(BREATH_SCALE/2)
                        save_settings(global_led_state, global_current_colour, global_fade)
                        click_pending = False
                # first click, wait to se if double click happens
                else:
                    click_pending = True
                    release_time = now
                        
            # check if double click expireed
            if click_pending:
                if (now - release_time) > (DOUBLE_CLICK_TIME * 1000):
                    if global_led_state:
                        global_current_colour = flip(global_current_colour)
                    save_settings(global_led_state, global_current_colour, global_fade)
                    click_pending = False
            
        await asyncio.sleep(0.01)
        
def led_off():
    return(0, 0, 0)

def fade(colour, step):
    r, g, b = colour
    scale = BREATH_TABLE[step] / BREATH_SCALE
    return (int(r * scale), int(g * scale), int(b * scale))
 
async def update_leds(neopixel, led_count):
    global global_breath_index
    
    if not global_led_state:
        for i in range(led_count):
            neopixel[i] = led_off()
        neopixel.write()
        return
    
    if not global_fade:
        for i in range(led_count):
            neopixel[i] = COLOURS[global_current_colour]
        neopixel.write()
        return
    
    # breathing          
    for i in range(led_count):
        neopixel[i] = fade(COLOURS[global_current_colour], global_breath_index)
    
    neopixel.write()
    global_breath_index = (global_breath_index + 1) % (BREATH_SCALE+1)
    await asyncio.sleep_ms(BREATH_DELAY)
    
async def le_leds():
    while True:
        await update_leds(onboard_led, 1)
        await update_leds(argb_led, ARGB_COUNT)
        await asyncio.sleep(0.01)
        
async def main():
    global global_led_state
    global global_current_colour
    global global_fade
    global_led_state, global_current_colour, global_fade = read_settings()
    
    asyncio.create_task(the_button())
    asyncio.create_task(le_leds())
    
    while True:
        await asyncio.sleep_ms(1)

asyncio.run(main())
    
        
        
