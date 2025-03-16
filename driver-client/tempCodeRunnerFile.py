from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = "nammayatrisecretkey123"

# Database connection function
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='CodedChutney',
            user='root',  # Replace with your MySQL username
            password='Abhi301103#'  # Replace with your MySQL password
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
@app.route('/api/estimate_fare', methods=['POST'])
def estimate_fare():
    data = request.get_json()
    source = data.get('source')
    destination = data.get('destination')
    service_type = data.get('service_type')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Get area IDs for source and destination
        cursor.execute("SELECT AreaID, AreaScore FROM Area WHERE AreaName = %s", (source,))
        source_data = cursor.fetchone()
        
        cursor.execute("SELECT AreaID, AreaScore FROM Area WHERE AreaName = %s", (destination,))
        dest_data = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if source_data and dest_data:
            # Simple fare calculation based on area scores and service type
            base_fare = 30
            if service_type == 'auto':
                multiplier = 1.0
            elif service_type == 'bike':
                multiplier = 0.8
            else:  # car
                multiplier = 1.5
                
            # Higher area scores result in higher fares (simulating demand-based pricing)
            demand_factor = (source_data['AreaScore'] + dest_data['AreaScore']) / 10
            fare = round(base_fare * multiplier * demand_factor, 2)
            
            return {'fare': fare}
    
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
        
        # Get earnings data (simplified for this example)
        # In a real app, you would have transactions or payment tables
        cursor.execute("""
            SELECT 
                b.BookingID, 
                b.BookingTime, 
                b.Status,
                p.Name as PassengerName,
                src.AreaName as Source,
                dst.AreaName as Destination,
                ROUND((src.AreaScore + dst.AreaScore) * 15, 2) as EstimatedAmount
            FROM Booking b
            JOIN Passenger p ON b.PassengerID = p.PassengerID
            JOIN Area src ON b.SourceID = src.AreaID
            JOIN Area dst ON b.DestID = dst.AreaID
            WHERE b.DriverID = %s AND b.Status = 'Completed'
            ORDER BY b.BookingTime DESC
            LIMIT 10
        """, (driver_id,))
        
        earnings_rows = cursor.fetchall()
        
        # Calculate statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as TotalTrips,
                ROUND(SUM((src.AreaScore + dst.AreaScore) * 15), 2) as TotalEarnings
            FROM Booking b
            JOIN Area src ON b.SourceID = src.AreaID
            JOIN Area dst ON b.DestID = dst.AreaID
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
                'amount': row['EstimatedAmount']
            })
        
        return render_template('driver_earnings.html', 
                              driver_id=driver_id,
                              total_earnings=total_earnings,
                              total_trips=total_trips,
                              avg_earnings=avg_earnings,
                              earnings=earnings)
    
    return "Database connection error", 500

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
        
        # Get earnings data for the period
        query = f"""
            SELECT 
                COUNT(*) as TotalTrips,
                ROUND(SUM((src.AreaScore + dst.AreaScore) * 15), 2) as TotalEarnings
            FROM Booking b
            JOIN Area src ON b.SourceID = src.AreaID
            JOIN Area dst ON b.DestID = dst.AreaID
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
                        ROUND(SUM(IFNULL((src.AreaScore + dst.AreaScore) * 15, 0)), 2) as Earnings
                    FROM Booking b
                    LEFT JOIN Area src ON b.SourceID = src.AreaID
                    LEFT JOIN Area dst ON b.DestID = dst.AreaID
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
                        ROUND(SUM(IFNULL((src.AreaScore + dst.AreaScore) * 15, 0)), 2) as Earnings
                    FROM Booking b
                    LEFT JOIN Area src ON b.SourceID = src.AreaID
                    LEFT JOIN Area dst ON b.DestID = dst.AreaID
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
                        ROUND(SUM(IFNULL((src.AreaScore + dst.AreaScore) * 15, 0)), 2) as Earnings
                    FROM Booking b
                    LEFT JOIN Area src ON b.SourceID = src.AreaID
                    LEFT JOIN Area dst ON b.DestID = dst.AreaID
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
                        ROUND(SUM(IFNULL((src.AreaScore + dst.AreaScore) * 15, 0)), 2) as Earnings
                    FROM Booking b
                    LEFT JOIN Area src ON b.SourceID = src.AreaID
                    LEFT JOIN Area dst ON b.DestID = dst.AreaID
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


if __name__ == '__main__':
    app.run(debug=True)
