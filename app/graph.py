import json
import re
from typing import TypedDict, List, Dict, Any
import httpx
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

try:
    from app.config import GROQ_API_KEY, TAVILY_API_KEY, AVIATIONSTACK_API_KEY, DEFAULT_ORIGIN_IATA
except ImportError:
    from config import GROQ_API_KEY, TAVILY_API_KEY, AVIATIONSTACK_API_KEY, DEFAULT_ORIGIN_IATA

class TripState(TypedDict):
    source: str
    destination: str
    departure_date: str
    num_days: int
    travelers: int
    preferences: str
    places_covered: str
    available_flights: List[Dict[str, Any]]
    selected_flight: Dict[str, Any]
    itinerary_days: List[Dict[str, Any]]
    itinerary_markdown: str
    budget_data: Dict[str, Any]
    flights: str
    hotels: str

llm = ChatGroq(model_name='openai/gpt-oss-20b', api_key=GROQ_API_KEY, temperature=0.3)
tavily_search = TavilySearchResults(max_results=3, api_key=TAVILY_API_KEY)

def extract_json_safely(text: str):
    """Safely extracts JSON from an LLM response with loose strictness."""
    text = text.strip()
    if '```json' in text:
        text = text.split('```json')[1].split('```')[0].strip()
    elif '```' in text:
        text = text.split('```')[1].split('```')[0].strip()
    
    # Try finding array brackets [ ... ]
    sb = text.find('[')
    eb = text.rfind(']')
    if sb != -1 and eb != -1 and eb > sb:
        try:
            return json.loads(text[sb:eb+1], strict=False)
        except Exception:
            pass

    # Try finding object braces { ... }
    sc = text.find('{')
    ec = text.rfind('}')
    if sc != -1 and ec != -1 and ec > sc:
        try:
            return json.loads(text[sc:ec+1], strict=False)
        except Exception:
            pass

    return json.loads(text, strict=False)

def generate_default_timetable(day_title: str, overnight: str, landing_time: str = None, flight_name: str = "Flight"):
    """Generates hour-by-hour schedule tailored to landing time if on Day 1."""
    if landing_time:
        return [
            {"time": landing_time, "activity": f"{flight_name} touches down / Arrival at airport terminal"},
            {"time": "45 mins after arrival", "activity": "Baggage collection, airport exit & meetup with private cab driver"},
            {"time": "1.5 hrs after arrival", "activity": "Transfer to hotel, check-in & relax/freshen up"},
            {"time": "Afternoon / Evening", "activity": f"Local orientation tour, visits to {day_title} and cultural highlights"},
            {"time": "08:00 PM", "activity": "Traditional dinner at authentic local restaurant"},
            {"time": "10:00 PM", "activity": f"Return to hotel for comfortable overnight stay in {overnight}"}
        ]
    return [
        {"time": "08:00 AM", "activity": f"Breakfast and preparation for {day_title}"},
        {"time": "09:30 AM", "activity": "Pickup by private AC vehicle / Departure for sightseeing"},
        {"time": "11:00 AM", "activity": "Guided tour of key monuments and cultural attractions"},
        {"time": "01:00 PM", "activity": "Lunch at highly-rated local authentic restaurant"},
        {"time": "03:30 PM", "activity": "Afternoon exploration, photography, and artisan market visits"},
        {"time": "06:00 PM", "activity": "Sunset viewpoint or cultural evening activity"},
        {"time": "08:00 PM", "activity": f"Dinner followed by transfer to hotel for overnight stay in {overnight}"}
    ]

