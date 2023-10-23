# Importing necessary libraries
import os
import requests
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from ast import literal_eval
import time
import ast

# Function to read settings from a file
def read_settings(filename="data/settings.txt"):
    settings = {}
    with open(filename, "r") as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()  # Remove any whitespace
            if line and not line.startswith("#"):  # Check it's not a comment or empty line
                key, value = line.split("=")
                settings[key] = value
    return settings

# Loading configurations
config = read_settings()
data_folder = config["data_folder"]
package_path = config["package_path"]
api_key = config["api_key"]
raw_data_filename = config["raw_data_filename"]
db_name = config["db_name"]
cities_csv = config["cities_csv"]
cities = ast.literal_eval(config['cities'])

# Function to initialize the SQLite database and its tables
def initialize_database():
    """Initialize the SQLite database and create tables if they don't exist."""
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()

        # Creating Cities table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Cities(
         city_id INTEGER PRIMARY KEY AUTOINCREMENT,
         city TEXT UNIQUE,
         lat DECIMAL(9,6),
         lon DECIMAL(9,6),
         timezone TEXT,
         timezone_offset INT
        )
        ''')

        # Creating WeatherHourly table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS WeatherHourly
        (
         weather_id INTEGER PRIMARY KEY AUTOINCREMENT,
         city_id INT,
         dt BIGINT,
         temp DECIMAL(5,2),
         weather_description TEXT,
         wind_speed DECIMAL(5,2),
         FOREIGN KEY (city_id) REFERENCES Cities(city_id)
        );
        ''')

        conn.commit()

    return "DB initialized or already exists"

# Function to insert a new city or retrieve its ID if it already exists
def get_or_insert_city(city_name, lat, lon, timezone):
    """Get city_id if city exists. If not, insert new city and return its city_id."""
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()

        # Check if city exists
        cursor.execute('SELECT city_id FROM Cities WHERE city=?', (city_name,))
        existing_city = cursor.fetchone()

        # Return city_id if city exists
        if existing_city:
            return existing_city[0]
        # Insert new city and return its city_id
        else:
            cursor.execute('INSERT INTO Cities(city, lat, lon, timezone) VALUES (?, ?, ?, ?)',
                           (city_name, lat, lon, timezone))
            return cursor.lastrowid

# Function to insert hourly weather data for a city
def insert_weather_hourly(city_id, row):
    """Insert data into the WeatherHourly table if it doesn't exist."""
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()

        # Check if weather data for given city and date-time exists
        cursor.execute('SELECT weather_id FROM WeatherHourly WHERE city_id=? AND dt=?',
                       (city_id, row['dt']))
        existing_weather = cursor.fetchone()

        # Insert weather data if not existing
        if not existing_weather:
            cursor.execute('''
            INSERT INTO WeatherHourly(city_id, dt, temp, weather_description, wind_speed) 
            VALUES (?, ?, ?, ?, ?)
            ''', (
                  city_id, 
                  row['dt'],
                  row['temp'],
                  row['description'], 
                  row['wind_speed'],
                  ))
    return print("Weather data inserted or already exists")

# Function to fetch historical hourly weather data for a given city
def get_historical_weather_hourly(api_key, city, lat, lon, start_date, end_date, units="metric"):
    """Fetch historical hourly weather data from OWM."""
    base_url = "https://api.openweathermap.org/data/3.0/onecall/timemachine"
    hourly_data = []

    current_epoch = int(start_date)
    while int(current_epoch) <= int(end_date):
        url = f"{base_url}?lat={lat}&lon={lon}&dt={current_epoch}&appid={api_key}&units={units}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()

            hourly_data.append({
                **response.json(),
                "City": city
            })
            print(f'Data Downloaded for {city} and time {current_epoch}: {hourly_data[-1]}')

        # Handle potential HTTP or SSL errors
        except requests.exceptions.HTTPError as http_err:
            print(f'HTTP error occurred for {city} and time {current_epoch}: {http_err}')
            time.sleep(10)
        except requests.exceptions.SSLError as ssl_err:
            print(f'SSL error occurred for {city} and time {current_epoch}: {ssl_err}')
            time.sleep(10)
            continue
        except Exception as err:
            print(f'Error occurred for {city} and time {current_epoch}: {err}')
            time.sleep(10)
            current_epoch += 3600
            continue

        current_epoch += 3600

    return hourly_data

# Function to save fetched weather data to a CSV file
def save_raw_data_to_csv(weather_data, file_name=raw_data_filename):
    """Append weather data to CSV, considering duplicates, without loading the entire file into memory."""
    new_df = pd.DataFrame(weather_data)
    
    # Check if file exists
    if not os.path.exists(file_name):
        new_df.to_csv(file_name, index=False)        
    
    return print(f"Data saved to {file_name}")

# Function to normalize and structure raw weather data
def normalize_raw_data(json):
    """Normalize and structure raw weather data."""
    df = pd.DataFrame(json)
    df['data'] = df['data'].apply(literal_eval)
    normalized_data = pd.json_normalize(df['data'].explode().reset_index(drop=True))
    result_df = pd.concat([df.drop(columns='data'), normalized_data], axis=1)
    normalized_weather = pd.json_normalize(result_df['weather'].explode().groupby(level=0).first().reset_index(drop=True))
    result_df = pd.concat([result_df.drop(columns='weather'), normalized_weather], axis=1)

    return result_df

# Function to save normalized data to the database
def save_df_to_db(df):
    for _, row in df.iterrows():
        city_id = get_or_insert_city(row['City'], row['lat'], row['lon'], row['timezone'])
        insert_weather_hourly(city_id, row)
    
    return "Data saved to database"

def retrieve_last_date_for_each_city():
    """Get the latest weather data date for each city."""
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT Cities.city, Cities.lat, Cities.lon, MAX(WeatherHourly.dt) as last_date
        FROM Cities
        JOIN WeatherHourly ON Cities.city_id = WeatherHourly.city_id
        GROUP BY Cities.city, Cities.lat, Cities.lon
        ORDER BY Cities.city;
        ''')
        results = cursor.fetchall()

    return results
