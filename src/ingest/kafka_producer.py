import json
import yaml
from kafka import KafkaProducer

def get_kafka_producer():
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # YAML 주소 연동
    return KafkaProducer(
        bootstrap_servers=config['development']['kafka']['bootstrap_servers'],
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8')
    )

def send_to_kafka(producer, job_data):
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    topic = config['development']['kafka']['topic']
    producer.send(topic, value=job_data)
    producer.flush()