def generate_curated_circuit_itinerary(dest: str, src: str, days: int, landing_time: str = None, flight_name: str = "Flight"):
    """Provides high-quality realistic itinerary for popular circuits if LLM parsing hits a glitch."""
    dest_lower = dest.lower()
    t_land = landing_time or "09:15 AM"
    
    if "golden triangle" in dest_lower or ("delhi" in dest_lower and "agra" in dest_lower) or "jaipur" in dest_lower:
        full_plan = [
            {
                "day": 1,
                "route": f"Day 1 : {src} to Delhi",
                "title": "Delhi Arrival & Heritage City Tour",
                "description": f"Flight {flight_name} lands at Delhi Airport at {t_land}. Pickup by private AC cab and transfer to hotel. Afternoon visit to India Gate, Lotus Temple, and the magnificent Akshardham Temple with evening light & sound show. Overnight stay at Delhi.",
                "overnight": "Delhi",
                "timetable": [
                    {"time": t_land, "activity": f"Flight {flight_name} touches down at Delhi Airport (DEL)"},
                    {"time": "10:15 AM", "activity": "Airport pickup and transfer to hotel in private AC vehicle"},
                    {"time": "11:30 AM", "activity": "Hotel check-in and freshen up"},
                    {"time": "01:00 PM", "activity": "Lunch at Connaught Place authentic restaurant"},
                    {"time": "02:45 PM", "activity": "Guided visit to India Gate, War Memorial, and Lotus Temple"},
                    {"time": "06:00 PM", "activity": "Visit Akshardham Temple and musical fountain show"},
                    {"time": "08:30 PM", "activity": "Dinner and overnight stay in Delhi"}
                ]
            },
            {
                "day": 2,
                "route": "Day 2 : Delhi - Mathura - Vrindavan - Agra",
                "title": "Delhi to Agra via Krishna Janmabhoomi",
                "description": "Morning drive to Agra via Yamuna Expressway. En-route stop at Mathura to visit Shri Krishna Janmabhoomi and Banke Bihari Temple in Vrindavan. Arrive in Agra, check into hotel. Late afternoon sunset visit to the world-famous Taj Mahal. Overnight stay in Agra.",
                "overnight": "Agra",
                "timetable": [
                    {"time": "07:30 AM", "activity": "Buffet breakfast and checkout from Delhi hotel"},
                    {"time": "08:30 AM", "activity": "Drive to Mathura via Yamuna Expressway (2.5 hrs)"},
                    {"time": "11:00 AM", "activity": "Visit Shri Krishna Janmabhoomi Temple in Mathura"},
                    {"time": "01:00 PM", "activity": "Lunch at traditional Brijwasi restaurant"},
                    {"time": "02:30 PM", "activity": "Proceed to Agra and hotel check-in"},
                    {"time": "04:30 PM", "activity": "Guided tour of the Taj Mahal during golden sunset hour"},
                    {"time": "08:00 PM", "activity": "Mughlai specialty dinner and overnight stay in Agra"}
                ]
            },
            {
                "day": 3,
                "route": "Day 3 : Agra - Fatehpur Sikri - Jaipur",
                "title": "Agra Fort & Drive to Jaipur via Fatehpur Sikri",
                "description": "Morning visit to the imposing Agra Fort. Drive to Jaipur (Pink City) with an en-route visit to the UNESCO World Heritage site of Fatehpur Sikri (Buland Darwaza). Arrive in Jaipur, check into hotel. Evening visit to Chokhi Dhani ethnic resort for Rajasthani cultural dance and dinner. Overnight stay in Jaipur.",
                "overnight": "Jaipur",
                "timetable": [
                    {"time": "08:00 AM", "activity": "Breakfast and visit to Agra Fort & Diwan-i-Khas"},
                    {"time": "10:30 AM", "activity": "Drive towards Jaipur with stop at Fatehpur Sikri"},
                    {"time": "12:00 PM", "activity": "Explore Buland Darwaza and Salim Chishti Dargah"},
                    {"time": "01:30 PM", "activity": "Lunch at highway heritage motel"},
                    {"time": "04:30 PM", "activity": "Arrive in Jaipur and check in to hotel"},
                    {"time": "07:00 PM", "activity": "Evening cultural show & traditional Rajasthani dinner at Chokhi Dhani"},
                    {"time": "10:30 PM", "activity": "Overnight stay in Jaipur"}
                ]
            },
            {
                "day": 4,
                "route": f"Day 4 : Jaipur - {src} / Delhi Airport",
                "title": "Jaipur Palaces & Departure Transfer",
                "description": f"Morning visit to Amber Fort with optional jeep ride, photo stop at Jal Mahal, and tour of City Palace and Hawa Mahal. Afternoon drive back to Delhi / Jaipur airport for your onward flight to {src}.",
                "overnight": "Departure",
                "timetable": [
                    {"time": "08:00 AM", "activity": "Breakfast and hotel checkout"},
                    {"time": "09:00 AM", "activity": "Visit Amber Fort, Sheesh Mahal and photo stop at Jal Mahal"},
                    {"time": "11:30 AM", "activity": "Explore City Palace and iconic Hawa Mahal (Palace of Winds)"},
                    {"time": "01:00 PM", "activity": "Lunch and quick shopping for Jaipur handicrafts & blue pottery"},
                    {"time": "02:30 PM", "activity": "Transfer to airport / railway station for onward departure"},
                    {"time": "06:30 PM", "activity": "Board departure flight back home with fond memories"}
                ]
            }
        ]
        return full_plan[:days] if days <= len(full_plan) else full_plan

    elif "char dham" in dest_lower or "kedarnath" in dest_lower or "badrinath" in dest_lower:
        dham_plan = [
            {"day": 1, "route": f"Day 1 : {src} to Haridwar", "title": "Delhi to Haridwar & Ganga Aarti", "description": f"Arrival from {src}. Drive to holy city of Haridwar. Evening attend world-famous Ganga Aarti at Har Ki Pauri. Overnight in Haridwar.", "overnight": "Haridwar", "timetable": generate_default_timetable("Haridwar Arrival", "Haridwar", t_land, flight_name)},
            {"day": 2, "route": "Day 2 : Haridwar to Barkot", "title": "Scenic Mountain Drive to Barkot", "description": "Morning drive to Barkot via Mussoorie and Kempty Falls. Check in to scenic mountain resort. Overnight stay at Barkot.", "overnight": "Barkot", "timetable": generate_default_timetable("Barkot Drive", "Barkot")},
            {"day": 3, "route": "Day 3 : Barkot - Yamunotri - Barkot", "title": "First Dham: Holy Yamunotri Darshan", "description": "Early morning drive to Janki Chatti. Trek/Pony to Yamunotri Temple. Holy dip in Surya Kund, Divya Shila pooja, and temple darshan. Return to Barkot for overnight stay.", "overnight": "Barkot", "timetable": generate_default_timetable("Yamunotri Darshan", "Barkot")},
            {"day": 4, "route": "Day 4 : Barkot to Uttarkashi", "title": "Drive to Uttarkashi & Kashi Vishwanath", "description": "Drive to Uttarkashi along the Bhagirathi River. Visit the ancient Kashi Vishwanath Temple and Shakti Temple. Overnight stay at Uttarkashi.", "overnight": "Uttarkashi", "timetable": generate_default_timetable("Uttarkashi Vishwanath", "Uttarkashi")},
            {"day": 5, "route": "Day 5 : Uttarkashi - Gangotri - Uttarkashi", "title": "Second Dham: Sacred Gangotri Darshan", "description": "Morning drive through picturesque Harsil Valley to Gangotri. Holy dip in Bhagirathi river and Gangotri Temple Darshan. Return to Uttarkashi for overnight stay.", "overnight": "Uttarkashi", "timetable": generate_default_timetable("Gangotri Darshan", "Uttarkashi")},
            {"day": 6, "route": "Day 6 : Uttarkashi to Guptkashi", "title": "Scenic Valley Drive to Guptkashi", "description": "Scenic drive to Guptkashi (base for Kedarnath). Visit Ardh Narishwar Temple. Check in and overnight stay at Guptkashi.", "overnight": "Guptkashi", "timetable": generate_default_timetable("Guptkashi Base", "Guptkashi")},
            {"day": 7, "route": "Day 7 : Guptkashi to Kedarnath", "title": "Third Dham: Kedarnath Temple Darshan", "description": "Transfer to Phata/Sirsi for Helicopter or trek to Kedarnath. Check in to ashram/hotel near temple. Attend the divine evening Kedarnath Aarti amidst Himalayan peaks. Overnight stay in Kedarnath.", "overnight": "Kedarnath", "timetable": generate_default_timetable("Kedarnath Darshan", "Kedarnath")},
            {"day": 8, "route": "Day 8 : Kedarnath to Badrinath", "title": "Descent & Journey to Badrinath", "description": "Morning darshan of Baba Kedar. Return to Guptkashi and proceed via Chopta valley and Joshimath to Badrinath. Check in and overnight in Badrinath.", "overnight": "Badrinath", "timetable": generate_default_timetable("Journey to Badrinath", "Badrinath")},
            {"day": 9, "route": "Day 9 : Badrinath - Mana - Rudraprayag", "title": "Fourth Dham: Badrinath Darshan & Mana Village", "description": "Early morning holy bath in Tapt Kund and Badrinath Temple Darshan. Visit Mana Village (last Indian village), Vyas Gufa, and Bhim Pul. Drive to Rudraprayag for overnight stay.", "overnight": "Rudraprayag", "timetable": generate_default_timetable("Badrinath Darshan", "Rudraprayag")},
            {"day": 10, "route": f"Day 10 : Rudraprayag - Rishikesh - {src}", "title": "Rishikesh Ram Jhula & Onward Departure", "description": f"Morning drive to Rishikesh. Visit Ram Jhula, Laxman Jhula, and Triveni Ghat. Transfer to airport / station for onward return to {src}.", "overnight": "Departure", "timetable": generate_default_timetable("Rishikesh Departure", "Departure")}
        ]
        return dham_plan[:days] if days <= len(dham_plan) else dham_plan

    # General / Custom Tour Fallback
    res = []
    for d in range(1, days + 1):
        if d == 1:
            res.append({
                "day": 1,
                "route": f"Day 1 : {src} to {dest}",
                "title": f"Arrival at {dest} & Local Orientation",
                "description": f"Flight {flight_name} lands at {t_land}. Airport pickup in private vehicle, hotel check-in, and afternoon exploration of {dest}'s primary sights. Overnight stay in {dest}.",
                "overnight": dest,
                "timetable": generate_default_timetable(f"{dest} Day 1", dest, t_land, flight_name)
            })
        elif d == days:
            res.append({
                "day": d,
                "route": f"Day {d} : {dest} - Departure",
                "title": f"Final Sightseeing & Departure to {src}",
                "description": f"Morning breakfast and souvenir shopping in {dest}. Afternoon transfer to airport / transit station for onward journey to {src}.",
                "overnight": "Departure",
                "timetable": generate_default_timetable(f"{dest} Departure", "Departure")
            })
        else:
            res.append({
                "day": d,
                "route": f"Day {d} : {dest} Sightseeing Tour",
                "title": f"Exploring Cultural Highlights of {dest}",
                "description": f"Full-day guided exploration of major landmarks, temples, and culinary delights in {dest}. Evening sunset views and authentic dinner. Overnight stay in {dest}.",
                "overnight": dest,
                "timetable": generate_default_timetable(f"{dest} Day {d}", dest)
            })
    return res

