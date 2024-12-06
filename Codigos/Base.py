import network
import time
from machine import Pin, PWM
from umqtt.simple import MQTTClient

# Configuración de WiFi
SSID = "UTNG_GUEST"
PASSWORD = "R3d1nv1t4d0s#UT"

# Configuración MQTT
MQTT_BROKER = "broker.emqx.io"
MQTT_TOPIC_SENSOR = "esp32/sensor/distance"
MQTT_TOPIC_CONTROL = "gds0643/ich/first"
MQTT_PORT = 1883

# Notas musicales
NOTES = {
    'B0': 31, 'C1': 33, 'CS1': 35, 'D1': 37, 'DS1': 39, 'E1': 41, 'F1': 44,
    'FS1': 46, 'G1': 49, 'GS1': 52, 'A1': 55, 'AS1': 58, 'B1': 62, 'C2': 65,
    'CS2': 69, 'D2': 73, 'DS2': 78, 'E2': 82, 'F2': 87, 'FS2': 93, 'G2': 98,
    'GS2': 104, 'A2': 110, 'AS2': 117, 'B2': 123, 'C3': 131, 'CS3': 139,
    'D3': 147, 'DS3': 156, 'E3': 165, 'F3': 175, 'FS3': 185, 'G3': 196,
    'GS3': 208, 'A3': 220, 'AS3': 233, 'B3': 247, 'C4': 262, 'CS4': 277,
    'D4': 294, 'DS4': 311, 'E4': 330, 'F4': 349, 'FS4': 370, 'G4': 392,
    'GS4': 415, 'A4': 440, 'AS4': 466, 'B4': 494, 'C5': 523, 'CS5': 554,
    'D5': 587, 'DS5': 622, 'E5': 659, 'F5': 698, 'FS5': 740, 'G5': 784,
    'GS5': 831, 'A5': 880, 'AS5': 932, 'B5': 988, 'C6': 1047, 'CS6': 1109,
    'D6': 1175, 'DS6': 1245, 'E6': 1319, 'F6': 1397, 'FS6': 1480, 'G6': 1568,
    'GS6': 1661, 'A6': 1760, 'AS6': 1865, 'B6': 1976, 'C7': 2093, 'CS7': 2217,
    'D7': 2349, 'DS7': 2489, 'E7': 2637, 'F7': 2794, 'FS7': 2960, 'G7': 3136,
    'GS7': 3322, 'A7': 3520, 'AS7': 3729, 'B7': 3951, 'C8': 4186
}

melody = [
    'E5', 'D5', 'C5', 'D5', 'E5', None, 'E5', None,
    'E5', 'D5', 'C5', 'D5', 'E5', None, 'C5'
]

durations = [
    0.3, 0.3, 0.3, 0.3, 0.6, 0.3, 0.6, 0.3,
    0.3, 0.3, 0.3, 0.3, 0.6, 0.3, 0.6
]

speed_factor = 0.8

# Hardware inicialización
buzzer = PWM(Pin(27), freq=440, duty=0)
led_pins = [Pin(i, Pin.OUT) for i in (13, 12, 14, 26, 25, 15, 16, 17, 23)]

# Estado inicial para control manual
manual_control = False

def conectar_wifi():
    print("Conectando...", end="")
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect(SSID, PASSWORD)
    while not sta_if.isconnected():
        print(".", end="")
        time.sleep(0.3)
    print("WiFi Conectada!")

def play_tone_with_led(note, duration):
    if note:
        buzzer.freq(NOTES[note])
        buzzer.duty(512)
        for led in led_pins:
            led.on()
        start_time = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_time) < duration * 1000 * speed_factor:
            pass
        buzzer.duty(0)
        for led in led_pins:
            led.off()
        time.sleep(0.05 * speed_factor)

def play_melody():
    for note, duration in zip(melody, durations):
        play_tone_with_led(note, duration)

def manejar_mensaje(topic, msg):
    global manual_control
    if topic == MQTT_TOPIC_SENSOR.encode():
        try:
            distancia = float(msg.decode())
            if not manual_control:
                if distancia <= 20:
                    play_melody()
                else:
                    buzzer.duty(0)
                    for led in led_pins:
                        led.off()
        except Exception:
            pass
    elif topic == MQTT_TOPIC_CONTROL.encode():
        if msg == b"true":
            manual_control = True
            for led in led_pins:
                led.on()
        elif msg == b"false":
            manual_control = False
            for led in led_pins:
                led.off()

# Conexión WiFi y MQTT
conectar_wifi()

cliente = MQTTClient("ESP32_Actuador", MQTT_BROKER, port=MQTT_PORT)
cliente.set_callback(manejar_mensaje)
cliente.connect()
cliente.subscribe(MQTT_TOPIC_SENSOR)
cliente.subscribe(MQTT_TOPIC_CONTROL)
print(f"Conectado al broker {MQTT_BROKER} y suscrito a los tópicos.")

try:
    while True:
        cliente.wait_msg()
except KeyboardInterrupt:
    buzzer.deinit()
    cliente.disconnect()