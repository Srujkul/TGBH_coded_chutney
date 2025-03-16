import csv
import json
from kafka import KafkaProducer

# Kafka Configuration
KAFKA_BROKER = "localhost:9092"  # Update if needed
TOPIC_NAME = "ride_requests"

# Initialize Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# Read CSV file and send messages to Kafka
CSV_FILE_PATH = "ride_requests.csv"

with open(CSV_FILE_PATH, mode="r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        message = {
            "RequestID": int(row["RequestID"]),
            "PassengerID": int(row["PassengerID"]),
            "Source": row["Source"],
            "Destination": row["Destination"],
            "RequestTimestamp": row["RequestTimestamp"]
        }
        producer.send(TOPIC_NAME, message)
        print(f"Sent: {message}")

# Close the producer
producer.flush()
producer.close()

print("Kafka Producer finished sending ride requests.")