async def destination_agent(state: TripState):
    """Analyzes source and destination/circuit and identifies key stops."""
    src = state.get("source") or "Delhi"
    dest = state.get("destination") or "Golden Triangle"
    days = state.get("num_days", 4)
    pref = state.get("preferences", "")
    
    prompt = f"""You are a professional travel circuit planner.
Travel Details:
- Source City: {src}
- Destination / Tour Circuit: {dest}
- Duration: {days} Days
- Extra Preferences: {pref}

Task:
Identify the exact circuit route and major places/stops to be visited.
Example:
- Golden Triangle -> Delhi - Mathura - Agra - Fatehpur Sikri - Jaipur - Delhi
- Char Dham -> Haridwar - Barkot (Yamunotri) - Uttarkashi (Gangotri) - Guptkashi - Kedarnath - Badrinath - Rishikesh

Provide ONLY a concise 1-2 sentence summary of the route and key places."""

    res = await llm.ainvoke(prompt)
    places = res.content.strip().strip('"')
    return {"places_covered": places}

async def flight_search_agent(state: TripState):
    """
    Searches available flights / primary transit from source to destination hub on the departure date.
    Returns distinct options (Morning, Afternoon, Evening) with departure and landing times.
    """
    src = state.get("source") or "Delhi"
    dest = state.get("destination") or "Golden Triangle"
    dep_date = state.get("departure_date") or "2026-11-20"

    prompt = f"""Provide 3 realistic commercial flight or transit options from {src} to {dest} on {dep_date}.
Include:
1. A morning flight (landing between 08:30 AM - 10:30 AM)
2. An afternoon flight (landing between 01:00 PM - 03:00 PM)
3. An evening flight (landing between 06:30 PM - 08:30 PM)

Return ONLY a valid JSON array of objects with schema:
[
  {{
    "flight_id": "FL-1",
    "airline": "IndiGo 6E-204",
    "departure_time": "06:30 AM",
    "landing_time": "09:15 AM",
    "duration": "2h 45m",
    "price_inr": 4850,
    "slot": "Morning Flight"
  }}
]"""

    available_flights = []
    try:
        res = await llm.ainvoke(prompt)
        available_flights = extract_json_safely(res.content)
        if not isinstance(available_flights, list):
            available_flights = []
    except Exception:
        available_flights = []

    if not available_flights:
        # Fallback flight schedule
        available_flights = [
            {
                "flight_id": "FL-1",
                "airline": "IndiGo 6E-204",
                "departure_time": "06:30 AM",
                "landing_time": "09:15 AM",
                "duration": "2h 45m",
                "price_inr": 4850,
                "slot": "Morning Flight"
            },
            {
                "flight_id": "FL-2",
                "airline": "Air India AI-101",
                "departure_time": "10:45 AM",
                "landing_time": "01:30 PM",
                "duration": "2h 45m",
                "price_inr": 5420,
                "slot": "Afternoon Flight"
            },
            {
                "flight_id": "FL-3",
                "airline": "Vistara UK-812",
                "departure_time": "04:45 PM",
                "landing_time": "07:30 PM",
                "duration": "2h 45m",
                "price_inr": 6120,
                "slot": "Evening Flight"
            }
        ]

    default_selected = available_flights[0] if available_flights else {}
    return {
        "available_flights": available_flights,
        "selected_flight": default_selected
    }

