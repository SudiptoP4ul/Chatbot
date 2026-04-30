import pandas as pd
import numpy as np
import os
import glob
import re
import logging
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client, helpers, transports
from zeep.wsse import UsernameToken

# Suppress technical noise
logging.getLogger('zeep').setLevel(logging.ERROR)

# Configuration
BASE_DIR = '/Users/sudiptogoldfish/code files/7059B A_AI Lab/Chatbot/train service data/'
STATION_CSV = os.path.join(BASE_DIR, 'StationNameAndCode.csv')

USERNAME = "wwang"
PASSWORD = "?i92S6"

# Load Station Data
df_stations = pd.read_csv(STATION_CSV)
df_stations['N'] = df_stations['NAME'].str.upper()
df_stations['C'] = df_stations['CRS'].str.upper()

class Parser:
    def num(self, t): 
        match = re.search(r'\d+', str(t))
        return int(match.group()) if match else 1
    
    def time(self, t): 
        match = re.search(r'\d{1,2}:\d{2}', str(t))
        return match.group() if match else None
    
    def date(self, t): 
        match = re.search(r'\d{4}-\d{2}-\d{2}', str(t))
        return match.group() if match else None

parser = Parser()

class DelayModel:
    """Random Forest Regressor for knowledge-based delay prediction."""
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        self.train()

    def train(self):
        X, y = [], []
        files = glob.glob(os.path.join(BASE_DIR, '*.xlsx'))

        for f in files:
            try:
                df = pd.read_excel(f, engine='openpyxl')
                df['p'] = pd.to_datetime(df['planned_arrival_time'], format='%H:%M:%S', errors='coerce')
                df['a'] = pd.to_datetime(df['actual_arrival_time'], format='%H:%M:%S', errors='coerce')
                df['delay'] = (df['a'] - df['p']).dt.total_seconds() / 60.0
                df = df.dropna(subset=['delay', 'rid'])

                for _, g in df.groupby('rid'):
                    if len(g) < 2: continue
                    g = g.sort_values('p')
                    final_delay = g.iloc[-1]['delay']
                    for i in range(len(g) - 1):
                        X.append([g.iloc[i]['delay'], len(g) - i - 1, i])
                        y.append(final_delay)
            except Exception:
                continue

        if X:
            print("Bot: Training Random Forest model on historical data...")
            self.model.fit(np.array(X), np.array(y))
        else:
            self.model.fit([[0, 0, 0], [10, 2, 1], [20, 3, 2]], [0, 8, 15])

    def predict(self, d, stops=3, pos=1):
        pred = self.model.predict([[d, stops, pos]])
        return max(0, int(round(pred[0])))

predictor = DelayModel()

def find_station(text):
    text = text.upper().strip()
    m = df_stations[df_stations['C'] == text]
    if not m.empty: return m.iloc[0]['NAME'], m.iloc[0]['CRS']
    
    m = df_stations[df_stations['N'] == text]
    if not m.empty: return m.iloc[0]['NAME'], m.iloc[0]['CRS']
    
    if "LONDON" in text:
        return "LONDON WATERLOO", "WAT"
        
    m = df_stations[df_stations['N'].str.contains(rf'\b{text}\b', regex=True, na=False)]
    if not m.empty: return m.iloc[0]['NAME'], m.iloc[0]['CRS']
    return None, None

def ask_station(q):
    while True:
        raw = input(f"{q}: ").strip().upper()
        clean = re.sub(r'\b(I AM|I\'M|GOING TO|FROM|TO|AT|DEPARTING)\b', '', raw)
        clean = re.sub(r'[^A-Z ]', '', clean).strip()

        for token in [clean] + clean.split():
            n, c = find_station(token)
            if n:
                ok = input(f"→ Found {n} ({c}). Correct? [Y/n]: ").lower()
                if ok in ['', 'y', 'yes']: return n, c
        print("Bot: Station not recognized. Try the name or 3-letter code.")

