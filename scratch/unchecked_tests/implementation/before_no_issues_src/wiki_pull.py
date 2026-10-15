# wikipedia needed for company selection and sector info
import requests
# abbreviation
import pandas as pd
# to convert html string to file-like object
import io

# returns wikipedia dataframe with S&P 500 company ticker, name, and sector
def get_wiki_dataframe():
    wiki_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    # header to get past 403 error
    # header adds meta data to the request (not bot traffic)
    # non-browser like strings work for wikipedia
    headers = {"User-Agent": "plsgivemedata"}

    wiki_pull = requests.get(wiki_url, headers=headers)

    html_string = wiki_pull.text

    # newer versions of pandas requires file-like object to read html tables
    html_file = io.StringIO(html_string)

    # pd.read_html returns a list of dataframes
    wiki_dataframe = pd.read_html(html_file)[0]

    # double brackets for dataframe, single brackets for series
    filtered_dataframe = wiki_dataframe[["Symbol", "Security", "GICS Sector", "CIK"]]

    # replaces periods in ticker to dashes
    # regex=False treat special characters as literal strings
    filtered_dataframe["Symbol"] = filtered_dataframe["Symbol"].str.replace(".", "-", regex=False)

    return filtered_dataframe

# no if __name__ == "__main__" block because module requires no further testing
