import paho.mqtt.client as mqtt
import time

class IrrigationMonitoringSystem:
    def __init__(self, broker, port, topic):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = mqtt.Client()
        self.soil_moisture = 0
        self.irrigation_status = False

    def connect(self):
        self.client.connect(self.broker, self.port)
        self.client.loop_start()
        print("Connected to MQTT broker")

    def on_message(self, client, userdata, message):
        self.soil_moisture = float(message.payload.decode())
        print(f"Soil moisture level: {self.soil_moisture}")
        self.analyze_data()

    def analyze_data(self):
        if self.soil_moisture < 30:
            self.control_irrigation(True)
        else:
            self.control_irrigation(False)

    def control_irrigation(self, status):
        if status and not self.irrigation_status:
            print("Turning on irrigation...")
            self.irrigation_status = True
            self.client.publish('irrigation/control', 'ON')
        elif not status and self.irrigation_status:
            print("Turning off irrigation...")
            self.irrigation_status = False
            self.client.publish('irrigation/control', 'OFF')

    def start(self):
        self.client.on_message = self.on_message
        self.client.subscribe(self.topic)
        print(f"Subscribed to topic: {self.topic}")
        while True:
            time.sleep(1)

if __name__ == '__main__':
    irrigation_system = IrrigationMonitoringSystem(broker='mqtt.example.com', port=1883, topic='sensor/soil_moisture')
    irrigation_system.connect()
    irrigation_system.start()