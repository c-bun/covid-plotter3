
testing = False

# script:
# read in data
# check site
# compare data
# if different:
# send message
# append data
# update plotly

import pandas as pd
import datetime
import requests
from bs4 import BeautifulSoup
import plotly.express as px
import plotly.graph_objects as go
import chart_studio.plotly as csp
from chart_studio.tools import set_credentials_file
import json


def initialize_keys(path):
    return json.load(open(path))


def parse_soup(soup):
    td = soup.find_all("td")
    result = [x.get_text() for x in td]
    print(result)
    to_send = (
        "Students pos/cum.pos/quarantine || Staff pos/cum.pos\n"
        + result[2]
        + "/"
        + result[3]
        + "/"
        + result[4]
        + " || "
        + result[7]
        + "/"
        + result[8]
    )
    to_append = [
        int(result[2]),
        int(result[3]),
        int(result[4]),
        int(result[7]),
        int(result[8]),
    ]
    return to_append, to_send


def telegram_bot_sendtext(bot_message):

    bot_token = keys["telegram"]["bot_token"]
    bot_chatID = keys["telegram"]["bot_chatID"]
    send_text = (
        "https://api.telegram.org/bot"
        + bot_token
        + "/sendMessage?chat_id="
        + bot_chatID
        + "&parse_mode=Markdown&text="
        + bot_message
    )

    response = requests.get(send_text)

    return response.json()


def generate_figure(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["pos"],
        name="Student Cases",
        line=dict(color='firebrick', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["employees pos"],
        name="Employee Cases",
        line=dict(color='royalblue', width=2)
    ))
    
    fig.update_layout(title="Dickinson Positive Cases", xaxis_title="Day", yaxis_title="Case Count")
    #for setting to view the most recent 20 points?
    fig.update_xaxes(range=[data["time"].iloc[-30], data["time"].iloc[-1]])

    return fig


def upload_figure(fig):
    set_credentials_file(
        username=keys["chart_studio"]["username"],
        api_key=keys["chart_studio"]["api_key"],
    )
    csp.plot(fig, filename="Dickinson College Cases. Updated "+datetime.datetime.now().strftime("%x %X"))


def add_data(data, new_data):
    time = datetime.datetime.now().strftime("%x %X")
    new_numbers = pd.DataFrame(
        {
            "time": [time],
            "pos": [new_data[0]],
            "cumulative": [new_data[1]],
            "quarantine": [new_data[2]],
            "employees pos": [new_data[3]],
            "employees cum.": [new_data[4]],
        }
    )
    return data.append(new_numbers, ignore_index=True)


if __name__ == "__main__":

    keys = initialize_keys("./keys.json")

    try:
        data = pd.read_csv("./data.csv", index_col=0)
    except FileNotFoundError:
        print("CSV does not exist. Creating new one.")
        time = datetime.datetime.now().strftime("%x %X")
        df = pd.DataFrame(
            {"time": [time], "pos": [0], "cumulative": [0], "quarantine": [0]}
        )
        df.to_csv("./data.csv")
        data = pd.read_csv("./data.csv", index_col=0)

    print("found data, reading site")

    url = "https://www.dickinson.edu/homepage/1505/fall_2021_semester_information"
    page = requests.get(url)

    soup = BeautifulSoup(page.text, "html.parser")

    current_numbers, to_send = parse_soup(soup)
    print("Found Current numbers:", to_send)

    last_numbers = list(data.iloc[-1].values[1:])

    if (last_numbers != current_numbers) or testing:
        print("New numbers!")
        data = add_data(data, current_numbers)
        print("Appended. Writing csv.")
        data.to_csv("./data.csv")

        # send telegram
        if not testing: telegram_bot_sendtext(to_send)

        # update plot
        data["time"] = pd.to_datetime(data["time"])
        fig = generate_figure(data)

        # upload plot
        if not testing:
            upload_figure(fig)
        print("Updated plot on plotly.")

    else:
        print("No new numbers right now.")