async def review_agent(state: TripState):
    """
    Human-in-the-Loop review: Halts execution to let the user select a flight on that day
    and approve/customize tour stops before generating the detailed schedule.
    """
    places = state.get("places_covered", "")
    dest = state.get("destination", "")
    src = state.get("source", "")
    days = state.get("num_days", 4)
    dep_date = state.get("departure_date", "")
    flights = state.get("available_flights", [])
    
    feedback = interrupt({
        "source": src,
        "destination": dest,
        "departure_date": dep_date,
        "num_days": days,
        "places_covered": places,
        "available_flights": flights,
        "prompt": "Select a flight and review tour stops."
    })
    
    # Process user feedback
    final_places = places
    selected_flight = state.get("selected_flight", flights[0] if flights else {})

    if isinstance(feedback, dict):
        if "places_covered" in feedback and feedback["places_covered"]:
            final_places = feedback["places_covered"]
        if "selected_flight" in feedback and feedback["selected_flight"]:
            selected_flight = feedback["selected_flight"]
    elif isinstance(feedback, str) and feedback.strip():
        # Check if feedback is a JSON string
        try:
            parsed = json.loads(feedback)
            if isinstance(parsed, dict):
                if "places_covered" in parsed and parsed["places_covered"]:
                    final_places = parsed["places_covered"]
                if "selected_flight" in parsed and parsed["selected_flight"]:
                    selected_flight = parsed["selected_flight"]
        except Exception:
            if feedback.lower() not in ['approve', 'ok', 'yes', 'approved', '']:
                final_places = feedback.strip()

    return {
        "places_covered": final_places,
        "selected_flight": selected_flight
    }

