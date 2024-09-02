import os
import time
import uuid
from confluent_kafka import SerializingProducer
import simplejson as json
from datetime import datetime, timedelta
import random

LONDON_COORDINATES = {'latitude': 51.5074, 'longitude': 52.4862}
BIRMINGHAM_COORDINATES = {'latitude': 51.5074,  'longitude': 52.4862}

#calculate movement
LATITUDE_INCREMENT = BIRMINGHAM_COORDINATES['latitude'] - LONDON_COORDINATES['latitude']/100
LONGITUDE_INCREMENT = BIRMINGHAM_COORDINATES['longitude'] - LONDON_COORDINATES['longitude']/100

#environment variable setup
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')

VEHICLE_TOPIC = os.getenv('VEHICLE_TOPIC', 'vehicle_data')
GPS_TOPIC = os.getenv('GPS_TOPIC', 'gps_data')
CAMERA_TOPIC = os.getenv('CAMERA_TOPIC', 'camera_data')
WEATHER_TOPIC = os.getenv('WEATHER_TOPIC', 'weather_data')
EMERGENCY_TOPIC = os.getenv('EMERGENCY_TOPIC', 'emergency_data')

random.seed(42)
start_time = datetime.now()
start_location = LONDON_COORDINATES.copy()

def get_next_time():
    global start_time
    start_time += timedelta(seconds=random.randint(30, 60))
    return start_time

def generate_gps_data(device_id, timestamp, vehicle_type='private'):
    return {
        'id': uuid.uuid4(),
        'device_id': device_id,
        'timestamp': timestamp,
        'speed': random.uniform(0, 40),
        'direction': 'North-East',
        'vehicle_type': vehicle_type
    }

def generate_traffic_camera_date(device_id, timestamp, location, camera_id):
    return {
        'id': uuid.uuid4(),
        'device_id': device_id,
        'camera_id': camera_id,
        'location': location,
        'timestamp': timestamp,
        'snapshot': 'Base64EncodedString'
    }

def generate_weather_data(device_id, timestamp, location):
    return {
        'id': uuid.uuid4(),
        'device_id': device_id,
        'timestamp': timestamp,
        'location': location,
        'temperature': random.uniform(-5, 26),
        'weatherCondition': random.choice(['Sunny', 'Cloudy', 'Rain', 'Snow']),
        'precipitation': random.uniform(0, 25),
        'windSpeed': random.uniform(0, 100),
        'humidity': random.randint(0, 100),
        'airQualityIndex': random.uniform(0, 500)

    }

def generate_emergency_date(device_id, timestamp, location):
    return {
        'id': uuid.uuid4(),
        'device_id': device_id,
        'incident_id': uuid.uuid4(),
        'timestamp': timestamp,
        'type': random.choice(['Accident', 'Fire', 'Medical', 'Police', 'None']),
        'location': location,
        'status': random.choice(['Active', 'Resolved']),
        'description': 'Description of the incident '
    }

def simulate_vehicle_movement():
    global start_location
    #move towards bermingham
    start_location['latitude'] += LATITUDE_INCREMENT
    start_location['longitude'] += LONGITUDE_INCREMENT

    #adding randomness to simulate actual road travel
    start_location['latitude'] += random.uniform(-0.0005, 0.0005)
    start_location['longitude'] += random.uniform(-0.0005, 0.0005)

    return start_location


def generate_vehicle_date(device_id):
    location = simulate_vehicle_movement()
    return {
        'id': uuid.uuid4(),
        'deviceId': device_id,
        'timestamp': get_next_time().isoformat(),
        'location': (location['latitude'], location['longitude']),
        'speed': random.uniform(10, 40),
        'direction': 'North-East',
        'make': 'BMW',
        'model': '530D',
        'year': '2024',
        'fuelType': 'Hybrid'

    }

def json_serializer(obj):
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')


def produce_data_to_kafka(producer, topic, data):
    producer.produce(
        topic,
        key=str(data['id']),
        value=json.dumps(data, default=json_serializer).encode('utf-8'),
        on_delivery=delivery_report
    )

    producer.flush()

def simulate_journey(producer, device_id):
    while True:
        vehicle_data = generate_vehicle_date(device_id)
        gps_data = generate_gps_data(device_id, vehicle_data['timestamp'])
        camera_data = generate_traffic_camera_date(device_id, vehicle_data['timestamp'], vehicle_data['location'], camera_id='Nikon_Cam123')
        weather_data = generate_weather_data(device_id, vehicle_data['timestamp'], vehicle_data['location'])
        emergency_date = generate_emergency_date(device_id, vehicle_data['timestamp'], vehicle_data['location'])

        if (vehicle_data['location'][0] >= BIRMINGHAM_COORDINATES['latitude']
                and vehicle_data['location'][1] <= BIRMINGHAM_COORDINATES['longitude']):
            print(f'Vehicle has reached Birmingham. Simulation ending.....')
            break

        produce_data_to_kafka(producer, VEHICLE_TOPIC, vehicle_data)
        produce_data_to_kafka(producer, GPS_TOPIC, gps_data)
        produce_data_to_kafka(producer, CAMERA_TOPIC, camera_data)
        produce_data_to_kafka(producer, WEATHER_TOPIC, weather_data)
        produce_data_to_kafka(producer, EMERGENCY_TOPIC, emergency_date)

        time.sleep(5)


if __name__ == "__main__":
    producer_config = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'error_cb': lambda err: print(f'kafka error {err}')
    }
    producer = SerializingProducer(producer_config)
    try:
        simulate_journey(producer, 'vehicles-k-929')

    except KeyboardInterrupt:
        print(f'Simulation ended by User')
    except Exception as e:
        print(f'Unexpected Error occurred: {e}')


