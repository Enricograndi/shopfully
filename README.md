# Weather Data Fetcher
This script fetches, normalizes, and saves historical hourly weather data for specified cities.

## Description
The script retrieves weather data from the last 10 days up to yesterday. If the data is already available locally, it will read it; otherwise, it will fetch the data from the source.

The data is then normalized and saved to a database. The script manages both new and previously fetched cities and ensures that the data is fetched only once.

## Dependencies
- os
- pandas
- DateTime
- pyowm

  You can install the requirments txt:

  pip install -r requirements.txt


## Setup
Ensure that you have the required dependencies installed.

Place your configuration in the utilities package. Configuration should include:

- data_folder: The directory where CSV files will be saved.
- package_path: The root directory of this script.
- api_key: Your API key for fetching weather data.
- cities_csv: A CSV file that contains city names and their respective latitude and longitude values.
- cities: A list of cities for which you want to fetch the data.

Make sure your database settings in the utilities package are correct.

## Usage
Run the script with:

cd  [where your donwnload the folder]/download_weather_data
python main.py
Once executed, the script will provide a message when new data has been downloaded.

## Functions
- You can find the explanation on the notebook
  
## Contribution
Feel free to fork and submit pull requests. For major changes, please open an issue first to discuss what you'd like to change.