async def itinerary_agent(state: TripState):
    """
    Generates structured day-by-day itinerary with an hourly timetable.
    Day 1 timetable is tailored specifically to the flight's landing time!
    """
    src = state.get("source") or "Delhi"
    dest = state.get("destination") or "Golden Triangle"
    route = state.get("places_covered") or dest
    days = state.get("num_days", 4)
    dep_date = state.get("departure_date") or "2026-11-20"
    travelers = state.get("travelers", 2)
    pref = state.get("preferences", "")
    
    # Selected flight & landing time details
    sel_flight = state.get("selected_flight") or {}
    flight_name = sel_flight.get("airline", "Scheduled Flight")
    dep_time = sel_flight.get("departure_time", "06:30 AM")
    landing_time = sel_flight.get("landing_time", "09:15 AM")
    flight_fare = sel_flight.get("price_inr", 4800)

    prompt = f"""You are a master tour designer.
Create a complete day-by-day travel itinerary with hour-by-hour timetables for:
- Source: {src}
- Destination / Circuit: {dest}
- Route & Places: {route}
- Departure Date: {dep_date}
- Number of Days: {days} Days
- Travelers: {travelers}
- Specific Notes: {pref}

✈️ FLIGHT & ARRIVAL DETAILS FOR DAY 1:
- Airline / Flight: {flight_name}
- Departure Time: {dep_time}
- Landing Time: {landing_time}

CRITICAL REQUIREMENT FOR DAY 1:
The traveler's flight lands at {landing_time} on Day 1.
Day 1's timetable MUST start directly at {landing_time} with:
- "{landing_time}": "Flight {flight_name} lands at {dest} airport / terminal"
- Next item (approx 45m later): "Baggage claim & pickup by private AC cab / transfer to hotel"
- Next item: "Hotel check-in & freshen up"
- Followed by appropriate afternoon and evening sightseeing based on this arrival time!

Days 2 through {days} should follow standard morning-to-night tour schedules.

Return ONLY a valid JSON array of objects with schema:
[
  {{
    "day": 1,
    "route": "Day 1 : Arrival at {dest}",
    "title": "{dest} Arrival & Afternoon Tour",
    "description": "After landing at {landing_time} on flight {flight_name}, proceed with hotel check-in and evening sightseeing...",
    "overnight": "{dest}",
    "timetable": [
      {{"time": "{landing_time}", "activity": "Flight {flight_name} touches down at airport terminal"}},
      {{"time": "10:15 AM", "activity": "Baggage claim, pickup by private driver & transfer to hotel"}},
      {{"time": "11:30 AM", "activity": "Hotel check-in & freshen up"}},
      {{"time": "01:00 PM", "activity": "Lunch at local restaurant"}},
      {{"time": "03:00 PM", "activity": "Sightseeing at key monuments"}},
      {{"time": "07:30 PM", "activity": "Evening leisure & dinner"}},
      {{"time": "10:00 PM", "activity": "Overnight stay at hotel"}}
    ]
  }}
]"""

    res = await llm.ainvoke(prompt)
    raw_content = res.content.strip()
    itinerary_days = []
    
    try:
        parsed = extract_json_safely(raw_content)
        if isinstance(parsed, list) and len(parsed) > 0:
            itinerary_days = parsed
        elif isinstance(parsed, dict) and "itinerary" in parsed:
            itinerary_days = parsed["itinerary"]
    except Exception:
        itinerary_days = []

    dest_lower = dest.lower()
    is_popular_circuit = any(k in dest_lower for k in [
        "golden triangle", "char dham", "kedarnath", "badrinath"
    ])

    # Enforce rich, authentic circuit details instead of generic LLM placeholders
    is_generic = False
    if itinerary_days:
        for d in itinerary_days:
            desc = d.get("description", "").lower()
            title = d.get("title", "").lower()
            if "exploration of" in desc or "exploration of" in title or (dest_lower in desc and len(desc) < 90):
                is_generic = True
                break

    if is_popular_circuit or not itinerary_days or is_generic or not isinstance(itinerary_days, list):
        itinerary_days = generate_curated_circuit_itinerary(dest, src, int(days), landing_time, flight_name)

    # Ensure timetable is present in every day object
    for d in itinerary_days:
        d_num = d.get("day", 1)
        t_list = d.get("timetable", [])
        if not t_list or not isinstance(t_list, list):
            d["timetable"] = generate_default_timetable(d.get("title", dest), d.get("overnight", dest), landing_time if d_num == 1 else None, flight_name)
        else:
            clean_t = []
            for item in t_list:
                if isinstance(item, dict):
                    clean_t.append(item)
                elif isinstance(item, str):
                    if " - " in item:
                        t_parts = item.split(" - ", 1)
                        clean_t.append({"time": t_parts[0].strip(), "activity": t_parts[1].strip()})
                    else:
                        clean_t.append({"time": "Scheduled", "activity": item.strip()})
            d["timetable"] = clean_t if clean_t else generate_default_timetable(d.get("title", dest), d.get("overnight", dest), landing_time if d_num == 1 else None, flight_name)

    # Build flights text summary
    flights_summary = f"""- Selected Flight: {flight_name}
- Route: {src} ➔ {dest}
- Departure: {dep_time} | Landing: {landing_time}
- Flight Duration: {sel_flight.get('duration', '2h 45m')}
- Estimated Airfare: ₹{flight_fare:,} per traveler
- Note: Day 1 itinerary schedule commences directly upon {landing_time} landing."""

    # Build markdown summary for easy reading and export
    md_lines = [
        f"# {days}-Day Itinerary for {dest} (Starting from {src})",
        f"**Selected Flight:** {flight_name} (Departs: {dep_time} ➔ Lands: {landing_time})\n"
    ]
    for d in itinerary_days:
        route_text = d.get("route") or f"Day {d.get('day', 1)}"
        md_lines.append(f"### {route_text}")
        md_lines.append(f"**{d.get('title', '')}**")
        md_lines.append(f"{d.get('description', '')}\n")
        
        md_lines.append("#### 🕒 Daily Timetable:")
        for t_item in d.get("timetable", []):
            md_lines.append(f"- **{t_item.get('time', '')}**: {t_item.get('activity', '')}")
        md_lines.append(f"\n*Overnight Stay:* **{d.get('overnight', 'Hotel')}**\n")

    itinerary_markdown = "\n".join(md_lines)
    return {
        "itinerary_days": itinerary_days,
        "itinerary_markdown": itinerary_markdown,
        "flights": flights_summary
    }

