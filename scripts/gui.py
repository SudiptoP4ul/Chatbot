import ssl
import certifi
import re
import flet as ft
from datetime import datetime, timedelta

ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

# imports from tasks' codes
from cheapestticket import df_stations, parser, find_station, fetch_fare
from knowledgebase import predictor
from contingency import expert_system

def main(page: ft.Page):
    page.title = "Smart Railway System Chatbot - PG17 (v1.0)"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#06070B"
    page.window_width = 1200
    page.window_height = 800
    page.padding = 0

    CENTER = ft.Alignment(0, 0)

    conversation = {
        "mode": "booking",                
        "origin": None,
        "destination": None,
        "date": None,
        "time": None,
        "adults": 1,
        "return_requested": False,         
        "awaiting_return_details": False, 
        "return_date": None,
        "return_time": None,
        "last_asked": None,
        "delay_minutes": None,
        "scheduled_arrival": None,
        "awaiting_followup_response": False,
        
        "contingency_location": None,
        "contingency_type": None,
        "contingency_severity": None
    }

    chat_view = ft.ListView(expand=True, spacing=12, auto_scroll=True, padding=20, visible=False)

    def handle_calendar_change(e):
        if date_picker.value:
            # Shift the date forward by exactly 1 day to correct for the Flet UI picker offset bug
            corrected_date = date_picker.value + timedelta(days=1)
            
            # Format cleanly into DD/MM/YYYY string format
            selected_date = f"{corrected_date.day:02d}/{corrected_date.month:02d}/{corrected_date.year}"
            
            if conversation["last_asked"] == "date":
                conversation["date"] = selected_date
                input_box.value = selected_date
            elif conversation["awaiting_return_details"] or conversation["last_asked"] == "return_date":
                conversation["return_date"] = selected_date
                input_box.value = selected_date
            page.update()

    date_picker = ft.DatePicker(on_change=handle_calendar_change)
    page.overlay.append(date_picker)

    def trigger_calendar_view(e):
        # VERSION COMPATIBILITY FIX: Swapped .pick_date() to programmatic property definition rules
        date_picker.open = True
        page.update()

    calendar_button = ft.Container(
        content=ft.Text("📅", size=22),
        alignment=CENTER,
        padding=10,
        on_click=trigger_calendar_view,
        tooltip="Open Calendar Picker"
    )

    def add_user_message(message):
        chat_view.controls.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.END,
                controls=[ft.Container(content=ft.Text(message, color="white", size=15), bgcolor="#2563EB", border_radius=20, padding=15)]
            )
        )

    def add_bot_message(message, primary_link=None, return_link=None):
        controls = [ft.Text(message, color="white", selectable=True, size=15)]
        if primary_link:
            controls.append(ft.TextButton("Click and Book Outbound Journey", url=primary_link))
        if return_link:
            controls.append(ft.TextButton("Click and Book Return Journey", url=return_link))
        
        chat_view.controls.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.START,
                controls=[ft.Container(content=ft.Column(controls), bgcolor="#17181D", border_radius=20, padding=15)]
            )
        )
        page.update()

    welcome_container = ft.Container(
        expand=True, alignment=CENTER,
        content=ft.Column(
            [
                ft.Text("How can I help you today?", size=36, color="#E5E7EB", weight=ft.FontWeight.W_300),
                ft.Text("Live Ticket Booking, Delay Prediction & Integrated Operational Contingency Expert", size=16, color="#6B7280"),
            ],
            alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    def activate_glow(e=None):
        input_bar.shadow = ft.BoxShadow(spread_radius=2, blur_radius=40, color="#2563EB", offset=ft.Offset(0, 0))
        page.update()

    def deactivate_glow(e=None):
        if input_box.value.strip(): return
        input_bar.shadow = ft.BoxShadow(spread_radius=1, blur_radius=20, color="#123A7A", offset=ft.Offset(0, 0))
        page.update()

    def extract_and_fill_stations(text):
        clean_s = text.upper().strip()
        if "LONDON" in clean_s or "WATERLOO" in clean_s:
            return ["LONDON WATERLOO"]
        matched_stations = []
        for idx, row in df_stations.iterrows():
            if re.search(r'\b' + re.escape(str(row.iloc[0]).upper()) + r'\b', clean_s) or re.search(r'\b' + re.escape(str(row.iloc[1]).upper()) + r'\b', clean_s):
                matched_stations.append(str(row.iloc[0]))
        return matched_stations

    def process_message(user_text):
        if any(w in user_text.lower() for w in ["blockage", "incident", "contingency", "emergency", "closure", "failed", "disruption"]):
            conversation["mode"] = "contingency"
        elif any(w in user_text.lower() for w in ["delay", "late", "prediction", "predict", "showing"]):
            if conversation["mode"] != "contingency":
                conversation["mode"] = "delay"
            
        stations = extract_and_fill_stations(user_text)

        # ---- OPERATIONAL STAFF EMERGENCY CONTINGENCY MATRIX ----
        if conversation["mode"] == "contingency":
            if stations and not conversation["contingency_location"]:
                conversation["contingency_location"] = stations[0]
            
            if any(w in user_text.lower() for w in ["full", "complete", "total", "entire", "blocked entirely"]):
                conversation["contingency_severity"] = "FULL"
            elif any(w in user_text.lower() for w in ["partial", "part", "some", "restricted"]):
                conversation["contingency_severity"] = "PARTIAL"
                
            if any(w in user_text.lower() for w in ["signal", "light", "fault"]):
                conversation["contingency_type"] = "SIGNAL FAILURE"
            elif any(w in user_text.lower() for w in ["track", "blockage", "derail", "line", "obstruction"]):
                conversation["contingency_type"] = "TRACK BLOCKAGE"

            if not conversation["contingency_location"]:
                conversation["last_asked"] = "cont_loc"
                return "Which operational station hub or sector line is experiencing the disruption?", None, None
            if not conversation["contingency_type"]:
                conversation["last_asked"] = "cont_type"
                return f"What event layout happened at {conversation['contingency_location']}? (Track Blockage / Signal Failure)", None, None
            if not conversation["contingency_severity"]:
                conversation["last_asked"] = "cont_sev"
                return "Specify incident impact metrics: (Full Blockage / Partial Blockage)", None, None

            plans = expert_system.evaluate_incident(
                conversation["contingency_severity"], 
                conversation["contingency_type"],
                conversation["contingency_location"]
            )
            
            expert_system.log_incident_to_db(
                conversation["contingency_type"], conversation["contingency_location"],
                conversation["contingency_severity"], plans["advice_staff"], plans["advice_passenger"]
            )

            reply = (f"⚠️ --- EMERGENCY OPERATION PLAN DISPATCHED ---\n"
                     f"• Affected Node: {conversation['contingency_location']}\n"
                     f"• Classification: {conversation['contingency_type']} [{conversation['contingency_severity']}]\n\n"
                     f"📋 INTERNAL COMMAND INSTRUCTIONS FOR STAFF:\n{plans['advice_staff']}\n\n"
                     f"📢 EXTERNAL DIRECTIVES FOR PASSENGERS:\n{plans['advice_passenger']}\n\n"
                     f"Operational footprint saved into system database file securely. Any other requests?")
            
            conversation.update({"mode": "booking", "contingency_location": None, "contingency_type": None, "contingency_severity": None, "last_asked": None, "awaiting_followup_response": True})
            return reply, None, None

        # ---- ML MODEL TRAIN LATENCY REGRESSOR ----
        if conversation["mode"] == "delay":
            if conversation["last_asked"] == "origin" and stations: conversation["origin"] = stations[0]
            elif conversation["last_asked"] == "destination" and stations: conversation["destination"] = stations[0]
            else:
                if len(stations) >= 2:
                    conversation["origin"] = stations[0]
                    conversation["destination"] = stations[1]
                elif len(stations) == 1:
                    conversation["origin"] = stations[0]

            mins = parser.num(user_text)
            if mins > 1 and mins != conversation["adults"] and "min" in user_text.lower():
                conversation["delay_minutes"] = mins

            clock_time = parser.time(user_text)
            if clock_time: conversation["scheduled_arrival"] = clock_time

            if not conversation["origin"]:
                conversation["last_asked"] = "origin"
                return "Which station are you querying?", None, None
            if not conversation["destination"]:
                conversation["last_asked"] = "destination"
                return "What is the final target terminal station?", None, None
            if conversation["delay_minutes"] is None:
                conversation["last_asked"] = "delay_mins"
                return f"How many minutes delay is showing on-screen at {conversation['origin']}?", None, None
            if not conversation["scheduled_arrival"]:
                conversation["last_asked"] = "sched_arr"
                return "What is the timetabled arrival window at that target? (HH:MM)", None, None

            pred_mins = predictor.predict(int(conversation["delay_minutes"]))
            try:
                base_time = datetime.strptime(conversation["scheduled_arrival"], "%H:%M")
                final_time = base_time + timedelta(minutes=pred_mins)
                eta_str = final_time.strftime("%H:%M")
            except: eta_str = "Unavailable"

            expert_system.log_predictive_run(conversation["origin"], conversation["destination"], int(conversation["delay_minutes"]), pred_mins)

            reply = (f"--- ML DELAY REGRESSOR EXTRAPOLATION ---\n"
                     f"• Transit Sector: {conversation['origin']} ➔ {conversation['destination']}\n"
                     f"• Current Latency: {conversation['delay_minutes']} mins\n"
                     f"• Predicted Terminal Blockage Delay: {pred_mins} mins\n"
                     f"• Calculated Arrival Window: {eta_str}\n\n"
                     f"Metrics logged safely into integrated relational histories. Any other tasks needed?")
            conversation.update({"mode": "booking", "origin": None, "destination": None, "date": None, "time": None, "return_requested": False, "awaiting_return_details": False, "delay_minutes": None, "scheduled_arrival": None, "last_asked": None, "awaiting_followup_response": True})
            return reply, None, None

        # ---- STANDARD TICKET BOOKING CORE ----
        upper_text = user_text.upper()
        to_match = re.search(r'\b(TO|GO TO|GOING TO)\b\s*([A-Z\s]+)', upper_text)
        from_match = re.search(r'\b(FROM|DEPARTING FROM)\b\s*([A-Z\s]+)', upper_text)
        extracted_dest, extracted_orig = None, None
        
        if to_match:
            _, d_code = find_station(to_match.group(2))
            if d_code: extracted_dest = next((s for s in stations if find_station(s)[1] == d_code), None)
        if from_match:
            _, o_code = find_station(from_match.group(2))
            if o_code: extracted_orig = next((s for s in stations if find_station(s)[1] == o_code), None)

        if conversation["last_asked"] == "origin" and stations: conversation["origin"] = stations[0]
        elif conversation["last_asked"] == "destination" and stations: conversation["destination"] = stations[0]
        else:
            if extracted_orig: conversation["origin"] = extracted_orig
            if extracted_dest: conversation["destination"] = extracted_dest
            if len(stations) >= 2 and not conversation["origin"] and not conversation["destination"]:
                conversation["origin"] = stations[0]
                conversation["destination"] = stations[1]
            elif len(stations) == 1 and not conversation["origin"] and not conversation["destination"]:
                conversation["destination"] = stations[0]

        extracted_date = parser.date(user_text)
        if extracted_date: conversation["date"] = extracted_date
        extracted_time = parser.time(user_text)
        if extracted_time: conversation["time"] = extracted_time
        
        p_count = parser.extract_passenger_count(user_text)
        if p_count is not None: conversation["adults"] = p_count

        if any(w in user_text.lower() for w in ["return", "round trip", "two way"]):
            conversation["return_requested"] = True

        if not conversation["origin"]:
            conversation["last_asked"] = "origin"
            return "Where are you traveling from?", None, None
        if not conversation["destination"]:
            conversation["last_asked"] = "destination"
            return "Where are you going?", None, None
        if not conversation["date"]:
            conversation["last_asked"] = "date"
            return "What date would you like to travel? (Use calendar widget or enter DD/MM/YYYY)", None, None
        if not conversation["time"]:
            conversation["last_asked"] = "time"
            return "What departure time? (HH:MM)", None, None

        conversation["last_asked"] = None

        if conversation["return_requested"] and conversation["return_date"] and conversation["return_time"]:
            o_n, o_c = find_station(conversation["origin"])
            d_n, d_c = find_station(conversation["destination"])
            fare_out, link_out = fetch_fare(o_c, d_c, conversation["date"], conversation["time"], conversation["adults"])
            fare_ret, link_ret = fetch_fare(d_c, o_c, conversation["return_date"], conversation["return_time"], conversation["adults"])
            
            reply = (f"Ticket endpoints synced!\n\nOutbound Journey:\n• {fare_out}\n\nReturn Journey:\n• {fare_ret}\n\nAnything else I can build?")
            conversation.update({"origin": None, "destination": None, "date": None, "time": None, "return_requested": False, "awaiting_return_details": False, "return_date": None, "return_time": None, "awaiting_followup_response": True})
            return reply, link_out, link_ret

        if conversation["return_requested"] and (not conversation["return_date"] or not conversation["return_time"]):
            conversation["awaiting_return_details"] = True
            return "Please specify a return travel date and time (Use calendar picker or enter DD/MM/YYYY HH:MM):", None, None

        o_n, o_c = find_station(conversation["origin"])
        d_n, d_c = find_station(conversation["destination"])
        fare_text, booking_url = fetch_fare(o_c, d_c, conversation["date"], conversation["time"], conversation["adults"])
        
        reply = (f"Ticket parameters locked successfully!\n• Route: {o_n} ➔ {d_n}\n• Layout: {conversation['adults']} Adult passenger(s)\n• {fare_text}\n\nWould you like to assign a return route ticket to this build? (Yes/No)")
        return reply, booking_url, None

    def handle_send(e=None):
        user_text = input_box.value.strip()
        if not user_text: return
        
        if welcome_container.visible:
            welcome_container.visible = False
            chat_view.visible = True
        add_user_message(user_text)

        bot_reply, p_link, r_link = "", None, None

        if conversation["awaiting_followup_response"]:
            has_keywords = any(w in user_text.lower() for w in ["delay", "late", "predict", "showing", "ticket", "book", "blockage", "incident", "emergency"])
            if has_keywords: conversation["awaiting_followup_response"] = False
            else:
                clean_intent = user_text.lower().strip()
                if clean_intent in ["no", "nope", "nothing", "thank you", "thanks", "bye"]:
                    bot_reply = "System session cleared down successfully. Have safe travels! 👋"
                    expert_system.log_interaction_to_db(conversation["mode"], user_text, bot_reply)
                    conversation.update({"origin": None, "destination": None, "date": None, "time": None, "return_requested": False, "awaiting_return_details": False, "awaiting_followup_response": False, "mode": "booking"})
                    input_box.value = ""
                    deactivate_glow()
                    add_bot_message(bot_reply, None, None)
                    return

        if conversation["return_requested"] and not conversation["awaiting_return_details"] and not conversation["return_date"] and conversation["mode"] == "booking":
            if user_text.lower() in ["yes", "y", "yeah", "sure"]:
                conversation["awaiting_return_details"] = True
                bot_reply = "Please specify the return trip date (or select via calendar widget):"
            else:
                bot_reply = "Outbound track processing saved. Any other assistance needed?"
                conversation.update({"origin": None, "destination": None, "date": None, "time": None, "return_requested": False, "awaiting_followup_response": True})
        elif conversation["awaiting_return_details"] and conversation["mode"] == "booking":
            dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b", user_text)
            times = re.findall(r"\b\d{2}:\d{2}\b", user_text)
            if dates: conversation["return_date"] = dates[0]
            if times: conversation["return_time"] = times[0]
            
            if not conversation["return_date"]: bot_reply = "Please specify a clear return travel date:"
            elif not conversation["return_time"]: bot_reply = "Please append a return time target (HH:MM):"
            else:
                o_n, o_c = find_station(conversation["origin"])
                d_n, d_c = find_station(conversation["destination"])
                fare_out, link_out = fetch_fare(o_c, d_c, conversation["date"], conversation["time"], conversation["adults"])
                fare_ret, link_ret = fetch_fare(d_c, o_c, conversation["return_date"], conversation["return_time"], conversation["adults"])
                bot_reply = f"Dual route ticket pipelines synchronized successfully!\n\nOutbound:\n• {fare_out}\n\nReturn:\n• {fare_ret}"
                p_link, r_link = link_out, link_ret
                conversation.update({"origin": None, "destination": None, "date": None, "time": None, "return_requested": False, "awaiting_return_details": False, "return_date": None, "return_time": None, "awaiting_followup_response": True})
        else:
            bot_reply, p_link, r_link = process_message(user_text)
        
        expert_system.log_interaction_to_db(conversation["mode"], user_text, bot_reply)
        input_box.value = ""
        deactivate_glow()
        add_bot_message(bot_reply, p_link, r_link)
        page.update()

    input_box = ft.TextField(
        hint_text="Ask about tickets, delays, or blockage incidents...",
        expand=True, color="white", text_size=16, cursor_color="white",
        border=ft.InputBorder.NONE, focused_border_width=0, bgcolor="transparent",
        on_submit=handle_send, on_focus=activate_glow, on_blur=deactivate_glow,
    )

    send_button = ft.Container(
        width=56, height=56, border_radius=28, bgcolor="#2563EB", alignment=CENTER,
        shadow=ft.BoxShadow(blur_radius=20, color="#2563EB99"),
        content=ft.Text("➜", size=26, color="white"),
        on_click=handle_send,
    )

    input_bar = ft.Container(
        content=ft.Row(controls=[calendar_button, input_box, send_button]),
        bgcolor="#17181D", border_radius=40, padding=10, margin=20,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color="#123A7A"),
    )

    background_glow = ft.Container(
        expand=True, bgcolor="#06070B",
        content=ft.Stack([ft.Container(width=850, height=850, border_radius=425, bgcolor="#001B5E", opacity=0.12, left=280, top=120)])
    )

    page.add(ft.Stack([background_glow, ft.Column(controls=[welcome_container, chat_view, input_bar], expand=True, spacing=0)], expand=True))

if __name__ == "__main__":
    ft.run(main)