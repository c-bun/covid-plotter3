
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

def parse_soup_f2022(soup):
    td = soup.find_all("td")
    result = [x.get_text() for x in td]
    print(result)
    to_send = (
        "Students current/cumulative || Staff current/cumulative\n"
        + result[2] #students current
        + "/"
        + result[3] #students cumulative
        + " || "
        + result[6] #staff current
        + "/"
        + result[7] #staff cumulative
    )
    to_append = [
        int(result[2]),
        int(result[3]),
        -1, # supposed to be quarantine, but not available anymore
        int(result[6]),
        int(result[7]),
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

def reshape_data(data):
    data_students = data[['time', 'pos', 'cumulative']]
    data_students['group'] = 'students'
    data_employees = data[['time', 'employees pos', 'employees cum.']]
    data_employees = data_employees.rename(columns={'employees pos':'pos', 'employees cum.':'cumulative'})
    data_employees = data_employees.dropna(axis=0)
    data_employees['group'] = 'employees'

    return pd.concat([data_students,data_employees])

def generate_figure(data_long, data):

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    d_students = data_long[data_long['group']=='students']
    d_employees = data_long[data_long['group']=='employees']

    fig.add_trace(
        go.Scatter(x=d_students['time'], y=d_students['pos'], name="students pos"),
        secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=d_employees['time'], y=d_employees['pos'], name="employees pos"),
        secondary_y=False
    )

    fig.add_trace(
        go.Scatter(x=d_students['time'], y=d_students['cumulative'], name="students cumulative"),
        secondary_y=True
    )
    fig.add_trace(
        go.Scatter(x=d_employees['time'], y=d_employees['cumulative'], name="employees cumulative"),
        secondary_y=True
    )

    time = datetime.datetime.now().strftime("%x %X")
    fig.update_layout(
        title="Dickinson Cases. (Updated "+time+")"
    )
    fig.update_xaxes(title_text="Day")
    fig.update_yaxes(title_text="Positive Case Count", secondary_y=False)
    fig.update_yaxes(title_text="Cumulative Case Count", secondary_y=True)

        #for setting to view the most recent 20 points?
    fig.update_xaxes(range=[data["time"].iloc[-30], data["time"].iloc[-1]])
    return fig


def upload_figure(fig):
    set_credentials_file(
        username=keys["chart_studio"]["username"],
        api_key=keys["chart_studio"]["api_key"],
    )
    if testing: title = "testplot"
    else: title = "Dickinson College Cases"
    csp.plot(fig, filename=title)


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

    url = 'https://www.dickinson.edu/homepage/1580/covid-19_student_information' # new url for fall 2022
    #url = "https://www.dickinson.edu/homepage/1505/fall_2021_semester_information"

    try:
        page = requests.get(url)

        soup = BeautifulSoup(page.text, "html.parser")

        #current_numbers, to_send = parse_soup(soup)
        current_numbers, to_send = parse_soup_f2022(soup) # new function for fall 2022
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
            data_long = reshape_data(data)
            fig = generate_figure(data_long, data)

            # upload plot
            upload_figure(fig)
            print("Updated plot on plotly.")

        else:
            print("No new numbers right now.")
    except Exception as e:
        print("Error:", e)
        if not testing: telegram_bot_sendtext("Error: "+str(e))