async def budget_agent(state: TripState):
    """Calculates realistic budget incorporating selected flight prices."""
    src = state.get("source") or "Delhi"
    dest = state.get("destination") or "Golden Triangle"
    days = state.get("num_days", 4)
    travelers = state.get("travelers", 2)
    route = state.get("places_covered", dest)
    sel_flight = state.get("selected_flight") or {}
    flight_cost_total = sel_flight.get("price_inr", 4800) * travelers

    prompt = f"""Estimate realistic mid-range trip budget in INR for:
- Route: {src} to {dest} ({route})
- Duration: {days} Days
- Travelers: {travelers} Persons
- Flights/Airfare: Total ₹{flight_cost_total:,} for {travelers} travelers.

Return ONLY a valid JSON object in this schema:
{{
  "total_inr": 48000,
  "per_person_inr": 24000,
  "breakdown": {{
    "accommodation_inr": 20000,
    "transportation_inr": 18000,
    "food_and_activities_inr": 10000
  }},
  "notes": "Includes selected flights ({sel_flight.get('airline', 'Flight')}), private AC vehicle, 3-star/4-star hotels, and entry tickets."
}}"""

    res = await llm.ainvoke(prompt)
    budget_data = {}
    try:
        budget_data = extract_json_safely(res.content)
        if not isinstance(budget_data, dict) or "total_inr" not in budget_data:
            budget_data = {}
    except Exception:
        budget_data = {}

    if not budget_data:
        base_cost = int(days) * int(travelers) * 4500
        total_inr = base_cost + flight_cost_total
        budget_data = {
            "total_inr": total_inr,
            "per_person_inr": total_inr // max(int(travelers), 1),
            "breakdown": {
                "accommodation_inr": int(base_cost * 0.50),
                "transportation_inr": flight_cost_total + int(base_cost * 0.25),
                "food_and_activities_inr": int(base_cost * 0.25)
            },
            "notes": f"Includes {sel_flight.get('airline', 'flight')} airfare and private AC vehicle."
        }

    return {"budget_data": budget_data}

