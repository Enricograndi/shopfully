import os
import pandas as pd
from datetime import datetime, timedelta
from pyowm.utils import formatting
from utilities import utilities as ut
import ast

def initialize_dates(now):
    """Initialize start and end times based on current date."""
    start_date = (now - timedelta(days=10)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
    return formatting.to_UNIXtime(start_date), formatting.to_UNIXtime(end_time)

def fetch_weather_data(city_data, api_key, package_path, data_folder):
    """Fetch, normalize, and save the weather data."""
    file_path = f"{data_folder}/{city_data['city']}_{city_data['start_time']}_{city_data['end_time']}.csv"

    if not os.path.exists(file_path):
        weather_data = ut.get_historical_weather_hourly(
            api_key,
            city=city_data['city'],
            lat=city_data['lat'],
            lon=city_data['lng'],
            start_date=city_data['start_time'],
            end_date=city_data['end_time']
        )
        ut.save_raw_data_to_csv(weather_data, file_name=file_path)

    weather_data = pd.read_csv(file_path)
    normalized_data = ut.normalize_raw_data(weather_data)
    ut.save_df_to_db(normalized_data)

def main():
    # Configuration and initialization
    config = ut.read_settings()
    data_folder = config["data_folder"]
    package_path = config["package_path"]
    api_key = config["api_key"]
    cities_csv = config["cities_csv"]
    cities = ast.literal_eval(config['cities'])

    ut.initialize_database()
    
    now = datetime.now()
    start_date_unix, end_time_unix = initialize_dates(now)

    cities_df = pd.DataFrame(ut.retrieve_last_date_for_each_city(), columns=['city', 'lat', 'lng', 'start_time'])
    if cities_df.empty:
        cities_df = pd.read_csv(cities_csv)
        cities_df = cities_df[cities_df["city"].isin(cities)][['city', 'lat', 'lng']]
        cities_df["start_time"] = start_date_unix
    
    cities_df["end_time"] = end_time_unix

    # Identify missing cities and fetch their data if needed
    missing_cities = set(cities) - set(cities_df['city'])
    if missing_cities:
        all_cities_df = pd.read_csv(cities_csv)
        missing_city_data = all_cities_df[all_cities_df["city"].isin(missing_cities)]
        missing_city_data["start_time"] = start_date_unix
        missing_city_data["end_time"] = end_time_unix
        cities_df = pd.concat([cities_df, missing_city_data], ignore_index=True)

    # Filter out rows with same start and end times
    cities_df = cities_df[cities_df["start_time"].astype(int) != end_time_unix-3599]

    # For each city, fetch and save weather data
    for _, city_data in cities_df.iterrows():
        fetch_weather_data(city_data, api_key, package_path, data_folder)

    print("New Data downloaded")

if __name__ == "__main__":
    main()
