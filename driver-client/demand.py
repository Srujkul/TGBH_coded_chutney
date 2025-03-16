import mysql.connector

def get_highest_demand_nearby_areas(db_config):
    """
    For each area, find the area with highest demand score within 7km.
    If no higher demand area exists within that radius, return the area itself.
    
    Parameters:
    db_config (dict): Database connection parameters
    
    Returns:
    dict: A dictionary mapping each area name to its highest demand nearby area
    """
    # Connect to the database
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        print("Connected to database successfully")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None
    
    try:
        # Get all areas from the database
        cursor.execute("SELECT AreaID, AreaName, AreaScore FROM Area ORDER BY AreaID")
        areas = cursor.fetchall()
        
        # Create a lookup dictionary for area name to ID and score
        area_lookup = {}
        for area in areas:
            area_lookup[area['AreaName']] = {
                'AreaID': area['AreaID'], 
                'AreaScore': area['AreaScore']
            }
        
        # Get distance data from the Fares table
        cursor.execute("SELECT Source, Destination, Distance_KM FROM Fares")
        distances = cursor.fetchall()
        
        # Create a distance lookup dictionary for quick access
        distance_lookup = {}
        for d in distances:
            source = d['Source']
            destination = d['Destination']
            distance = d['Distance_KM']
            
            # Skip if area names not in area_lookup (might be different naming)
            if source not in area_lookup or destination not in area_lookup:
                continue
                
            # Store distances both ways for easier lookup
            if source not in distance_lookup:
                distance_lookup[source] = {}
            if destination not in distance_lookup:
                distance_lookup[destination] = {}
                
            distance_lookup[source][destination] = distance
            # Assuming symmetrical distances (if not already in the table both ways)
            if destination not in distance_lookup.get(source, {}):
                distance_lookup[destination][source] = distance
        
        # Create results dictionary
        results_dict = {}
        
        # For each area, find the highest demand area within
        for area in areas:
            area_id = area['AreaID']
            area_name = area['AreaName']
            area_score = area['AreaScore']
            
            # Initialize with the area itself (default if no better area is found)
            highest_demand_area = {
                'AreaID': area_id,
                'AreaName': area_name,
                'AreaScore': area_score
            }
            
            # Check if this area has distance data
            if area_name in distance_lookup:
                # Find areas within 7km that have higher demand
                for other_area_name, distance in distance_lookup[area_name].items():
                    # Skip if no distance data available or not within 7km
                    if distance > 7:
                        continue
                    
                    other_area_info = area_lookup.get(other_area_name)
                    if not other_area_info:
                        continue
                        
                    # Check if has higher demand
                    if other_area_info['AreaScore'] > highest_demand_area['AreaScore']:
                        highest_demand_area = {
                            'AreaID': other_area_info['AreaID'],
                            'AreaName': other_area_name,
                            'AreaScore': other_area_info['AreaScore']
                        }
            
            # Add to results dictionary
            results_dict[area_name] = {
                'AreaID': highest_demand_area['AreaID'],
                'AreaName': highest_demand_area['AreaName'],
                'AreaScore': highest_demand_area['AreaScore'],
                'IsSameArea': highest_demand_area['AreaID'] == area_id
            }
        
        return results_dict
        
    except Exception as e:
        print(f"Error executing query: {e}")
        return None
    finally:
        cursor.close()
        conn.close()
        print("Database connection closed")



if __name__ == '__main__':
    # Database configuration
    db_config = {
        'host': '172.25.160.1',  # or your actual host IP
        'user': 'root',
        'password': 'thanishkn11',
        'database': 'CodedChutney'
    }
    
    # Call the function
    results_dict = get_highest_demand_nearby_areas(db_config)
    print(results_dict,'\n\n')
    # Print the results in a readable format
    if results_dict:
        print("\nArea Recommendations for Higher Demand:\n")
        print("{:<20} {:<20} {:<10} {:<10}".format(
            "Area", "Recommendation", "Score", "Status"))
        print("-" * 60)
        
        for area_name, info in results_dict.items():
            status = "Current" if info['IsSameArea'] else "Move to"
            print("{:<20} {:<20} {:<10.1f} {:<10}".format(
                area_name, 
                info['AreaName'], 
                info['AreaScore'],
                status
            ))
    else:
        print("Failed to retrieve area recommendations.")