from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, FloatType, IntegerType
from pyspark.sql.functions import col, desc
import mysql.connector
import json

# Initialize Spark Session (keeps running for batch processing)
spark = SparkSession.builder \
    .appName("RideRequestsBatchProcessing") \
    .master("local[*]") \
    .config("spark.hadoop.fs.defaultFS", "file:///") \
    .getOrCreate()

print("Spark Batch Processing Started...")

# Load batch messages from file
with open("batch_data.json", "r") as f:
    batch_messages = json.load(f)

if not batch_messages:
    print("No new messages. Skipping batch processing.")
    spark.stop()
    exit()

# Define schema for ride requests
ride_schema = StructType([
    StructField("RequestID", IntegerType(), True),
    StructField("PassengerID", IntegerType(), True),
    StructField("Source", StringType(), True),
    StructField("Destination", StringType(), True),
    StructField("RequestTimestamp", StringType(), True)
])

# Create DataFrame from batch messages
ride_requests_df = spark.createDataFrame(
    [(msg["RequestID"], msg["PassengerID"], msg["Source"], msg["Destination"], msg["RequestTimestamp"]) for msg in batch_messages],
    ride_schema
)

# Connect to MySQL and fetch fares & area data
conn = mysql.connector.connect(
    host="172.25.160.1",
    user="root",
    password="thanishkn11",
    database="CodedChutney"
)
cursor = conn.cursor()

cursor.execute("SELECT Source, Destination, Distance_KM, Fare_Rupees FROM Fares")
fares_rows = cursor.fetchall()

cursor.execute("SELECT AreaID, AreaName, AreaScore FROM Area")
area_rows = cursor.fetchall()

cursor.close()
conn.close()

# Convert data for PySpark
fares_rows = [(src, dest, float(dist), float(fare)) for src, dest, dist, fare in fares_rows]
area_rows = [(int(aid), name, float(score)) for aid, name, score in area_rows]

# Define schemas
fares_schema = StructType([
    StructField("Source", StringType(), True),
    StructField("Destination", StringType(), True),
    StructField("Distance_KM", FloatType(), True),
    StructField("Fare_Rupees", FloatType(), True)
])

area_schema = StructType([
    StructField("AreaID", IntegerType(), True),
    StructField("AreaName", StringType(), True),
    StructField("AreaScore", FloatType(), True)
])

# Create DataFrames
fares_df = spark.createDataFrame(fares_rows, schema=fares_schema)
area_df = spark.createDataFrame(area_rows, schema=area_schema)

# Register tables for Spark SQL
ride_requests_df.createOrReplaceTempView("ride_requests")
area_df.createOrReplaceTempView("area")

# Compute demand per area
ride_counts_df = spark.sql("""
    SELECT Source AS AreaName, COUNT(*) AS RideCount
    FROM ride_requests
    GROUP BY Source
    ORDER BY RideCount DESC
""")

# Join area demand with area info
area_demand_df = area_df.join(ride_counts_df, "AreaName", "left").fillna({'RideCount': 0})

# Find highest-demand area
highest_demand_area = area_demand_df.orderBy(desc("RideCount")).first()[0]

# Find closest higher-demand area within 7 km
closest_high_demand_df = area_demand_df.alias("a1").join(
    fares_df.alias("f"), col("a1.AreaName") == col("f.Source")
).join(
    area_demand_df.alias("a2"), col("f.Destination") == col("a2.AreaName")
).filter(
    (col("f.Distance_KM") <= 7) & (col("a2.RideCount") > col("a1.RideCount"))
).select(
    col("a1.AreaName").alias("Area"),
    col("a2.AreaName").alias("ClosestHighDemandArea")
)

# If no close higher-demand area, assign highest demand area
final_df = area_demand_df.alias("a").join(
    closest_high_demand_df.alias("c"), col("a.AreaName") == col("c.Area"), "left"
).fillna({"ClosestHighDemandArea": highest_demand_area})

# Compute updated Area Scores
updated_scores_df = final_df.select(
    col("AreaID"),
    ((col("RideCount") + 1) / (col("AreaScore") + 1)).alias("UpdatedScore")
)

# Convert to dictionary
updated_scores = {row["AreaID"]: row["UpdatedScore"] for row in updated_scores_df.collect()}
print("Updated Scores:", updated_scores)

# Update scores in MySQL
conn = mysql.connector.connect(
    host="172.25.160.1",
    user="root",
    password="thanishkn11",
    database="CodedChutney"
)
cursor = conn.cursor()

for area_id, new_score in updated_scores.items():
    cursor.execute("UPDATE Area SET AreaScore = %s WHERE AreaID = %s", (new_score, area_id))

conn.commit()
cursor.close()
conn.close()

print("Area scores updated successfully.")

# Stop Spark Session
spark.stop()
