import concurrent.futures
import os
from functools import partial

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

TARGET_BASE_URL = "https://garmin.opentopomap.org/"


def getDefaultDownloadFolder():
    """
    The function gets the user's home directory and joins it with the 'Downloads' folder.
    If the folder does not exist, it creates it.

    Returns:
    download_folder (str): The default download folder for OpenTopoMap Garmin CLI Downloader.
    """
    home_directory = os.path.expanduser("~")
    download_folder = os.path.join(home_directory, "Downloads/OTM-Garmin")
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
    return download_folder


def downloadWithProgress(url):
    """
    Downloads a file from the given URL and displays a progress bar.

    Args:
        url (str): The URL of the file to download.

    Returns:
        str: The path to the downloaded file.
    """
    downloadFolder = getDefaultDownloadFolder()
    response = requests.head(url)
    total_size = int(response.headers.get("content-length", 0))
    bar = tqdm(
        total=total_size,
        unit="B",
        unit_scale=True,
        desc=os.path.basename(url),
        ncols=100,
    )
    return downloadZip(url, downloadFolder, bar)


def downloadZip(url, downloadFolder, bar):
    try:
        response = requests.get(url, stream=True)
        file_name = os.path.join(downloadFolder, os.path.basename(url))

        with open(file_name, "wb") as file:
            for chunk in response.iter_content(
                chunk_size=1048576
            ):  # 1MB chunk = 1048576
                bar.update(len(chunk))
                file.write(chunk)

        return file_name, bar

    except Exception as e:
        return str(e), bar


import requests
from bs4 import BeautifulSoup


def getCountriesListFromHtmlTable():
    """
    Extracts a list of countries from an HTML table on a website.

    Returns:
    A list of dictionaries, where each dictionary represents a country and contains the following keys:
    - number: The number of the country in the list.
    - id: The ID of the country.
    - name: The name of the country.
    - continent: The continent that the country belongs to.
    """
    try:
        # Make an HTTP GET request to the target URL
        response = requests.get(TARGET_BASE_URL)
        response.raise_for_status()  # Raise an HTTPError for bad requests

        # Parse the HTML content of the response
        soup = BeautifulSoup(response.content, "html.parser")

        countries = []
        country_number = 1  # Initialize the country number

        # Find all rows with class 'country'
        country_rows = soup.find_all("tr", class_="country")

        for row in country_rows:
            # Extract country name and continent from the row
            country_name = row.find("td").text
            continent = row["continent"]
            country_id = row["id"]

            # Append the extracted data to the countries list along with the country number
            countries.append(
                {
                    "number": country_number,
                    "id": country_id,
                    "name": country_name,
                    "continent": continent,
                }
            )

            # Increment the country number for the next country
            country_number += 1
        return countries

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


def getUserSelectionOfCountries():
    """
    Allows the user to select multiple countries from the available list.

    Returns:
        list: A list of dictionaries, each containing information about a selected country.
              Each dictionary includes keys: 'id', 'name', 'continent' representing the country's ID, name, and continent.
    """
    countriesList = getCountriesListFromHtmlTable()
    selected_countries = []
    print("Available Maps:")
    for idx, country in enumerate(countriesList, start=1):
        print(f"{str(idx).zfill(3)}. {country['name']}")
    while True:
        try:
            selected_index = int(
                input("Enter the number of the Maps you want to select (0 to finish): ")
            )
            if selected_index == 0:
                break
            elif 1 <= selected_index <= len(countriesList):
                selected_country = countriesList[selected_index - 1]
                selected_countries.append(selected_country)
                print(f"Selected: {selected_country['name']}")
            else:
                print("Invalid input. Please enter a valid number.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    return selected_countries


def makeUrl(userSelected):
    """
    This function takes a list of dictionaries containing information about selected countries and returns a list of URLs for downloading OpenTopoMap files.

    Args:
    - userSelected: a list of dictionaries containing information about selected countries.

    Returns:
    - A list of strings representing URLs for downloading OpenTopoMap files.
    """
    otmDownloadList = []
    for country in userSelected:
        otmDownloadList.append(
            f"{TARGET_BASE_URL}{country['continent']}/{country['id']}/otm-{country['id']}.zip"
        )
        otmDownloadList.append(
            f"{TARGET_BASE_URL}{country['continent']}/{country['id']}/otm-{country['id']}-contours.zip"
        )
        if country["continent"] == "europe":
            basecamp = input(
                f"Would you like a BaseCamp map for {country['name']}? Enter: 0 for no, else for yes."
            )
            if basecamp != "0":
                otmDownloadList.append(
                    f"{TARGET_BASE_URL}europe/{country['id']}/otm-{country['id']}-basecamp.zip"
                )

    return otmDownloadList


def main():
    urls_to_download = makeUrl(getUserSelectionOfCountries())
    print("Starts downloading, please wait")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(partial(downloadWithProgress), urls_to_download))

    print(f"\nDownloaded: {len(results)}/{len(urls_to_download)}")


if __name__ == "__main__":
    main()
