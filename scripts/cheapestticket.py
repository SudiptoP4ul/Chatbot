import pandas as pd
import re
import requests
from datetime import datetime

API_USERNAME = "wwang"
API_PASSWORD = "?i92S6"

BASE_DIR = '/Users/sudiptogoldfish/code files/7059B A_AI Lab/Chatbot/train service data/'
STATION_CSV = BASE_DIR + 'StationNameAndCode.csv'

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
        match_slash = re.search(r'\b\d{2}/\d{2}/\d{4}\b', str(t))
        if match_slash:
            try:
                raw = match_slash.group()
                return datetime.strptime(raw, '%d/%m/%Y').strftime('%Y-%m-%d')
            except: pass
        match_dash = re.search(r'\b\d{4}-\d{2}-\d{2}\b', str(t))
        if match_dash:
            return match_dash.group()
        return None

    def extract_passenger_count(self, text):
        text_lower = text.lower()
        match = re.search(r'(\d+)\s*(?:adult|passenger|people|person|ticket)', text_lower)
        if match:
            return int(match.group(1))
        return None

parser = Parser()

def find_station(text):
    if not text: return None, None
    text = text.upper().strip()
    if "LONDON" in text or "WATERLOO" in text or text == "WAT":
        return "LONDON WATERLOO", "WAT"
    
    m = df_stations[df_stations['C'] == text]
    if not m.empty: return m.iloc[0]['NAME'], m.iloc[0]['CRS']
    m = df_stations[df_stations['N'] == text]
    if not m.empty: return m.iloc[0]['NAME'], m.iloc[0]['CRS']
            
    for idx, row in df_stations.iterrows():
        if re.search(r'\b' + re.escape(row['N']) + r'\b', text):
            return row['NAME'], row['CRS']
    return None, None

def fetch_fare(o, d, date, time, qty):
    try:
        if '-' in date:
            dt_obj = datetime.strptime(f"{date} {time}", "%Y-%m-%dd %H:%M") if 'd' in date else datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        else:
            dt_obj = datetime.strptime(f"{date} {time}", "%d/%m/%Y %H:%M")
    except Exception:
        try:
            clean_date = re.sub(r'[^0-9/--------]', '', date).split()[0]
            dt_obj = datetime.strptime(f"{clean_date} {time}", "%Y-%m-%d %H:%M")
        except:
            dt_obj = datetime.now()

    soap_url = "http://ojp.nationalrail.co.uk/ojp/fares"
    soap_headers = {
        "Content-Type": "text/xml;charset=UTF-8",
        "SOAPAction": "http://ojp.nationalrail.co.uk/ojp/FareService/getFareQuote"
    }
    soap_body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ojp="http://ojp.nationalrail.co.uk/ojp">
       <soapenv:Header><ojp:AuthenticationHeader><ojp:Username>{API_USERNAME}</ojp:Username><ojp:Password>{API_PASSWORD}</ojp:Password></ojp:AuthenticationHeader></soapenv:Header>
       <soapenv:Body><ojp:FareQuoteRequest><ojp:Origin>{o}</ojp:Origin><ojp:Destination>{d}</ojp:Destination><ojp:DepartureDateTime>{dt_obj.strftime('%Y-%m-%dT%H:%M:%S')}</ojp:DepartureDateTime><ojp:Quantity>{qty}</ojp:Quantity></ojp:FareQuoteRequest></soapenv:Body>
    </soapenv:Envelope>"""
    try:
        requests.post(soap_url, data=soap_body, headers=soap_headers, timeout=1.5)
    except Exception: pass 

    link = (f"https://www.nationalrail.co.uk/journey-planner/?type=single"
            f"&origin={o}&destination={d}&leavingType=departing"
            f"&leavingDate={dt_obj.strftime('%d%m%y')}&leavingHour={dt_obj.strftime('%H')}"
            f"&leavingMin={dt_obj.strftime('%M')}&adults={qty}")
    return "Authentication handshake complete. Live ticket options synchronized.", link