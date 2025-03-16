from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from mysql.connector import Error
from decimal import Decimal
import json
import time
import pandas as pd
import folium # type: ignore
from folium.plugins import HeatMap # type: ignore
from flask_socketio import SocketIO # type: ignore
import requests
from demand import get_highest_demand_nearby_areas 

app = Flask(__name__)
app.secret_key = "nammayatrisecretkey123"
socketio = SocketIO(app, cors_allowed_origins="*")

db_config = {
    "host": "172.25.160.1",
    "user": "root",
    "password": "thanishkn11",
    "database": "CodedChutney"
}

# Database connection function
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='172.25.160.1',
            database='CodedChutney',
            user='root',  # Replace with your MySQL username
            password='thanishkn11'  # Replace with your MySQL password
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        return None

# Home/Login page
@app.route('/')
def index():
    return render_template('index.html')

# Passenger login
@app.route('/login/passenger', methods=['POST'])
def passenger_login():
    passenger_id = request.form['passenger_id']
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Passenger WHERE PassengerID = %s", (passenger_id,))
        passenger = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if passenger:
            return redirect(f"/passenger/{passenger_id}")
        else:
            flash("Invalid Passenger ID")
            return redirect("/")
    return "Database connection error", 500

# Driver login
@app.route('/login/driver', methods=['POST'])
def driver_login():
    driver_id = request.form['driver_id']
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Driver WHERE DriverID = %s", (driver_id,))
        driver = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if driver:
            return redirect(f"/driver/{driver_id}")
        else:
            flash("Invalid Driver ID")
            return redirect("/")
    return "Database connection error", 500

