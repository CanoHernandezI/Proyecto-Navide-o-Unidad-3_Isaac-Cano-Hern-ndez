import network
import time
from machine import Pin, PWM
from umqtt.simple import MQTTClient

SSID = "UTNG_GUEST"
PASSWORD = "R3d1nv1t4d0s#UT"

MQTT_BROKER = "broker.emqx.io"
MQTT_TOPIC_DISTANCE = "esp32/sensor/distance"
MQTT_TOPIC_BUTTON = "gds0643/ich/main"
MQTT_PORT = 1883

sensor_activado = False

def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        print("Conectando a Wi-Fi...")
        time.sleep(1)
    print("Conectado:", wlan.ifconfig())

trigger_pin = Pin(26, Pin.OUT)
echo_pin = Pin(27, Pin.IN)

servo1 = PWM(Pin(15), freq=50)
servo2 = PWM(Pin(16), freq=50)
servo3 = PWM(Pin(17), freq=50)

led1_pin = Pin(19, Pin.OUT)
led2_pin = Pin(18, Pin.OUT)

current_angle_servo1 = 0
current_angle_servo2 = 0
current_angle_servo3 = 0

def posiServ(servo, current_angle, target_angle, step=3, delay=0.015):
    """
    Controla el movimiento del servo de forma gradual y rápida, pero suave.
    - step: Incremento en grados por iteración (ajustado a 3 para suavidad).
    - delay: Tiempo de espera entre incrementos (reducido a 0.015 para mayor rapidez).
    """
    if current_angle < target_angle:
        for angle in range(current_angle, target_angle + 1, step):
            duty = int(25 + (angle / 180) * 100)
            servo.duty(duty)
            time.sleep(delay)
    else:
        for angle in range(current_angle, target_angle - 1, -step):
            duty = int(25 + (angle / 180) * 100)
            servo.duty(duty)
            time.sleep(delay)
    return target_angle

def medir_distancia():
    trigger_pin.off()
    time.sleep_us(2)
    trigger_pin.on()
    time.sleep_us(10)
    trigger_pin.off()
    
    while echo_pin.value() == 0:
        inicio = time.ticks_us()
    while echo_pin.value() == 1:
        fin = time.ticks_us()
    
    duracion = time.ticks_diff(fin, inicio)
    distancia = (duracion / 2) / 29.1
    return distancia

def llegada_mensaje(topic, msg):
    global sensor_activado
    print(f"Mensaje recibido: {msg.decode()}")
    if topic.decode() == MQTT_TOPIC_BUTTON:
        if msg == b'true':
            sensor_activado = True
            print("Sensor activado")
        elif msg == b'false':
            sensor_activado = False
            print("Sensor desactivado")

conectar_wifi()

cliente = MQTTClient("ESP32_Sensor", MQTT_BROKER, port=MQTT_PORT)
cliente.set_callback(llegada_mensaje)
cliente.connect()
cliente.subscribe(MQTT_TOPIC_BUTTON)

print("Conectado al broker MQTT y suscrito al tópico.")

try:
    while True:
        cliente.check_msg()  
        
        if sensor_activado:
            distancia = medir_distancia()
            print(f"Distancia medida: {distancia:.2f} cm")
            
            cliente.publish(MQTT_TOPIC_DISTANCE, str(distancia))
            
            if distancia <= 20:
                led1_pin.on()
                led2_pin.on()
                for angle in [40, 0]:
                    current_angle_servo1 = posiServ(servo1, current_angle_servo1, angle)
                    current_angle_servo2 = posiServ(servo2, current_angle_servo2, angle)
                    current_angle_servo3 = posiServ(servo3, current_angle_servo3, angle)
                    time.sleep(0.2)
            else:
                led1_pin.off()
                led2_pin.off()
                current_angle_servo1 = posiServ(servo1, current_angle_servo1, 0)
                current_angle_servo2 = posiServ(servo2, current_angle_servo2, 0)
                current_angle_servo3 = posiServ(servo3, current_angle_servo3, 0)
            time.sleep(1)
        else:
            led1_pin.off()
            led2_pin.off()
            current_angle_servo1 = posiServ(servo1, current_angle_servo1, 0)
            current_angle_servo2 = posiServ(servo2, current_angle_servo2, 0)
            current_angle_servo3 = posiServ(servo3, current_angle_servo3, 0)
            time.sleep(1)

except KeyboardInterrupt:
    cliente.disconnect()
    print("Desconectado del broker MQTT")