def generate_curated_hotels(dest: str, route: str) -> str:
    """Returns hardcoded curated hotel recommendations for popular circuits."""
    dest_lower = dest.lower()

    if "golden triangle" in dest_lower or ("delhi" in dest_lower and "agra" in dest_lower) or "jaipur" in dest_lower:
        return """• Delhi — The Lalit New Delhi ⭐⭐⭐⭐⭐ (Barakhamba Ave, Connaught Place)
  Tariff: ₹7,500–₹12,000/night | Pool, Spa, Multi-cuisine restaurants, 24hr room service

• Agra — Trident Hotel Agra ⭐⭐⭐⭐⭐ (Taj East Gate Road, Tajganj)
  Tariff: ₹6,500–₹9,500/night | Taj Mahal views, Pool, Mughal garden, Fine dining

• Jaipur — ITC Rajputana ⭐⭐⭐⭐⭐ (Palace Road, Jaipur)
  Tariff: ₹7,000–₹11,000/night | Heritage décor, Pool, Rajasthani cuisine, Spa"""

    elif "char dham" in dest_lower or "kedarnath" in dest_lower or "badrinath" in dest_lower:
        return """• Haridwar — Hotel Haveli Hari Ganga ⭐⭐⭐⭐ (28 Ramghat, Haridwar)
  Tariff: ₹3,500–₹6,500/night | Ganges view, Yoga pavilion, Heritage rooms

• Kedarnath / Guptkashi — Hotel Ukhimath ⭐⭐⭐ (Guptkashi)
  Tariff: ₹2,500–₹4,500/night | Mountain views, Hot water, Vegetarian meals

• Badrinath — Hotel Snow Crest Inn ⭐⭐⭐ (Near Badrinath Temple)
  Tariff: ₹2,000–₹4,000/night | Temple proximity, Clean rooms, Jain-friendly kitchen"""

    elif "kerala" in dest_lower or "backwater" in dest_lower or "munnar" in dest_lower:
        return """• Alleppey (Backwaters) — Houseboat Cruise ⭐⭐⭐⭐ (Kerala Backwaters)
  Tariff: ₹8,000–₹15,000/night | All-inclusive houseboat, Kerala cuisine, Sunset cruise

• Munnar — The Windermere Estate ⭐⭐⭐⭐ (Pothamedu, Munnar)
  Tariff: ₹5,500–₹9,000/night | Tea estate views, Colonial bungalows, Trekking

• Kovalam — Vivanta Kovalam ⭐⭐⭐⭐⭐ (Kovalam Beach, Trivandrum)
  Tariff: ₹9,000–₹16,000/night | Beachfront, Infinity pool, Ayurvedic spa"""

    elif "rajasthan" in dest_lower or ("udaipur" in dest_lower or "jodhpur" in dest_lower):
        return """• Jaipur — Rambagh Palace (Taj) ⭐⭐⭐⭐⭐ (Bhawani Singh Road)
  Tariff: ₹18,000–₹35,000/night | Heritage palace, Polo ground, Royal dining

• Jodhpur — Raas Jodhpur ⭐⭐⭐⭐⭐ (Tunwarji ka Jhalra, Old City)
  Tariff: ₹14,000–₹25,000/night | Mehrangarh Fort views, Rooftop pool, Boutique rooms

• Udaipur — Fateh Garh ⭐⭐⭐⭐⭐ (Fatehsagar Lake Road)
  Tariff: ₹9,000–₹18,000/night | Lake Pichola views, Heritage architecture, Spa"""

    elif "goa" in dest_lower:
        return """• North Goa — Taj Fort Aguada Resort ⭐⭐⭐⭐⭐ (Sinquerim Beach, Candolim)
  Tariff: ₹12,000–₹22,000/night | Heritage fort, Beachfront, Multiple pools

• South Goa — Alila Diwa Goa ⭐⭐⭐⭐⭐ (Majorda Beach, Salcete)
  Tariff: ₹10,000–₹20,000/night | Paddy field views, Infinity pool, Fine dining

• Panjim — Mayfair Hideaway Spa Resort ⭐⭐⭐⭐ (Near Panjim City)
  Tariff: ₹5,500–₹10,000/night | Pool, Spa, City & river views"""

    elif "kashmir" in dest_lower or "srinagar" in dest_lower:
        return """• Srinagar — The Lalit Grand Palace ⭐⭐⭐⭐⭐ (Gupkar Road, Srinagar)
  Tariff: ₹10,000–₹20,000/night | Dal Lake views, Heritage palace, Mughal gardens

• Gulmarg — Khyber Himalayan Resort ⭐⭐⭐⭐⭐ (Gulmarg)
  Tariff: ₹12,000–₹25,000/night | Ski slopes, Mountain views, Fireplace suites

• Pahalgam — Mountain Retreat Resort ⭐⭐⭐⭐ (Pahalgam)
  Tariff: ₹5,000–₹9,000/night | Pine forest, River-facing rooms, Trekking base"""

    # Generic fallback for any other destination
    return ""