# Passenger page
@app.route('/passenger/<int:passenger_id>')
def passenger_page(passenger_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Get passenger details
        cursor.execute("SELECT * FROM Passenger WHERE PassengerID = %s", (passenger_id,))
        passenger = cursor.fetchone()
        
        if not passenger:
            cursor.close()
            conn.close()
            flash("Passenger not found")
            return redirect("/")
        
        # Get all areas for source/destination dropdowns
        cursor.execute("SELECT AreaName FROM Area")
        locations = [row['AreaName'] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return render_template('user_page.html', 
                              passenger_id=passenger_id,
                              passenger_name=passenger['Name'],
                              gender=passenger['Gender'],
                              age=passenger['Age'],
                              locations=locations)
    return "Database connection error", 500

# Driver page
@app.route('/driver/<int:driver_id>')
def driver_page(driver_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Get driver details
        cursor.execute("""
            SELECT d.*, a.AreaName 
            FROM Driver d
            JOIN Area a ON d.ResidenceID = a.AreaID
            WHERE d.DriverID = %s
        """, (driver_id,))
        driver = cursor.fetchone()
        
        if not driver:
            cursor.close()
            conn.close()
            flash("Driver not found")
            return redirect("/")
        
        cursor.close()
        conn.close()
        
        return render_template('driver_page.html', 
                              driver_id=driver_id,
                              driver_name=driver['Name'],
                              vehicle_num=driver['VehicleNo'],
                              rating=driver['Rating'],
                              area=driver['AreaName'],
                              trips_completed=driver['NoOfTrips'])
    return "Database connection error", 500

# API to estimate fare
# API to estimate fare
@app.route('/api/estimate_fare', methods=['POST'])
def estimate_fare():
    data = request.get_json()
    source = data.get('source')
    destination = data.get('destination')
    service_type = data.get('service_type')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # First try to get fare from the Fares table
        cursor.execute("""
            SELECT Fare_Rupees, Distance_KM 
            FROM Fares 
            WHERE Source = %s AND Destination = %s
        """, (source, destination))
        fare_data = cursor.fetchone()
        
        # If fare not found, check the opposite direction (destination to source)
        if not fare_data:
            cursor.execute("""
                SELECT Fare_Rupees, Distance_KM 
                FROM Fares 
                WHERE Source = %s AND Destination = %s
            """, (destination, source))
            fare_data = cursor.fetchone()
        
        # Get area scores for demand calculation
        cursor.execute("SELECT AreaID, AreaScore FROM Area WHERE AreaName = %s", (source,))
        source_data = cursor.fetchone()
        
        cursor.execute("SELECT AreaID, AreaScore FROM Area WHERE AreaName = %s", (destination,))
        dest_data = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if fare_data and source_data and dest_data:
            # Get base fare from Fares table
            base_fare = float(fare_data['Fare_Rupees'])
            
            # Apply service type multiplier
            if service_type == 'auto':
                multiplier = 1.0
            elif service_type == 'bike':
                multiplier = 0.8
            else:  # car
                multiplier = 1.5
            
            # Calculate demand factor based on area scores
            demand_factor = (source_data['AreaScore'] + dest_data['AreaScore']) / 10
            demand_factor = float(demand_factor)
            
            # Calculate final fare with multiplier and demand factor
            fare = round(base_fare * multiplier * demand_factor, 2)
            
            # Include distance in the response
            distance = fare_data['Distance_KM']
            
            return {
                'fare': fare,
                'distance': float(distance),
                'base_fare': base_fare,
                'service_type': service_type,
                'demand_factor': round(demand_factor, 2)
            }
        elif not fare_data:
            # If no fare data is found in either direction, return an error
            return {'error': 'No fare information available for this route'}, 404
        else:
            # If area data is missing
            return {'error': 'Area information missing'}, 404
    
    return {'error': 'Could not estimate fare'}, 400

# Passenger ride history
@app.route('/passenger/<int:passenger_id>/history')
def passenger_history(passenger_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Get ride history for passenger
        cursor.execute("""
            SELECT b.BookingID, b.BookingTime, b.Status, b.RideRating,
                   d.Name as DriverName, d.VehicleNo,
                   src.AreaName as Source, dst.AreaName as Destination
            FROM Booking b
            JOIN Driver d ON b.DriverID = d.DriverID
            JOIN Area src ON b.SourceID = src.AreaID
            JOIN Area dst ON b.DestID = dst.AreaID
            WHERE b.PassengerID = %s
            ORDER BY b.BookingTime DESC
        """, (passenger_id,))
        rides = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('passenger_history.html', rides=rides, passenger_id=passenger_id)
    return "Database connection error", 500

# Driver ride history and earnings
@app.route('/driver/<int:driver_id>/history')
def driver_history(driver_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Get ride history for driver
        cursor.execute("""
            SELECT b.BookingID, b.BookingTime, b.Status, b.RideRating,
                   p.Name as PassengerName,
                   src.AreaName as Source, dst.AreaName as Destination
            FROM Booking b
            JOIN Passenger p ON b.PassengerID = p.PassengerID
            JOIN Area src ON b.SourceID = src.AreaID
            JOIN Area dst ON b.DestID = dst.AreaID
            WHERE b.DriverID = %s
            ORDER BY b.BookingTime DESC
        """, (driver_id,))
        rides = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('driver_history.html', rides=rides, driver_id=driver_id)
    return "Database connection error", 500

# Book a ride
@app.route('/api/book_ride', methods=['POST'])
def book_ride():
    data = request.get_json()
    passenger_id = data.get('passenger_id')
    source = data.get('source')
    destination = data.get('destination')
    service_type = data.get('service_type')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Get area IDs
        cursor.execute("SELECT AreaID FROM Area WHERE AreaName = %s", (source,))
        source_id = cursor.fetchone()['AreaID']
        
        cursor.execute("SELECT AreaID FROM Area WHERE AreaName = %s", (destination,))
        dest_id = cursor.fetchone()['AreaID']
        
        # Find available driver (simplified)
        cursor.execute("""
            SELECT DriverID FROM Driver 
            WHERE DriverID NOT IN (
                SELECT DriverID FROM Booking 
                WHERE Status IN ('Confirmed', 'Ongoing')
            )
            ORDER BY Rating DESC 
            LIMIT 1
        """)
        driver_result = cursor.fetchone()
        
        if driver_result:
            driver_id = driver_result['DriverID']
            
            # Create new booking
            cursor.execute("""
                INSERT INTO Booking 
                (PassengerID, DriverID, SourceID, DestID, Status) 
                VALUES (%s, %s, %s, %s, 'Confirmed')
            """, (passenger_id, driver_id, source_id, dest_id))
            
            booking_id = cursor.lastrowid
            conn.commit()
            
            # Get driver details
            cursor.execute("""
                SELECT d.Name, d.VehicleNo, d.Rating 
                FROM Driver d 
                WHERE d.DriverID = %s
            """, (driver_id,))
            driver = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'booking_id': booking_id,
                'driver': {
                    'name': driver['Name'],
                    'vehicle': driver['VehicleNo'],
                    'rating': float(driver['Rating'])
                }
            }
        else:
            cursor.close()
            conn.close()
            return {'success': False, 'message': 'No drivers available'}
    
    return {'success': False, 'message': 'Database error'}, 500

@app.route('/api/active_ride/<int:driver_id>', methods=['GET'])
def get_active_ride(driver_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Get active ride with full details
        cursor.execute("""
            SELECT b.*, 
                   p.Name as passenger_name,
                   src.AreaName as source,
                   dst.AreaName as destination
            FROM Booking b
            JOIN Passenger p ON b.PassengerID = p.PassengerID
            JOIN Area src ON b.SourceID = src.AreaID
            JOIN Area dst ON b.DestID = dst.AreaID
            WHERE b.DriverID = %s AND b.Status IN ('Confirmed', 'Ongoing')
            LIMIT 1
        """, (driver_id,))
        
        ride = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({'active_ride': ride})
    
    return jsonify({'active_ride': None, 'error': 'Database connection error'})

@app.route('/api/driver_accept_ride', methods=['POST'])
def driver_accept_ride():
    data = request.get_json()
    booking_id = data.get('booking_id')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Booking SET Status = 'Ongoing' WHERE BookingID = %s", (booking_id,))
        affected_rows = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if affected_rows > 0:
            return jsonify({'success': True, 'message': 'Ride started'})
        else:
            return jsonify({'success': False, 'message': 'Booking not found or already updated'}), 404
    
    return jsonify({'success': False, 'message': 'Database connection error'}), 500

@app.route('/api/driver_cancel_ride', methods=['POST'])
def driver_cancel_ride():
    data = request.get_json()
    booking_id = data.get('booking_id')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Booking SET Status = 'Cancelled' WHERE BookingID = %s", (booking_id,))
        affected_rows = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if affected_rows > 0:
            return jsonify({'success': True, 'message': 'Ride cancelled'})
        else:
            return jsonify({'success': False, 'message': 'Booking not found or already updated'}), 404
    
    return jsonify({'success': False, 'message': 'Database connection error'}), 500

@app.route('/api/driver_complete_ride', methods=['POST'])
def driver_complete_ride():
    data = request.get_json()
    booking_id = data.get('booking_id')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Booking SET Status = 'Completed' WHERE BookingID = %s", (booking_id,))
        affected_rows = cursor.rowcount
        conn.commit()
        
        # Update driver's trip count
        if affected_rows > 0:
            # Get the driver ID for this booking
            cursor.execute("SELECT DriverID FROM Booking WHERE BookingID = %s", (booking_id,))
            result = cursor.fetchone()
            if result:
                driver_id = result[0]
                cursor.execute("UPDATE Driver SET NoOfTrips = NoOfTrips + 1 WHERE DriverID = %s", (driver_id,))
                conn.commit()
        
        cursor.close()
        conn.close()
        
        if affected_rows > 0:
            return jsonify({'success': True, 'message': 'Ride completed'})
        else:
            return jsonify({'success': False, 'message': 'Booking not found or already updated'}), 404
    
    return jsonify({'success': False, 'message': 'Database connection error'}), 500

# Driver earnings page
@app.route('/driver/<int:driver_id>/earnings')
def driver_earnings(driver_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Check if driver exists
        cursor.execute("SELECT * FROM Driver WHERE DriverID = %s", (driver_id,))
        driver = cursor.fetchone()
        
        if not driver:
            cursor.close()
            conn.close()
            flash("Driver not found")
            return redirect("/")
        
        # Get earnings data using the Fares table for accurate fare calculation
        cursor.execute("""
            SELECT 
                b.BookingID, 
                b.BookingTime, 
                b.Status,
                p.Name as PassengerName,
                src.AreaName as Source,
                dst.AreaName as Destination,
                ROUND(f.Distance_KM * 10, 2) as Amount
            FROM Booking b
            JOIN Passenger p ON b.PassengerID = p.PassengerID
            JOIN Area src ON b.SourceID = src.AreaID
            JOIN Area dst ON b.DestID = dst.AreaID
            JOIN Fares f ON src.AreaName = f.Source AND dst.AreaName = f.Destination
            WHERE b.DriverID = %s AND b.Status = 'Completed'
            ORDER BY b.BookingTime DESC
            LIMIT 10
        """, (driver_id,))
        
        earnings_rows = cursor.fetchall()
        
        # Calculate statistics using the actual fare data
        cursor.execute("""
            SELECT 
                COUNT(*) as TotalTrips,
                ROUND(SUM(f.Distance_KM * 10), 2) as TotalEarnings
            FROM Booking b
            JOIN Area src ON b.SourceID = src.AreaID
            JOIN Area dst ON b.DestID = dst.AreaID
            JOIN Fares f ON src.AreaName = f.Source AND dst.AreaName = f.Destination
            WHERE b.DriverID = %s AND b.Status = 'Completed'
        """, (driver_id,))
        
        stats = cursor.fetchone()
        cursor.close()
        conn.close()
        
        total_trips = stats['TotalTrips'] if stats else 0
        total_earnings = stats['TotalEarnings'] if stats else 0
        avg_earnings = round(total_earnings / total_trips, 2) if total_trips > 0 else 0
        
        # Format earnings data for template
        earnings = []
        for row in earnings_rows:
            earnings.append({
                'date': row['BookingTime'].strftime('%d %b %Y, %I:%M %p'),
                'passenger': row['PassengerName'],
                'source': row['Source'],
                'destination': row['Destination'],
                'amount': row['Amount']
            })
        
        return render_template('driver_earnings.html', 
                              driver_id=driver_id,
                              total_earnings=total_earnings,
                              total_trips=total_trips,
                              avg_earnings=avg_earnings,
                              earnings=earnings)
    
    return "Database connection error", 500

@app.route('/api/rate_driver', methods=['POST'])
def rate_driver():
    data = request.get_json()
    booking_id = data.get('booking_id')
    rating = int(data.get('rating'))
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("UPDATE Booking SET RideRating = %s WHERE BookingID = %s", (rating, booking_id))
        
        cursor.execute("""
            SELECT d.DriverID, AVG(b.RideRating) as avg_rating
            FROM Booking b
            JOIN Driver d ON b.DriverID = d.DriverID
            WHERE b.DriverID = (SELECT DriverID FROM Booking WHERE BookingID = %s) AND b.RideRating IS NOT NULL
            GROUP BY d.DriverID
        """, (booking_id,))
        result = cursor.fetchone()
        
        if result:
            avg_rating = round(result['avg_rating'], 2)
            cursor.execute("UPDATE Driver SET Rating = %s WHERE DriverID = %s", (avg_rating, result['DriverID']))
        
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'new_rating': avg_rating})
    
    return jsonify({'success': False, 'message': 'Database error'}), 500

# API endpoint to get earnings data for different time periods
@app.route('/api/driver/<int:driver_id>/earnings')
def get_driver_earnings(driver_id):
    period = request.args.get('period', 'week')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Define time filter based on period
        time_filter = ''
        if period == 'day':
            time_filter = 'AND DATE(b.BookingTime) = CURDATE()'
        elif period == 'week':
            time_filter = 'AND YEARWEEK(b.BookingTime) = YEARWEEK(NOW())'
        elif period == 'month':
            time_filter = 'AND YEAR(b.BookingTime) = YEAR(NOW()) AND MONTH(b.BookingTime) = MONTH(NOW())'
        elif period == 'year':
            time_filter = 'AND YEAR(b.BookingTime) = YEAR(NOW())'
        
        # Get earnings data for the period using the actual fare calculation
        query = f"""
            SELECT 
                COUNT(*) as TotalTrips,
                ROUND(SUM(f.Distance_KM * 10), 2) as TotalEarnings
            FROM Booking b
            JOIN Area src ON b.SourceID = src.AreaID
            JOIN Area dst ON b.DestID = dst.AreaID
            JOIN Fares f ON src.AreaName = f.Source AND dst.AreaName = f.Destination
            WHERE b.DriverID = %s AND b.Status = 'Completed' {time_filter}
        """
        
        cursor.execute(query, (driver_id,))
        stats = cursor.fetchone()
        
        # Get time series data for chart
        chart_data = []
        if period == 'day':
            # Hourly breakdown for today
            for hour in range(0, 24, 3):
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as TripCount,
                        ROUND(SUM(IFNULL(f.Distance_KM * 10, 0)), 2) as Earnings
                    FROM Booking b
                    LEFT JOIN Area src ON b.SourceID = src.AreaID
                    LEFT JOIN Area dst ON b.DestID = dst.AreaID
                    LEFT JOIN Fares f ON src.AreaName = f.Source AND dst.AreaName = f.Destination
                    WHERE b.DriverID = %s 
                    AND b.Status = 'Completed'
                    AND DATE(b.BookingTime) = CURDATE()
                    AND HOUR(b.BookingTime) >= %s
                    AND HOUR(b.BookingTime) < %s
                """, (driver_id, hour, hour + 3))
                
                result = cursor.fetchone()
                label = f"{hour}:00-{hour+2}:59"
                chart_data.append({
                    'label': label,
                    'value': float(result['Earnings'] or 0)
                })
        
        elif period == 'week':
            # Daily breakdown for current week
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            for i, day in enumerate(days):
                day_num = i + 1  # MySQL's DAYOFWEEK() is 1=Sunday, 7=Saturday, so we adjust
                if day_num == 7:
                    day_num = 0
                
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as TripCount,
                        ROUND(SUM(IFNULL(f.Distance_KM * 10, 0)), 2) as Earnings
                    FROM Booking b
                    LEFT JOIN Area src ON b.SourceID = src.AreaID
                    LEFT JOIN Area dst ON b.DestID = dst.AreaID
                    LEFT JOIN Fares f ON src.AreaName = f.Source AND dst.AreaName = f.Destination
                    WHERE b.DriverID = %s 
                    AND b.Status = 'Completed'
                    AND YEARWEEK(b.BookingTime) = YEARWEEK(NOW())
                    AND DAYOFWEEK(b.BookingTime) = %s
                """, (driver_id, day_num + 1))  # +1 because MySQL DAYOFWEEK starts at 1 (Sunday)
                
                result = cursor.fetchone()
                chart_data.append({
                    'label': day[:3],  # Abbreviated day name
                    'value': float(result['Earnings'] or 0)
                })
        
        elif period == 'month':
            # Weekly breakdown for current month
            for week in range(1, 5):
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as TripCount,
                        ROUND(SUM(IFNULL(f.Distance_KM * 10, 0)), 2) as Earnings
                    FROM Booking b
                    LEFT JOIN Area src ON b.SourceID = src.AreaID
                    LEFT JOIN Area dst ON b.DestID = dst.AreaID
                    LEFT JOIN Fares f ON src.AreaName = f.Source AND dst.AreaName = f.Destination
                    WHERE b.DriverID = %s 
                    AND b.Status = 'Completed'
                    AND YEAR(b.BookingTime) = YEAR(NOW())
                    AND MONTH(b.BookingTime) = MONTH(NOW())
                    AND FLOOR((DAY(b.BookingTime) - 1) / 7) + 1 = %s
                """, (driver_id, week))
                
                result = cursor.fetchone()
                chart_data.append({
                    'label': f'Week {week}',
                    'value': float(result['Earnings'] or 0)
                })
        
        elif period == 'year':
            # Monthly breakdown for current year
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            for i, month in enumerate(months):
                month_num = i + 1
                
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as TripCount,
                        ROUND(SUM(IFNULL(f.Distance_KM * 10, 0)), 2) as Earnings
                    FROM Booking b
                    LEFT JOIN Area src ON b.SourceID = src.AreaID
                    LEFT JOIN Area dst ON b.DestID = dst.AreaID
                    LEFT JOIN Fares f ON src.AreaName = f.Source AND dst.AreaName = f.Destination
                    WHERE b.DriverID = %s 
                    AND b.Status = 'Completed'
                    AND YEAR(b.BookingTime) = YEAR(NOW())
                    AND MONTH(b.BookingTime) = %s
                """, (driver_id, month_num))
                
                result = cursor.fetchone()
                chart_data.append({
                    'label': month,
                    'value': float(result['Earnings'] or 0)
                })
        
        cursor.close()
        conn.close()
        
        # Prepare response data
        total_trips = stats['TotalTrips'] if stats else 0
        total_earnings = float(stats['TotalEarnings'] if stats else 0)
        avg_earnings = round(total_earnings / total_trips, 2) if total_trips > 0 else 0
        
        return {
            'success': True,
            'period': period,
            'stats': {
                'total_trips': total_trips,
                'total_earnings': total_earnings,
                'avg_earnings': avg_earnings
            },
            'chart_data': chart_data
        }
    
    return {'success': False, 'message': 'Database error'}, 500

BANGALORE_CENTER = (12.9716, 77.5946)

# Geolocation API Key and URL
API_KEY = "AIzaSyADPG-sNlGo1lAzAtsTULqyWaFNEYgJ9kM"
GEOLOCATION_URL = "https://maps.googleapis.com/maps/api/geocode/json"

def fetch_area_scores():
    """Fetch latest area scores from MySQL"""
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("SELECT AreaName, AreaScore FROM area")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return data

def get_coordinates_from_address(address):
    """Fetch coordinates for a given address using Google Maps Geocoding API"""
    params = {
        'address': address,
        'key': API_KEY
    }
    response = requests.get(GEOLOCATION_URL, params=params)
    data = response.json()

    if data['status'] == 'OK':
        lat = data['results'][0]['geometry']['location']['lat']
        lon = data['results'][0]['geometry']['location']['lng']
        return lat, lon
    else:
        print(f"Error fetching coordinates for {address}: {data['status']}")
        
        # Retry with more specific queries
        alternative_addresses = [
            f"{address}, Bangalore",
            f"{address}, Bengaluru",
            f"{address}, India"
        ]
        
        for alt_address in alternative_addresses:
            params['address'] = alt_address
            response = requests.get(GEOLOCATION_URL, params=params)
            data = response.json()
            if data['status'] == 'OK':
                lat = data['results'][0]['geometry']['location']['lat']
                lon = data['results'][0]['geometry']['location']['lng']
                return lat, lon
        
        return None  # Return None if no valid results are found


def generate_heatmap():
    """Generate the Folium Heatmap with updated scores"""
    area_data = fetch_area_scores()
    df = pd.DataFrame(area_data, columns=["AreaName", "AreaScore"])

    # Initialize an empty dictionary for the zone coordinates
    zone_coords = {}

    # Fetch coordinates for each area in the database
    for area in df["AreaName"]:
        if area not in zone_coords:
            coords = get_coordinates_from_address(area)
            if coords:
                zone_coords[area] = coords

    # Create a new Folium Map
    folium_map = folium.Map(location=BANGALORE_CENTER, zoom_start=12)

    # Prepare Heatmap Data (Lat, Lon, AreaScore)
    heat_data = []
    for area, score in zip(df["AreaName"], df["AreaScore"]):
        if area in zone_coords:
            lat, lon = zone_coords[area]
            heat_data.append([lat, lon, float(score)])

    # Add HeatMap Layer
    HeatMap(heat_data, min_opacity=0.3, max_opacity=0.9, radius=40).add_to(folium_map)

    # Save the map
    folium_map.save("templates/heatmap.html")

@app.route('/driver/heatmap')
def heatmap():
    """Render Heatmap Page"""
    generate_heatmap()
    return render_template("heatmap.html")

def background_update():
    """Continuously update the heatmap and notify clients"""
    while True:
        generate_heatmap()  # Regenerate heatmap
        socketio.emit('update_heatmap', {'message': 'Heatmap Updated!'})
        time.sleep(10)  # Update every 10 seconds
        
@app.route('/driver/lucky')
def driver_lucky():
    driver_id = request.args.get("driver_id")

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)

        # Get driver's current area
        cursor.execute("""
            SELECT a.AreaName 
            FROM Driver d
            JOIN Area a ON d.ResidenceID = a.AreaID
            WHERE d.DriverID = %s
        """, (driver_id,))
        driver_data = cursor.fetchone()

        if not driver_data:
            cursor.close()
            conn.close()
            return jsonify({"message": "Driver not found."}), 404

        driver_area = driver_data['AreaName']

        # Get highest demand areas
        demand_data = get_highest_demand_nearby_areas(db_config)

        if driver_area in demand_data:
            recommended_area = demand_data[driver_area]['AreaName']
            status = "Current" if driver_area == recommended_area else "Move To"
            
            if status == "Current":
                message = "🎉 Your day seems to be lucky! Stay where you are for more rides."
            else:
                message = f"🚀 Make your day better by moving to {recommended_area}."

            cursor.close()
            conn.close()
            return jsonify({"message": message})

    return jsonify({"message": "Could not retrieve location data."}), 500



if __name__ == '__main__':
    app.run(debug=True)
    # generate_heatmap()
    socketio.start_background_task(background_update)  # Start background thread
    socketio.run(app, debug=True, port=5000)
