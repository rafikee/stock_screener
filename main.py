import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe
import datetime as dt
import pandas as pd
from pandas_datareader import data as pdr
import yfinance as yf
from finvizfinance.screener.overview import Overview
from google.cloud import secretmanager
import json
import pytz
import os

# This is set upon gcloud deployment
PROJECT_ID = os.getenv("MY_PROJECT_ID")


def get_secret(secret_name: str):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(name=name)
    secret = response.payload.data.decode("UTF-8")
    # if the secret is a file we need to convert to a dict
    # otherwise keep as is
    try:
        secret = json.loads(secret)
    except:
        pass
    return secret  # returns a json or a string depending on the secret type


def main(request):
    # If we are testing locally get the json file locally otherwise get from cloud
    if request == "test":
        with open("service_account.json") as json_file:
            service_account_json = json.load(json_file)
        pass
    else:
        service_account_json = get_secret("service_account_json")

    # To access Google Sheets
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        service_account_json, scope  # type: ignore
    )

    # we need to get roughly a year's worth of data to evaluate a stock for all the metrics
    now = dt.datetime.now()
    start = now - dt.timedelta(days=400)

    # Explanation on this. https://github.com/ranaroussi/yfinance#pandas_datareader-override
    yf.pdr_override()

    # Choose either Adjusted Close or Regular Close
    closing_types = ["Adj Close", "Close"]
    close = closing_types[1]

    # Use the FinViz API to get the first set of filters out of the way
    foverview = Overview()
    filters_dict = {
        "Market Cap.": "+Mid (over $2bln)",
        "Average Volume": "Over 1M",
        "200-Day Simple Moving Average": "Price above SMA200",
        "50-Day Simple Moving Average": "Price above SMA50",
        "52-Week High/Low": "30% or more above Low",
        "EPS growthqtr over qtr": "Over 20%",
        "Sales growthqtr over qtr": "Over 20%",
    }

    foverview.set_filter(filters_dict=filters_dict)
    finviz = foverview.screener_view()

    if isinstance(finviz, pd.DataFrame):
        finviz = finviz.drop(columns=["P/E"])  # we don't care about P/E

        # Get the DataFrame as list of dicts to loop through
        stocks = finviz.to_dict("records")

    else:
        return "We couldn't get the stocks from FinViz"

    output = pd.DataFrame()  # Create the empty output DataFrame

    # Loop through all the stocks we got from FinViz
    stock_data = []
    for stock in stocks:
        # added this short if statement because finviz changed Ticker to Ticker\n\n
        # if they ever fix it this shoould still work
        if "Ticker\n\n" in stock:
            stock["Ticker"] = stock.pop("Ticker\n\n")

        ticker = stock["Ticker"]

        try:
            df = pdr.get_data_yahoo(ticker, start, now)

            # Get most recently close (last row in df)
            currentClose = df.tail(1)[close][0]

            # Get SMA for 50, 150, 200 and round to 2 decimals
            moving_average_50 = round(df.tail(50)[close].mean(), 2)
            moving_average_150 = round(df.tail(150)[close].mean(), 2)
            moving_average_200 = round(df.tail(200)[close].mean(), 2)

            # Get the SMA_200 20 trading days ago to check if it's been trending up since
            moving_average_200_20 = round(df[close][-221:-21].mean(), 2)

            # Go back a year's worth of trading days and get the min/max
            low_of_52week = round(min(df.tail(255)[close]), 2)
            high_of_52week = round(max(df.tail(255)[close]), 2)

            # Some of the following conditions are already checked in Finviz but I'll do a double check here in case the code is updated
            conditions = []
            # Condition 1: Current Price > 150 SMA and > 200 SMA
            cond_1 = currentClose > moving_average_150 > moving_average_200
            conditions.append(cond_1)

            # Condition 2: 200 SMA trending up for at least 1 month (ideally 4-5 months)
            cond_2 = True if (moving_average_200 > moving_average_200_20) else False
            conditions.append(cond_2)

            # Condition 3: 50 SMA > 150 SMA and 50 SMA > 200 SMA
            cond_3 = (
                True
                if (moving_average_50 > moving_average_150 > moving_average_200)
                else False
            )
            conditions.append(cond_3)

            # Condition 4: Current Price > 50 SMA
            cond_4 = True if (currentClose > moving_average_50) else False
            conditions.append(cond_4)

            # Condition 5: Current Price is at least 30% above 52 week low (Many of the best are up 100-300% before coming out of consolidation)
            cond_5 = True if (currentClose >= (1.3 * low_of_52week)) else False
            conditions.append(cond_5)

            # Condition 6: Current Price is within 25% of 52 week high
            cond_6 = True if (currentClose >= (0.75 * high_of_52week)) else False
            conditions.append(cond_6)

            # count how many conditions are true
            count = sum(1 for cond in conditions if cond)

            # Set values and add to output DataFrame
            stock["cond count"] = count
            stock["cond 1"] = cond_1
            stock["cond 2"] = cond_2
            stock["cond 3"] = cond_3
            stock["cond 4"] = cond_4
            stock["cond 5"] = cond_5
            stock["cond 6"] = cond_6

            stock_data.append(stock)

        except Exception as e:
            print("There was an error with this stock", stock["Ticker"], e)

    output = pd.DataFrame(stock_data)

    # set the type of each column for formatting
    output = output.astype(
        {
            "cond count": "int",
            "cond 1": "int",
            "cond 2": "int",
            "cond 3": "int",
            "cond 4": "int",
            "cond 5": "int",
            "cond 6": "int",
            "Volume": "int",
            "Market Cap": "int",
        }  # type: ignore
    )

    # Round for appearance
    output = output.round({"Volume": 0, "Market Cap": 0, "Price": 2, "Change": 4})
    col_count = len(output.columns)  # how many columns are in the df
    # convert col count to column letter in sheet for formatting
    letter = chr(col_count + 64)
    first_row = f"A1:{letter}1"  # the range for first row in the sheet

    # get New York time to put in the sheet name
    newYorkTz = pytz.timezone("America/New_York")
    timeInNewYork = dt.datetime.now(newYorkTz)
    newYorkTz = timeInNewYork.strftime("%m-%d-%Y")

    # open up the Google Sheets page delete and create a new one
    gc = gspread.authorize(creds)
    gs = gc.open("Stock Screener")
    worksheet_list = gs.worksheets()
    for sheet in worksheet_list:
        if "Screener" in sheet.title:
            sheet = gs.worksheet(sheet.title)
            gs.del_worksheet(sheet)
    sheet = gs.add_worksheet(title=f"Screener {newYorkTz}", rows=1, cols=1)

    # Drop in the data from the data frame to the sheet
    set_with_dataframe(
        worksheet=sheet,
        dataframe=output,
        include_index=False,
        include_column_header=True,
        resize=True,
    )

    # Format the header row
    sheet.format(
        first_row,
        {
            "backgroundColor": {
                "red": 216 / 255,
                "green": 229 / 255,
                "blue": 252 / 255,
            },
            "horizontalAlignment": "CENTER",
            "textFormat": {"fontSize": 12, "bold": True},
        },
    )

    # Format cells for their numbers
    cell = sheet.find("Change")
    if cell:
        letter = chr(cell.col + 64)  # convert col num to letter
        sheet.format(f"{letter}:{letter}", {"numberFormat": {"type": "PERCENT"}})

    cell = sheet.find("Market Cap")
    if cell:
        letter = chr(cell.col + 64)  # convert col num to letter
        sheet.format(
            f"{letter}:{letter}",
            {"numberFormat": {"type": "NUMBER", "pattern": '0,,"M"'}},
        )

    cell = sheet.find("Price")
    if cell:
        letter = chr(cell.col + 64)  # convert col num to letter
        sheet.format(f"{letter}:{letter}", {"numberFormat": {"type": "CURRENCY"}})

    cell = sheet.find("Volume")
    if cell:
        letter = chr(cell.col + 64)  # convert col num to letter
        sheet.format(
            f"{letter}:{letter}",
            {"numberFormat": {"type": "NUMBER", "pattern": '0.0,,"M"'}},
        )

    # Sort and Filter. Filter out to only show the ones that met all 6 conditions, and sort by Volume
    cond_count_cell = sheet.find("cond count")
    if cond_count_cell:
        cond_count_cell = cond_count_cell.col

    vol_cell = sheet.find("Volume")
    if vol_cell:
        vol_cell = vol_cell.col

    if vol_cell and cond_count_cell:
        filterSettings = {
            "range": {"sheetId": sheet.id},
            "filterSpecs": [
                {
                    "filterCriteria": {"hiddenValues": ["0,", "1", "2", "3", "4", "5"]},
                    "columnIndex": cond_count_cell - 1,
                }
            ],
            "sortSpecs": [
                {
                    "sortOrder": "DESCENDING",
                    "dimensionIndex": vol_cell - 1,
                }
            ],
        }
        gs.batch_update({"requests": [{"setBasicFilter": {"filter": filterSettings}}]})
        sheet.columns_auto_resize(0, col_count)  # resize the columns

    # hide the conditions columns (we have 6 of them)
    sheet.hide_columns(col_count - 6, col_count)
    return "Yay Stocks!"


# running locally to test
if __name__ == "__main__":
    import tracemalloc

    tracemalloc.start()
    main("test")
    print(tracemalloc.get_traced_memory())
    tracemalloc.stop()
