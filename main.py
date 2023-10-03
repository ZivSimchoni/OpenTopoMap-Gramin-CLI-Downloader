import argparse
import concurrent.futures
import os

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

TARGET_BASE_URL = "https://garmin.opentopomap.org/"

def parse_arguments():
    parser = argparse.ArgumentParser(description='Download TopoMaps zips from https://garmin.opentopomap.org/.')
    parser.add_argument('-c', '--country', nargs='+', default=[], help='List of maps to download (optional), use the number of the country/area')
    return parser.parse_args()


def getDefultDownloadFolder():
    # Get the user's home directory
    home_directory = os.path.expanduser("~")

    # Join the home directory with the 'Downloads' folder
    download_folder = os.path.join(home_directory, 'Downloads/OTM-Garmin')

    # Check if the folder exists, if not, create it
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    return download_folder


# def downloadZip(url):
#     try:
#         downloadFolder = getDefultDownloadFolder()
#         response = requests.get(url, stream=True)
#         file_name = os.path.join(downloadFolder, os.path.basename(url))
#         with open(file_name, 'wb') as file:
#             for chunk in response.iter_content(chunk_size=8192):
#                 file.write(chunk)
#         return file_name
#     except Exception as e:
#         return str(e)

def downloadZip(url):
    try:
        downloadFolder = getDefultDownloadFolder()  # Set the download folder here
        response = requests.get(url, stream=True)
        file_name = os.path.join(downloadFolder, os.path.basename(url))
        
        # Get the total file size from the response headers
        total_size = int(response.headers.get('content-length', 0))
        
        # Create a tqdm progress bar
        with tqdm(total=total_size, unit='B', unit_scale=True, desc=os.path.basename(url), ncols=100) as bar:
            with open(file_name, 'wb') as file:
                for chunk in response.iter_content(chunk_size=1048576):  # 1MB chunk
                    # Update the progress bar with the size of the downloaded chunk
                    bar.update(len(chunk))
                    file.write(chunk)
        
        return file_name

    except Exception as e:
        return str(e)



def getCountriesListFromHtmlTable():
    try:
        # Make an HTTP GET request to the target URL
        response = requests.get(TARGET_BASE_URL)
        response.raise_for_status()  # Raise an HTTPError for bad requests

        # Parse the HTML content of the response
        soup = BeautifulSoup(response.content, 'html.parser')

        countries = []
        country_number = 1  # Initialize the country number

        # Find all rows with class 'country'
        country_rows = soup.find_all('tr', class_='country')

        for row in country_rows:
            # Extract country name and continent from the row
            country_name = row.find('td').text
            continent = row['continent']
            country_id = row['id']

            # Append the extracted data to the countries list along with the country number
            countries.append({'number': country_number, 'id': country_id, 'name': country_name, 'continent': continent})

            # Increment the country number for the next country
            country_number += 1
        return countries

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


def isCountryNameInList(countryName, countriesList):
    return any(country['name'] == countryName for country in countriesList)


def getUserSelectionOfCountries(countries_list):
    selected_countries = []
    print("Available Maps:")
    for idx, country in enumerate(countries_list, start=1):
        print(f"{str(idx).zfill(3)}. {country['name']}")
    while True:
        try:
            selected_index = int(input("Enter the number of the Maps you want to select (0 to finish): "))
            if selected_index == 0:
                break
            elif 1 <= selected_index <= len(countries_list):
                selected_country = countries_list[selected_index - 1]
                selected_countries.append(selected_country)
                print(f"Selected: {selected_country['name']}")
            else:
                print("Invalid input. Please enter a valid number.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    return selected_countries


def makeUrl(userSelected):
    # https://garmin.opentopomap.org/<Continent>/<Area>/otm-<Area>.zip
    # https://garmin.opentopomap.org/<Continent>/<Area>/otm-<Area>-contours.zip
    # https://garmin.opentopomap.org/europe/<Area>/otm-<Area>-basecamp.zip
    otmDownloadList = []
    for country in userSelected:
        otmDownloadList.append(f"https://garmin.opentopomap.org/{country['continent']}/{country['id']}/otm-{country['id']}.zip")
        otmDownloadList.append(f"https://garmin.opentopomap.org/{country['continent']}/{country['id']}/otm-{country['id']}-contours.zip")
        if country['continent'] == "europe":
            basecamp = input(f"Would you like a BaseCamp map for {country['name']}? Enter: 0 for no, else for yes.")
            if basecamp != '0':
                otmDownloadList.append(f"https://garmin.opentopomap.org/europe/{country['id']}/otm-{country['id']}-basecamp.zip")
    
    return otmDownloadList

def main():
    args = parse_arguments()
    
    countriesListOnRemote = getCountriesListFromHtmlTable()
    
    if not args.country:
        userSelected = getUserSelectionOfCountries(countriesListOnRemote)
    else:
        if args.country:
            userCountries = [country.lower() for country in args.name] # make all the args lower case same as the id
            userSelected = [countriesListOnRemote["nameOfCountry"] for nameOfCountry in userCountries if isCountryNameInList(nameOfCountry,countriesListOnRemote)]
        if not userSelected: 
            print("cannot parse your input args, please pick from this:")
            userSelected = getUserSelectionOfCountries(countriesListOnRemote)

    urls_to_download = makeUrl(userSelected)
    print("Starts downloading, please wait")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(downloadZip, urls_to_download))

    for result in results:
        print(f'Downloaded: {result}')


if __name__ == '__main__':
    main()
