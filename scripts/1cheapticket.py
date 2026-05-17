import pandas as pd
import requests
import logging
import re

from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from zeep import Client, helpers, transports

try:
    from zeep.wsse.username_token import UsernameToken
except:
    from zeep.wsse import UsernameToken

logging.basicConfig(level=logging.ERROR)
logging.getLogger("zeep").setLevel(logging.ERROR)

USERNAME = "wwang"
PASSWORD = "?i92S6"

CSV_PATH = "/Users/sudiptogoldfish/code files/7059B A_AI Lab/Chatbot/train service data/StationNameAndCode.csv"

df = pd.read_csv(CSV_PATH)

df["NAME_U"] = df["NAME"].astype(str).str.upper()
df["CRS_U"] = df["CRS"].astype(str).str.upper()


def clean_text(text):

    text = text.lower()

    text = text.replace("i want to go to", "to")
    text = text.replace("i want to travel to", "to")
    text = text.replace("i am travelling to", "to")
    text = text.replace("i am traveling to", "to")
    text = text.replace("going to", "to")
    text = text.replace("travelling to", "to")
    text = text.replace("traveling to", "to")

    text = text.replace("from", " from ")
    text = text.replace("to", " to ")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_date(text):

    if "today" in text:
        return datetime.now().strftime("%d/%m/%Y")

    if "tomorrow" in text:
        return (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")

    m = re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", text)

    if m:
        return m.group(0)

    return None


def extract_time(text):

    m = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", text)

    if m:
        return m.group(0)

    return None


def extract_adults(text):

    m = re.search(
        r"(\d+)\s*(adult|adults|people|passengers?)",
        text
    )

    if m:
        return int(m.group(1))

    return 1


def extract_stations(text):

    origin = None
    destination = None

    p1 = re.search(
        r"from\s+(.+?)\s+to\s+(.+?)(?:\s+with|\s+on|\s+at|$)",
        text
    )

    p2 = re.search(
        r"to\s+(.+?)\s+from\s+(.+?)(?:\s+with|\s+on|\s+at|$)",
        text
    )

    if p1:
        origin = p1.group(1).strip()
        destination = p1.group(2).strip()

    elif p2:
        destination = p2.group(1).strip()
        origin = p2.group(2).strip()

    return origin, destination


def resolve_station(raw):

    if not raw:
        return None

    raw = raw.upper().strip()

    london_map = {
        "LONDON": "WAT",
        "LONDON WATERLOO": "WAT",
        "WATERLOO": "WAT"
    }

    if raw in london_map:

        row = df[df["CRS_U"] == london_map[raw]]

        if not row.empty:
            return row.iloc[0]

    exact_code = df[df["CRS_U"] == raw]

    if not exact_code.empty:
        return exact_code.iloc[0]

    exact_name = df[df["NAME_U"] == raw]

    if not exact_name.empty:
        return exact_name.iloc[0]

    contains = df[df["NAME_U"].str.contains(raw, na=False)]

    if not contains.empty:

        contains = contains[
            ~contains["NAME_U"].str.contains("UNDERGROUND", na=False)
        ]

        contains = contains.sort_values(
            by="NAME_U",
            key=lambda s: s.str.len()
        )

        return contains.iloc[0]

    return None


def confirm_station(raw):

    station = resolve_station(raw)

    if station is None:
        return None, None

    name = station["NAME"]
    code = station["CRS"]

    ans = input(
        f"Bot: I found {name} ({code}). Is that correct? (y/n): "
    ).lower().strip()

    if ans in ["y", "yes", ""]:
        return name, code

    return None, None


def search_ticket(origin, dest, date, time, adults):

    try:

        dt = datetime.strptime(
            f"{date} {time}",
            "%d/%m/%Y %H:%M"
        )

        session = requests.Session()

        session.auth = HTTPBasicAuth(
            USERNAME,
            PASSWORD
        )

        client = Client(
            "https://ojp.nationalrail.co.uk/webservices/jpservices.wsdl",
            transport=transports.Transport(session=session),
            wsse=UsernameToken(USERNAME, PASSWORD)
        )

        payload = {
            "origin": {
                "stationCRS": origin
            },

            "destination": {
                "stationCRS": dest
            },

            "realtimeEnquiry": "STANDARD",

            "outwardTime": {
                "departBy": dt.isoformat()
            },

            "directTrains": False,

            "fareRequestDetails": {
                "passengers": {
                    "adult": int(adults),
                    "child": 0
                },

                "fareClass": "ANY"
            }
        }

        resp = client.service.RealtimeJourneyPlan(**payload)

        fares = []

        if resp and hasattr(resp, "outwardJourney"):

            for journey in resp.outwardJourney:

                j = helpers.serialize_object(journey)

                if "fare" in j:

                    for fare in j["fare"]:

                        try:

                            fares.append({
                                "price": float(fare["totalPrice"]) / 100,
                                "type": fare.get(
                                    "description",
                                    "Standard"
                                )
                            })

                        except:
                            pass

        if not fares:

            return None

        cheapest = min(
            fares,
            key=lambda x: x["price"]
        )

        booking_link = (
            f"https://www.nationalrail.co.uk/journey-planner/"
            f"?type=single"
            f"&origin={origin}"
            f"&destination={dest}"
            f"&leavingType=departing"
            f"&leavingDate={dt.strftime('%d%m%y')}"
            f"&leavingHour={dt.strftime('%H')}"
            f"&leavingMin={dt.strftime('%M')}"
            f"&adults={adults}"
        )

        return {
            "price": cheapest["price"],
            "type": cheapest["type"],
            "link": booking_link
        }

    except Exception as e:

        print(f"\nBot: API Error: {e}")

        return None


print("\nHi, I am your Smart Rail Ticket Booking Chatbot.")
print("How can I help you today?\n")

user = input("You: ")

user = clean_text(user)

origin_raw, dest_raw = extract_stations(user)

date = extract_date(user)
time = extract_time(user)
adults = extract_adults(user)

origin_name = None
origin_code = None

dest_name = None
dest_code = None


if origin_raw:

    origin_name, origin_code = confirm_station(origin_raw)


while not origin_code:

    ans = input(
        "Bot: Where are you travelling from?\nYou: "
    )

    origin_name, origin_code = confirm_station(ans)


if dest_raw:

    dest_name, dest_code = confirm_station(dest_raw)


while not dest_code:

    ans = input(
        "Bot: Where are you travelling to?\nYou: "
    )

    dest_name, dest_code = confirm_station(ans)


while not date:

    date = input(
        "Bot: Departure date (DD/MM/YYYY):\nYou: "
    )


while not time:

    time = input(
        "Bot: Departure time (HH:MM):\nYou: "
    )


print(
    f"\nBot: Searching tickets from "
    f"{origin_name} to {dest_name}..."
)

result = search_ticket(
    origin_code,
    dest_code,
    date,
    time,
    adults
)

if result:

    print("\nBot: Cheapest Ticket")
    print(f"Bot: £{result['price']:.2f}")
    print(f"Bot: {result['type']}")

    print("\nBot: Booking Link")
    print(result["link"])

else:
    print("\nBot: No tickets found.")


ret = input(
    "\nBot: Do you need a return ticket? (y/n)\nYou: "
).lower()


if ret in ["y", "yes"]:

    r_date = input(
        "Bot: Return date (DD/MM/YYYY):\nYou: "
    )

    r_time = input(
        "Bot: Return time (HH:MM):\nYou: "
    )

    r = search_ticket(
        dest_code,
        origin_code,
        r_date,
        r_time,
        adults
    )

    if r:

        print("\nBot: Cheapest Return Ticket")
        print(f"Bot: £{r['price']:.2f}")
        print(f"Bot: {r['type']}")

        print("\nBot: Return Booking Link")
        print(r["link"])

print("\nBot: Thank you for using Smart Rail Assistant.")