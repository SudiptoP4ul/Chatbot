import pandas as pd
import requests, logging, re
from datetime import datetime
from requests.auth import HTTPBasicAuth
from zeep import Client, helpers, transports

try:
    from zeep.wsse.username_token import UsernameToken
except ImportError:
    from zeep.wsse import UsernameToken

# Silence the 'Forcing soap:address' and other library warnings
logging.basicConfig(level=logging.ERROR)
logging.getLogger('zeep').setLevel(logging.ERROR)

CSV_PATH = '/Users/sudiptogoldfish/code files/7059B A_AI Lab/Chatbot/train service data/StationNameAndCode.csv'
df = pd.read_csv(CSV_PATH)
df['N_U'], df['C_U'] = df['NAME'].str.upper(), df['CRS'].str.upper()

def clean_input(text):
    fillers = [r"I AM TRAVELING TO", r"I'M TRAVELING TO", r"I AM GOING TO", r"GOING TO", 
               r"HEADING TO", r"STARTING FROM", r"TRAVELING FROM", r"FROM", r"TO"]
    text = text.upper()
    for f in fillers: text = re.sub(f, "", text)
    return text.strip()

def get_station(prompt):
    while True:
        raw = input(f"Bot: {prompt}\nYou: ")
        val = clean_input(raw)
        
        match = df[df['C_U'] == val]
        if match.empty: match = df[df['N_U'] == val]
        if match.empty:
            pot = df[df['N_U'].str.contains(val, na=False)].copy()
            if not pot.empty:
                main = pot[~pot['N_U'].str.endswith((' BUS', ' UNDERGROUND'))]
                match = (main if not main.empty else pot).assign(l=pot['NAME'].str.len()).sort_values('l').head(1)
        
        if not match.empty:
            n, c = match.iloc[0]['NAME'], match.iloc[0]['CRS']
            check = input(f"Bot: I found {n} ({c}), is that right? (y/n, default 'y'): ").lower().strip()
            if check in ['y', 'yes', '']: return n, c
        print(f"Bot: Sorry, I couldn't find a station. Try being more specific.")

def search(o_c, d_c, date, time, qty):
    try:
        dt = datetime.strptime(f"{date}T{time}", "%Y-%m-%dT%H:%M")
        session = requests.Session()
        session.auth = HTTPBasicAuth("username", "password")
        client = Client("https://ojp.nationalrail.co.uk/webservices/jpservices.wsdl", 
                        transport=transports.Transport(session=session), 
                        wsse=UsernameToken("username", "password"))
        
        payload = {
            "origin": {"stationCRS": o_c}, 
            "destination": {"stationCRS": d_c},
            "realtimeEnquiry": "STANDARD", 
            "outwardTime": {"departBy": dt.isoformat()},
            "directTrains": False, # Re-added this mandatory field
            "fareRequestDetails": {"passengers": {"adult": int(qty), "child": 0}, "fareClass": "ANY"}
        }

        resp = client.service.RealtimeJourneyPlan(**payload)
        fares = []
        if resp and hasattr(resp, 'outwardJourney') and resp.outwardJourney:
            for j in resp.outwardJourney:
                jd = helpers.serialize_object(j)
                for f in jd.get('fare', []):
                    fares.append({'p': float(f['totalPrice'])/100, 't': f.get('description', 'Standard')})
        
        if not fares: return None
        best = min(fares, key=lambda x: x['p'])
        link = f"https://www.nationalrail.co.uk/journey-planner/?type=single&origin={o_c}&destination={d_c}&leavingType=departing&leavingDate={dt.strftime('%d%m%y')}&leavingHour={dt.strftime('%H')}&leavingMin={dt.strftime('%M')}&adults={qty}&extraTime=0"
        return f"🎫 Best Fare: £{best['p']:.2f} ({best['t']})\n🔗 Book: {link}"
    except Exception as e:
        return f"Error connecting to National Rail: {str(e)}"

if __name__ == "__main__":
    print("\nBot: Hi! I'm your travel assistant. Let's find you a ticket.")
    o_n, o_c = get_station("Where are you starting from?")
    d_n, d_c = get_station("And where are you going?")
    
    qty = input("Bot: How many adults are traveling?\nYou: ")
    date = input("Bot: Departure date (YYYY-MM-DD)?\nYou: ")
    time = input("Bot: Departure time (HH:MM)?\nYou: ")

    print(f"\nBot: Searching from {o_n} to {d_n}...")
    result = search(o_c, d_c, date, time, qty)
    
    if result and "Best Fare" in result:
        print(f"Bot: {result}")
    else:
        print(f"Bot: {result or 'No fares found. Try a specific station (e.g. LST instead of LON).'}")

    if 'y' in input("\nBot: Need a return ticket? (y/n): ").lower():
        r_q = input("Bot: How many adults for the return?\nYou: ")
        r_d = input("Bot: Return date (YYYY-MM-DD)?\nYou: ")
        r_t = input("Bot: Return time (HH:MM)?\nYou: ")
        print(f"\nBot: {search(d_c, o_c, r_d, r_t, r_q) or 'No fares found.'}")

    print("\nBot: All set! Have a safe journey! 🚂")
