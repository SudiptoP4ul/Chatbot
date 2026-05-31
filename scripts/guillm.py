import ssl
import certifi
import re
import flet as ft
from datetime import datetime, timedelta

ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

from cheapestticket import df_stations, parser, find_station, fetch_fare
from knowledgebase import predictor
from contingency import expert_system
import task3llm


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
        "user_type": "passenger",
        "contingency_session": None,
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
    }

    STAFF_WORDS = [
        'staff', 'operator', 'signaller', 'driver', 'controller', 'control',
        'manager', 'employee', 'worker', 'dispatcher', 'train crew', 'crew',
        'network', 'rail worker',
    ]
    PASSENGER_WORDS = [
        'passenger', 'traveller', 'traveler', 'customer', 'commuter',
        'public', 'visitor', 'tourist',
    ]

    def detect_user_type(text):
        t = text.lower().strip()
        if t in ('1', 's', 'staff') or any(w in t for w in STAFF_WORDS):
            return 'staff'
        if t in ('2', 'p', 'passenger') or any(w in t for w in PASSENGER_WORDS):
            return 'passenger'
        return None

    def get_or_create_session():
        if conversation["contingency_session"] is None:
            conversation["contingency_session"] = task3llm.ContingencySession(
                user_type=conversation["user_type"] or "staff"
            )
        return conversation["contingency_session"]

    CONTINGENCY_TRIGGERS = [
        "blockage", "line blocked", "track blocked", "incident", "contingency",
        "emergency", "closure", "derailment", "obstruction", "disruption plan",
        "station disruption", "dmsl", "dmfl", "umsl", "umfl", "signaller",
        "contingency plan", "service alteration", "signal box",
    ]
    DELAY_TRIGGERS = ["delay", "late", "prediction", "predict", "how late", "showing"]

    def handle_calendar_change(e):
        if date_picker.value:
            v = date_picker.value
            selected_date = f"{v.day:02d}/{v.month:02d}/{v.year}"
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
        date_picker.open = True
        page.update()

    calendar_button = ft.Container(
        content=ft.Text("📅", size=22),
        alignment=CENTER, padding=10,
        on_click=trigger_calendar_view,
        tooltip="Open Calendar Picker",
    )

    chat_view = ft.ListView(expand=True, spacing=12, auto_scroll=True, padding=20, visible=False)

    def add_user_message(message):
        chat_view.controls.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.END,
                controls=[ft.Container(
                    content=ft.Text(message, color="white", size=15),
                    bgcolor="#2563EB", border_radius=20, padding=15,
                )],
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
                controls=[ft.Container(
                    content=ft.Column(controls),
                    bgcolor="#17181D", border_radius=20, padding=15,
                )],
            )
        )
        page.update()

    def extract_and_fill_stations(text):
        clean = text.upper().strip()

        if "LONDON" in clean or "WATERLOO" in clean:
            return ["LONDON WATERLOO"]

        matched = []
        seen_crs = set()

        for _, row in df_stations.iterrows():
            crs = str(row['C']).upper().strip()
            name = str(row['N']).upper().strip()
            display_name = str(row['NAME']).strip()

            if crs in seen_crs:
                continue

            if re.search(r'\b' + re.escape(crs) + r'\b', clean):
                matched.append(display_name)
                seen_crs.add(crs)
                continue

            if re.search(r'\b' + re.escape(name) + r'\b', clean):
                matched.append(display_name)
                seen_crs.add(crs)

        return matched

    def process_message(user_text):
        t = user_text.lower()

        BOOKING_TRIGGERS = [
            "ticket", "book", "booking", "cheapest", "fare", "price", "cost",
            "travel from", "going to", "i want to go", "journey from", "train to",
            "train from", "how much", "buy", "purchase",
        ]

        if any(w in t for w in BOOKING_TRIGGERS):
            conversation["mode"] = "booking"
        elif any(w in t for w in CONTINGENCY_TRIGGERS):
            conversation["mode"] = "contingency"
        elif any(w in t for w in DELAY_TRIGGERS):
            conversation["mode"] = "delay"

        if conversation["mode"] == "contingency":
            session = get_or_create_session()
            bot_reply = session.process(user_text)
            conversation["last_asked"] = None
            return bot_reply, None, None

        stations = extract_and_fill_stations(user_text)

        if conversation["mode"] == "delay":
            if conversation["last_asked"] == "origin" and stations:
                conversation["origin"] = stations[0]
            elif conversation["last_asked"] == "destination" and stations:
                conversation["destination"] = stations[0]
            else:
                if len(stations) >= 2:
                    conversation["origin"] = stations[0]
                    conversation["destination"] = stations[1]
                elif len(stations) == 1:
                    conversation["origin"] = stations[0]

            mins = parser.num(user_text)
            if mins > 1 and mins != conversation["adults"] and "min" in t:
                conversation["delay_minutes"] = mins

            clock_time = parser.time(user_text)
            if clock_time:
                conversation["scheduled_arrival"] = clock_time

            if not conversation["origin"]:
                conversation["last_asked"] = "origin"
                return "Which station are you arriving at?", None, None
            if not conversation["scheduled_arrival"]:
                conversation["last_asked"] = "scheduled_arrival"
                return "What was the scheduled arrival time? (HH:MM)", None, None
            if not conversation["delay_minutes"]:
                conversation["last_asked"] = "delay_minutes"
                return "How many minutes late is the train currently running?", None, None

            try:
                prediction = predictor.predict(
                    conversation["delay_minutes"],
                    conversation["scheduled_arrival"],
                )
                station_label = f" at {conversation['origin']}" if conversation.get("origin") else ""
                reply = f"Delay prediction{station_label}:\n{prediction}"
            except Exception as e:
                reply = f"Delay prediction unavailable: {e}"

            conversation.update({
                "origin": None, "scheduled_arrival": None,
                "delay_minutes": None, "awaiting_followup_response": True,
            })
            return reply, None, None

        upper_text = user_text.upper()
        to_match = re.search(r'\b(TO|GO TO|GOING TO)\b\s*([A-Z\s]+)', upper_text)
        from_match = re.search(r'\b(FROM|DEPARTING FROM)\b\s*([A-Z\s]+)', upper_text)
        extracted_dest, extracted_orig = None, None

        if to_match:
            _, d_code = find_station(to_match.group(2))
            if d_code:
                extracted_dest = next(
                    (s for s in stations if find_station(s)[1] == d_code), None
                )
        if from_match:
            _, o_code = find_station(from_match.group(2))
            if o_code:
                extracted_orig = next(
                    (s for s in stations if find_station(s)[1] == o_code), None
                )

        if conversation["last_asked"] == "origin" and stations:
            conversation["origin"] = stations[0]
        elif conversation["last_asked"] == "destination" and stations:
            conversation["destination"] = stations[0]
        else:
            if extracted_orig:
                conversation["origin"] = extracted_orig
            if extracted_dest:
                conversation["destination"] = extracted_dest
            if len(stations) >= 2 and not conversation["origin"] and not conversation["destination"]:
                conversation["origin"] = stations[0]
                conversation["destination"] = stations[1]
            elif len(stations) == 1 and not conversation["origin"] and not conversation["destination"]:
                conversation["destination"] = stations[0]

        extracted_date = parser.date(user_text)
        if extracted_date:
            conversation["date"] = extracted_date
        extracted_time = parser.time(user_text)
        if extracted_time:
            conversation["time"] = extracted_time

        p_count = parser.extract_passenger_count(user_text)
        if p_count is not None:
            conversation["adults"] = p_count

        if any(w in t for w in ["return", "round trip", "two way"]):
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
            reply = (
                f"Ticket endpoints synced!\n\nOutbound Journey:\n{fare_out}\n\n"
                f"Return Journey:\n{fare_ret}\n\nAnything else I can help with?"
            )
            conversation.update({
                "origin": None, "destination": None, "date": None, "time": None,
                "return_requested": False, "awaiting_return_details": False,
                "return_date": None, "return_time": None,
                "awaiting_followup_response": True,
            })
            return reply, link_out, link_ret

        if conversation["return_requested"] and (not conversation["return_date"] or not conversation["return_time"]):
            conversation["awaiting_return_details"] = True
            return "Please specify a return travel date and time (Use calendar picker or enter DD/MM/YYYY HH:MM):", None, None

        o_n, o_c = find_station(conversation["origin"])
        d_n, d_c = find_station(conversation["destination"])
        fare_text, booking_url = fetch_fare(o_c, d_c, conversation["date"], conversation["time"], conversation["adults"])

        reply = (
            f"Ticket found!\nRoute: {o_n} to {d_n}\n"
            f"{conversation['adults']} Adult passenger(s)\n{fare_text}\n\n"
            f"Would you like to add a return journey? (Yes/No)"
        )
        return reply, booking_url, None

    def activate_glow(e=None):
        input_bar.shadow = ft.BoxShadow(spread_radius=2, blur_radius=40, color="#2563EB", offset=ft.Offset(0, 0))
        page.update()

    def deactivate_glow(e=None):
        if input_box.value.strip():
            return
        input_bar.shadow = ft.BoxShadow(spread_radius=1, blur_radius=20, color="#123A7A", offset=ft.Offset(0, 0))
        page.update()

    def handle_send(e=None):
        user_text = input_box.value.strip()
        if not user_text:
            return

        if welcome_container.visible:
            welcome_container.visible = False
            chat_view.visible = True

        add_user_message(user_text)
        input_box.value = ""
        deactivate_glow()

        bot_reply, p_link, r_link = "", None, None

        detected = detect_user_type(user_text)
        if detected:
            conversation["user_type"] = detected
            if conversation["contingency_session"] is not None:
                conversation["contingency_session"].user_type = detected

        if conversation["awaiting_followup_response"]:
            has_keywords = any(w in user_text.lower() for w in [
                "delay", "late", "predict", "showing", "ticket", "book",
                "blockage", "incident", "emergency", "disruption",
            ])
            if has_keywords:
                conversation["awaiting_followup_response"] = False
            else:
                if user_text.lower().strip() in ["no", "nope", "nothing", "thank you", "thanks", "bye", "n"]:
                    bot_reply = "Session cleared. Have safe travels!"
                    if conversation["contingency_session"]:
                        conversation["contingency_session"].reset()
                    conversation.update({
                        "origin": None, "destination": None, "date": None, "time": None,
                        "return_requested": False, "awaiting_return_details": False,
                        "awaiting_followup_response": False, "mode": "booking",
                        "delay_minutes": None, "scheduled_arrival": None,
                    })
                    add_bot_message(bot_reply, None, None)
                    return

        if conversation["return_requested"] and not conversation["awaiting_return_details"] \
                and not conversation["return_date"] and conversation["mode"] == "booking":
            if user_text.lower() in ["yes", "y", "yeah", "sure"]:
                conversation["awaiting_return_details"] = True
                bot_reply = "Please specify the return trip date (or select via calendar widget):"
            else:
                bot_reply = "No problem. Anything else I can help with?"
                conversation.update({
                    "origin": None, "destination": None, "date": None, "time": None,
                    "return_requested": False, "awaiting_followup_response": True,
                })
            add_bot_message(bot_reply, None, None)
            return

        if conversation["awaiting_return_details"] and conversation["mode"] == "booking":
            dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b", user_text)
            times = re.findall(r"\b\d{2}:\d{2}\b", user_text)
            if dates:
                conversation["return_date"] = dates[0]
            if times:
                conversation["return_time"] = times[0]

            if not conversation["return_date"]:
                bot_reply = "Please specify a clear return travel date:"
            elif not conversation["return_time"]:
                bot_reply = "Please specify a return time (HH:MM):"
            else:
                o_n, o_c = find_station(conversation["origin"])
                d_n, d_c = find_station(conversation["destination"])
                fare_out, link_out = fetch_fare(o_c, d_c, conversation["date"], conversation["time"], conversation["adults"])
                fare_ret, link_ret = fetch_fare(d_c, o_c, conversation["return_date"], conversation["return_time"], conversation["adults"])
                bot_reply = (
                    f"Both journeys sorted!\n\nOutbound:\n{fare_out}\n\nReturn:\n{fare_ret}"
                )
                p_link, r_link = link_out, link_ret
                conversation.update({
                    "origin": None, "destination": None, "date": None, "time": None,
                    "return_requested": False, "awaiting_return_details": False,
                    "return_date": None, "return_time": None,
                    "awaiting_followup_response": True,
                })
            add_bot_message(bot_reply, p_link, r_link)
            return

        bot_reply, p_link, r_link = process_message(user_text)
        add_bot_message(bot_reply, p_link, r_link)

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

    welcome_container = ft.Container(
        expand=True, alignment=CENTER,
        content=ft.Column(
            [
                ft.Text("How can I help you today?", size=36, color="#E5E7EB", weight=ft.FontWeight.W_300),
                ft.Text("Live Ticket Booking, Delay Prediction & Integrated Operational Contingency Expert", size=16, color="#6B7280"),
                ft.Text("Ask about tickets, delays, disruptions, or contingency plans.", size=14, color="#9CA3AF"),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    background_glow = ft.Container(
        expand=True, bgcolor="#06070B",
        content=ft.Stack([
            ft.Container(
                width=850, height=850, border_radius=425,
                bgcolor="#001B5E", opacity=0.12, left=280, top=120,
            )
        ]),
    )

    page.add(ft.Stack(
        [background_glow, ft.Column(
            controls=[welcome_container, chat_view, input_bar],
            expand=True, spacing=0,
        )],
        expand=True,
    ))


if __name__ == "__main__":
    ft.run(main)
