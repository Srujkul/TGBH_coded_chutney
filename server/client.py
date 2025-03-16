import requests
import random
import time
import mysql.connector
import threading
from datetime import datetime

# The URL for the server's POST endpoint
SERVER_URL = "http://127.0.0.1:5001/send_request"

# Database connection configuration
db_config = {
    "host": "172.25.160.1",
    "user": "root",
    "password": "thanishkn11",
    "database": "CodedChutney"
}

def get_random_area():
    """Fetch a random source and destination from the 'area' table."""
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("SELECT AreaName FROM area ORDER BY RAND() LIMIT 2")
    areas = cursor.fetchall()

    cursor.close()
    conn.close()

    if len(areas) == 2:
        return areas[0][0], areas[1][0]  # Return source and destination
    return None, None

def get_random_passenger():
    """Fetch a random passenger ID from the 'passenger' table."""
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("SELECT PassengerID FROM passenger ORDER BY RAND() LIMIT 1")
    passenger = cursor.fetchone()

    cursor.close()
    conn.close()

    if passenger:
        return passenger[0]
    return None

def generate_and_send_request():
    """Generate and send ride requests to the server."""
    while True:
        source, destination = get_random_area()
        passenger_id = get_random_passenger()
        request_id = random.randint(1000, 9999)  # Generate a random RequestID

        if source and destination and passenger_id:
            ride_request = {
                "RequestID": request_id,
                "PassengerID": passenger_id,
                "Source": source,
                "Destination": destination,
                "RequestTimestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            try:
                response = requests.post(SERVER_URL, json=ride_request)
                if response.status_code == 200:
                    print(f"Request sent successfully: {ride_request}")
                else:
                    print(f"Failed to send request. Status: {response.status_code}, Response: {response.text}")
            except requests.exceptions.RequestException as e:
                print(f"Request error: {e}")

        time.sleep(0.5)  # Wait 0.5 seconds before sending the next request

def start_threads(num_threads=3):
    """Start multiple threads for sending requests."""
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=generate_and_send_request, daemon=True)
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()

if __name__ == '__main__':
    start_threads()
