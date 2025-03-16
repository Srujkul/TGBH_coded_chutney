from flask import Flask, request, jsonify
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

app = Flask(__name__)

# Global list to store requests received from the client
requests_list = []

# API endpoint to get all requests
@app.route('/requests', methods=['GET'])
def get_requests():
    return jsonify(requests_list)

# API endpoint to receive requests from the client
@app.route('/send_request', methods=['POST'])
def receive_request():
    data = request.json
    print(f"New request received: {data}")  # For logging purposes
    producer.send(TOPIC_NAME, data)
    print(f"Sent: {data}")
    requests_list.append(data)
    return jsonify({"message": "Request received successfully!"}), 200

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5001)