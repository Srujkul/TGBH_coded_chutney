from kafka import KafkaConsumer
import json
import time
import subprocess

# Kafka Configuration
KAFKA_BROKER = "localhost:9092"
TOPIC_NAME = "ride_requests"

# Initialize Kafka Consumer
consumer = KafkaConsumer(
    TOPIC_NAME,
    bootstrap_servers=KAFKA_BROKER,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=lambda v: json.loads(v.decode("utf-8"))
)

print("Kafka Consumer started, listening for messages...")

batch_messages = []
last_run_time = time.time()  # Track last Spark run time

for message in consumer:
    batch_messages.append(message.value)
    print(f"Received: {message.value}")

    # Trigger batch processing every 20 seconds
    if time.time() - last_run_time >= 40 and batch_messages:
        print(f"Processing {len(batch_messages)} messages in batch...")

        # Save batch messages to a JSON file (temporary storage)
        with open("batch_data.json", "w") as f:
            json.dump(batch_messages, f)

        # Trigger Spark processing
        subprocess.run(["python3", "spark_processor.py"])

        # Clear batch
        batch_messages = []
        last_run_time = time.time()  # Reset timer