async def hotel_agent(state: TripState):
    """Recommends 2-3 mid-range hotels for the key overnight stops."""
    dest = state.get("destination") or "Delhi"
    route = state.get("places_covered") or dest

    # Try curated list first for known circuits
    curated = generate_curated_hotels(dest, route)
    if curated:
        return {"hotels": curated}

    # For unknown destinations, ask the LLM
    prompt = f"""Recommend 3 highly-rated mid-range hotels for travelers visiting {dest} (Route: {route}).
For each hotel, mention:
- Hotel Name & exact location / overnight stop city
- Approx. tariff per night in INR
- Star rating and 2-3 key amenities
Format as clean bullet points, one hotel per bullet."""

    try:
        res = await llm.ainvoke(prompt)
        hotels_text = res.content.strip()
        if hotels_text:
            return {"hotels": hotels_text}
    except Exception as e:
        print(f"Warning: hotel_agent LLM call failed: {e}")

    # Last-resort generic fallback
    return {"hotels": f"""• Hotel 1 — Premium City Hotel ⭐⭐⭐⭐ ({dest})
  Tariff: ₹4,000–₹7,000/night | AC rooms, Restaurant, 24hr Front Desk

• Hotel 2 — Mid-Range Comfort Inn ⭐⭐⭐ ({dest})
  Tariff: ₹2,500–₹4,500/night | Clean rooms, Breakfast included, WiFi

• Hotel 3 — Budget Stay ⭐⭐⭐ ({dest})
  Tariff: ₹1,500–₹2,500/night | Basic amenities, Hot water, Central location"""}

builder = StateGraph(TripState)
builder.add_node('destination', destination_agent)
builder.add_node('flight_search', flight_search_agent)
builder.add_node('review', review_agent)
builder.add_node('itinerary', itinerary_agent)
builder.add_node('budget', budget_agent)
builder.add_node('hotels', hotel_agent)

builder.set_entry_point('destination')
builder.add_edge('destination', 'flight_search')
builder.add_edge('flight_search', 'review')
builder.add_edge('review', 'itinerary')
builder.add_edge('itinerary', 'budget')
builder.add_edge('budget', 'hotels')
builder.add_edge('hotels', END)

memory = MemorySaver()
trip_graph = builder.compile(checkpointer=memory)
trip_agent = trip_graph