def fetch_fare(o, d, date, time, qty):
    dt = datetime.strptime(f"{date}T{time}", "%Y-%m-%dT%H:%M")
    link = (f"https://www.nationalrail.co.uk/journey-planner/?type=single"
            f"&origin={o}&destination={d}&leavingType=departing"
            f"&leavingDate={dt.strftime('%d%m%y')}&leavingHour={dt.strftime('%H')}"
            f"&leavingMin={dt.strftime('%M')}&adults={qty}")

    try:
        session = Session()
        session.auth = HTTPBasicAuth(USERNAME, PASSWORD)
        client = Client(
            "https://ojp.nationalrail.co.uk/webservices/jpservices.wsdl",
            transport=transports.Transport(session=session),
            wsse=UsernameToken(USERNAME, PASSWORD)
        )

        payload = {
            "origin": {"stationCRS": o},
            "destination": {"stationCRS": d},
            "outwardTime": {"departBy": dt.isoformat()},
            "realtimeEnquiry": "STANDARD",
            "directTrains": False,
            "fareRequestDetails": {"passengers": {"adult": int(qty), "child": 0}, "fareClass": "ANY"}
        }

        resp = client.service.RealtimeJourneyPlan(**payload)
        fares = []
        if resp and hasattr(resp, 'outwardJourney'):
            for j in resp.outwardJourney:
                jd = helpers.serialize_object(j)
                if 'fare' in jd and jd['fare']:
                    for f in jd['fare']:
                        fares.append(float(f['totalPrice']) / 100)

        if fares:
            return f"Cheapest fare: £{min(fares):.2f}\nBooking Link: {link}"
        return f"Cheapest fare: Live price unavailable.\nBooking Link: {link}"

    except Exception as e:
        return f"Error: Live service unavailable ({str(e)}).\nBooking Link: {link}"

def booking_flow():
    print("\n--- Ticket Booking Service ---")
    o_n, o_c = ask_station("Departure station")
    d_n, d_c = ask_station("Destination station")
    qty = parser.num(input("Number of adults: "))
    date = parser.date(input("Travel date (YYYY-MM-DD): "))
    time = parser.time(input("Departure time (HH:MM): "))

    if not date or not time:
        print("Bot: Invalid date/time format.")
        return

    print("\nChecking National Rail...")
    print(fetch_fare(o_c, d_c, date, time, qty))

    # --- RETURN TICKET LOGIC ADDED BELOW ---
    if input("\nDo you need a return? [y/N]: ").lower() == 'y':
        r_date = parser.date(input("Return date (YYYY-MM-DD): "))
        r_time = parser.time(input("Return time (HH:MM): "))
        if r_date and r_time:
            print("\nChecking Return Fare...")
            # We swap o_c and d_c for the return journey
            print(fetch_fare(d_c, o_c, r_date, r_time, qty))
        else:
            print("Bot: Invalid return date or time format.")

def delay_flow():
    print("\n--- Delay Prediction (Random Forest) ---")
    curr_n, _ = ask_station("Current station")
    dest_n, _ = ask_station("Final destination")
    d = parser.num(input(f"Minutes delay at {curr_n}: "))
    sched = parser.time(input(f"Scheduled arrival at {dest_n} (HH:MM): "))

    if sched:
        pred = predictor.predict(d)
        new_time = datetime.strptime(sched, "%H:%M") + timedelta(minutes=pred)
        print(f"\nReported delay: {d} min")
        print(f"Predicted delay at end: {pred} min")
        print(f"Expected arrival: {new_time.strftime('%H:%M')}")
    else:
        print("Bot: Invalid time format.")

def main():
    while True:
        print("\nSWR TRANSIT MENU")
        print("1) Book Ticket\n2) Delay Prediction\n3) Exit")
        choice = input("> ").strip()
        if choice == '1': booking_flow()
        elif choice == '2': delay_flow()
        elif choice == '3': break
        else: print("Select 1, 2 or 3.")

if __name__ == "__main__":
    print("Initializing SWR Assistant...")
    main()