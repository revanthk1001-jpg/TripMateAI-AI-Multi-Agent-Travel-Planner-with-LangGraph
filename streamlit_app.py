import streamlit as st
import requests
import json
import io
from datetime import date, timedelta, datetime

# Page configuration MUST be first Streamlit command
st.set_page_config(
    page_title="TripMateAI - Smart Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

def escape_for_pdf(text: str) -> str:
    """Escapes special characters for safe ReportLab XML rendering."""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def generate_itinerary_pdf(trip: dict, currency_str: str, formatted_budget: str, formatted_pp: str) -> bytes:
    """Generates a professional agency-style tour itinerary PDF."""
    if not REPORTLAB_AVAILABLE:
        return b""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=4
    )
    
    sub_style = ParagraphStyle(
        'SubStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=12
    )
    
    day_header_style = ParagraphStyle(
        'DayHeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.white
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#374151')
    )
    
    table_time_style = ParagraphStyle(
        'TableTimeStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#B45309')
    )
    
    table_act_style = ParagraphStyle(
        'TableActStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1F2937')
    )

    story = []

    dest = escape_for_pdf(trip.get("destination", "Tour Package"))
    src = escape_for_pdf(trip.get("source", "Origin"))
    days = trip.get("num_days", len(trip.get("itinerary_days", [])))
    dep_date = escape_for_pdf(trip.get("departure_date", "Upcoming"))
    travelers = trip.get("travelers", 2)
    places = escape_for_pdf(trip.get("places_covered", dest))

    # Header
    story.append(Paragraph(f"✈️ TripMateAI Tour Itinerary: {dest}", header_style))
    story.append(Paragraph(f"{days}-Day Circuit starting from {src} | Departure: {dep_date} | Currency: {currency_str}", sub_style))

    # Overview Table
    sel_flight = trip.get("selected_flight") or {}
    flight_display = f"{sel_flight.get('airline', 'Scheduled')} (Dep: {sel_flight.get('departure_time', 'N/A')} ➔ Lands: {sel_flight.get('landing_time', 'N/A')})" if sel_flight else "Commercial Transit"

    overview_data = [
        [
            Paragraph("<b>Origin City:</b> " + src, body_style),
            Paragraph("<b>Departure Date:</b> " + dep_date, body_style),
            Paragraph("<b>Total Budget:</b> " + escape_for_pdf(formatted_budget), body_style)
        ],
        [
            Paragraph("<b>Duration:</b> " + f"{days} Days", body_style),
            Paragraph("<b>Travelers:</b> " + f"{travelers} Persons", body_style),
            Paragraph("<b>Per Person:</b> " + escape_for_pdf(formatted_pp), body_style)
        ],
        [
            Paragraph("<b>Selected Flight:</b> " + escape_for_pdf(flight_display), body_style),
            Paragraph("<b>Day 1 Landing:</b> " + escape_for_pdf(sel_flight.get('landing_time', 'Morning arrival')), body_style),
            Paragraph("<b>Circuit:</b> " + escape_for_pdf(dest), body_style)
        ]
    ]
    overview_table = Table(overview_data, colWidths=[175, 175, 190])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF3C7')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#FCD34D')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FDE68A')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 12))

    # Day-by-Day Section
    itinerary_days = trip.get("itinerary_days", [])
    if itinerary_days:
        story.append(Paragraph("<b>🗺️ Detailed Day-by-Day Itinerary & Schedule</b>", ParagraphStyle('SecTitle', fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=colors.HexColor('#1E293B'), spaceAfter=6)))
        
        for d in itinerary_days:
            day_elements = []
            day_num = d.get("day", 1)
            route = escape_for_pdf(d.get("route") or f"Day {day_num} : {d.get('title', 'Tour')}")
            title = escape_for_pdf(d.get("title", ""))
            desc = escape_for_pdf(d.get("description", ""))
            overnight = escape_for_pdf(d.get("overnight", dest))
            timetable = d.get("timetable", [])

            # Day Header
            header_table = Table([[Paragraph(f"DAY {day_num} : {title.upper()} ({route})", day_header_style)]], colWidths=[540])
            header_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F59E0B')),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ]))
            day_elements.append(header_table)

            # Day Content
            content_data = [
                [Paragraph(desc, body_style)],
                [Paragraph(f"<b>🏨 Overnight Stay:</b> {overnight}", body_style)]
            ]
            content_table = Table(content_data, colWidths=[540])
            content_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFBEB')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#FDE68A')),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ]))
            day_elements.append(content_table)

            # Timetable Table
            if timetable:
                tt_data = [[Paragraph("<b>Time</b>", table_time_style), Paragraph("<b>Daily Scheduled Timetable & Activities</b>", table_act_style)]]
                for t in timetable:
                    if isinstance(t, dict):
                        tt_data.append([
                            Paragraph(escape_for_pdf(t.get("time", "")), table_time_style),
                            Paragraph(escape_for_pdf(t.get("activity", "")), table_act_style)
                        ])
                    else:
                        tt_data.append([
                            Paragraph("Scheduled", table_time_style),
                            Paragraph(escape_for_pdf(str(t)), table_act_style)
                        ])

                tt_table = Table(tt_data, colWidths=[80, 460])
                tt_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FEF3C7')),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
                    ('TOPPADDING', (0,0), (-1,-1), 3.5),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('RIGHTPADDING', (0,0), (-1,-1), 6),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
                ]))
                day_elements.append(Spacer(1, 3))
                day_elements.append(tt_table)

            day_elements.append(Spacer(1, 10))
            story.append(KeepTogether(day_elements))

    # Transit Details
    flights = trip.get("flights")
    if flights:
        story.append(KeepTogether([
            Paragraph("<b>🛫 Transit & Travel Connections</b>", ParagraphStyle('TransTitle', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#1E293B'), spaceAfter=4)),
            Table([[Paragraph(escape_for_pdf(flights).replace('\n', '<br/>'), body_style)]], colWidths=[540], style=[
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0F9FF')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#BAE6FD')),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
            ]),
            Spacer(1, 8)
        ]))

    # Hotel Details
    hotels = trip.get("hotels")
    if hotels:
        story.append(KeepTogether([
            Paragraph("<b>🏨 Recommended Hotels</b>", ParagraphStyle('HotelTitle', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#1E293B'), spaceAfter=4)),
            Table([[Paragraph(escape_for_pdf(hotels).replace('\n', '<br/>'), body_style)]], colWidths=[540], style=[
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0FDF4')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#BBF7D0')),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
            ]),
            Spacer(1, 8)
        ]))

    doc.build(story)
    return buf.getvalue()

@st.cache_data(show_spinner=False)
def get_cached_pdf(trip_json_str: str, currency_str: str, formatted_budget: str, formatted_pp: str) -> bytes:
    """Caches generated PDF bytes in memory so day-switching never rebuilds the PDF."""
    try:
        trip = json.loads(trip_json_str)
        return generate_itinerary_pdf(trip, currency_str, formatted_budget, formatted_pp)
    except Exception:
        return b""

@st.cache_data(ttl=30, show_spinner=False)
def check_backend_health(url: str) -> bool:
    """Caches backend health check to eliminate redundant HTTP requests on every UI click."""
    try:
        r = requests.get(f"{url}/", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False

@st.cache_data(ttl=20, show_spinner=False)
def fetch_saved_trips(api_url: str):
    """Caches saved trips from PostgreSQL to prevent repeated heavy database queries on reruns."""
    try:
        trips_res = requests.get(f"{api_url}/trips", timeout=5)
        if trips_res.status_code == 200:
            return trips_res.json()
    except Exception:
        pass
    return []

# Custom CSS for modern travel styling and the Day-by-Day itinerary card matching agency style
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .main-title span {
        color: #F59E0B;
    }
    .tagline {
        font-size: 1.0rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    
    /* Day Itinerary Layout matching agency view */
    .day-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 68px;
        height: 68px;
        border-radius: 50%;
        background-color: #F59E0B;
        color: #FFFFFF;
        font-weight: 800;
        font-size: 1.05rem;
        letter-spacing: 0.05em;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(245, 158, 11, 0.3);
    }
    .itinerary-card {
        background-color: #FEF3C7;
        border: 1.5px solid #FDE68A;
        border-radius: 12px;
        padding: 2rem 2.2rem;
        min-height: 280px;
    }
    .day-title {
        font-size: 1.45rem;
        font-weight: 700;
        color: #1F2937;
        margin-bottom: 0.8rem;
    }
    .day-desc {
        font-size: 1.02rem;
        line-height: 1.65;
        color: #374151;
        margin-bottom: 1.2rem;
    }
    .day-overnight {
        display: inline-block;
        background: #FDE68A;
        color: #92400E;
        padding: 0.35rem 0.85rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.88rem;
        margin-bottom: 0.5rem;
    }

    /* Reset radio widget title label so it NEVER gets a box or background */
    div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin-bottom: 0.6rem !important;
        box-shadow: none !important;
    }
    div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] * {
        color: inherit !important;
        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }

    /* Style the radio options container */
    div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 8px !important;
        display: flex !important;
        flex-direction: column !important;
    }

    /* Unselected Option Card: Works seamlessly in both Dark Mode and Light Mode */
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] {
        background-color: var(--secondary-background-color, rgba(255, 255, 255, 0.06)) !important;
        border: 1.5px solid rgba(128, 128, 128, 0.28) !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        margin-bottom: 6px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"]:hover {
        border-color: #F59E0B !important;
        background-color: rgba(245, 158, 11, 0.12) !important;
    }

    /* Force readable high-contrast text on unselected options in dark and light modes */
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] p,
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] span,
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] div {
        color: var(--text-color, #E2E8F0) !important;
        font-size: 0.95rem !important;
        line-height: 1.4 !important;
    }

    /* Hide standard radio circle for clean agency card look */
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] > div:first-of-type {
        display: none !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] div[data-testid="stMarkdownContainer"] {
        width: 100% !important;
    }

    /* Selected Option Card: Vibrant Golden-Amber Badge with Bold White Text */
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) {
        background-color: #F59E0B !important;
        border-color: #D97706 !important;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.35) !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) p,
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) span,
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) div {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Agency-style Day Navigation Buttons (Zero flickering, zero radio circles) */
    button[aria-label^="Day "] {
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 12px 14px !important;
        border-radius: 6px !important;
        margin-bottom: 6px !important;
        font-size: 0.94rem !important;
        line-height: 1.4 !important;
        white-space: normal !important;
        height: auto !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
    }
    button[aria-label^="Day "][data-testid="baseButton-primary"],
    button[aria-label^="Day "][kind="primary"] {
        background-color: #F59E0B !important;
        border: 1.5px solid #D97706 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        box-shadow: 0 3px 8px rgba(245, 158, 11, 0.35) !important;
    }
    button[aria-label^="Day "][data-testid="baseButton-primary"] *,
    button[aria-label^="Day "][kind="primary"] * {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    button[aria-label^="Day "][data-testid="baseButton-secondary"],
    button[aria-label^="Day "][kind="secondary"] {
        background-color: var(--secondary-background-color, rgba(255, 255, 255, 0.05)) !important;
        border: 1.5px solid rgba(128, 128, 128, 0.25) !important;
        color: var(--text-color, #E2E8F0) !important;
    }
    button[aria-label^="Day "][data-testid="baseButton-secondary"]:hover,
    button[aria-label^="Day "][kind="secondary"]:hover {
        border-color: #F59E0B !important;
        background-color: rgba(245, 158, 11, 0.12) !important;
    }
    button[aria-label^="Day "][data-testid="baseButton-secondary"] *,
    button[aria-label^="Day "][kind="secondary"] * {
        color: var(--text-color, #E2E8F0) !important;
    }

    /* Daily Timetable Timeline */
    .timetable-box {
        background: #FFFFFF;
        border: 1px solid #FCD34D;
        border-radius: 8px;
        padding: 1.2rem;
        margin-top: 1.2rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    .timetable-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #92400E;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .timetable-row {
        display: flex;
        align-items: flex-start;
        padding: 0.45rem 0;
        border-bottom: 1px dashed #FDE68A;
    }
    .timetable-row:last-child {
        border-bottom: none;
    }
    .timetable-time {
        background: #F59E0B;
        color: #FFFFFF;
        font-weight: 700;
        font-size: 0.8rem;
        padding: 0.2rem 0.55rem;
        border-radius: 4px;
        white-space: nowrap;
        margin-right: 0.85rem;
        min-width: 78px;
        text-align: center;
    }
    .timetable-act {
        color: #374151;
        font-size: 0.95rem;
        line-height: 1.45;
    }

    /* Currency & Budget Card */
    .budget-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
    }
    .budget-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0F172A;
    }
</style>
""", unsafe_allow_html=True)

# Currency exchange rates relative to 1 INR (Base currency)
CURRENCIES = {
    "INR (₹)": {"symbol": "₹", "rate": 1.0, "format": "{:,.0f}"},
    "USD ($)": {"symbol": "$", "rate": 0.0118, "format": "{:,.2f}"},
    "EUR (€)": {"symbol": "€", "rate": 0.0109, "format": "{:,.2f}"},
    "GBP (£)": {"symbol": "£", "rate": 0.0093, "format": "{:,.2f}"},
    "AED (د.إ)": {"symbol": "AED ", "rate": 0.0432, "format": "{:,.2f}"},
    "SGD (S$)": {"symbol": "S$", "rate": 0.0158, "format": "{:,.2f}"},
    "CAD (C$)": {"symbol": "C$", "rate": 0.0164, "format": "{:,.2f}"},
    "AUD (A$)": {"symbol": "A$", "rate": 0.0182, "format": "{:,.2f}"},
    "JPY (¥)": {"symbol": "¥", "rate": 1.82, "format": "{:,.0f}"},
    "THB (฿)": {"symbol": "฿", "rate": 0.41, "format": "{:,.2f}"},
    "SAR (﷼)": {"symbol": "SAR ", "rate": 0.0442, "format": "{:,.2f}"},
    "CHF (CHF)": {"symbol": "CHF ", "rate": 0.0104, "format": "{:,.2f}"},
    "MYR (RM)": {"symbol": "RM", "rate": 0.052, "format": "{:,.2f}"},
}

def format_currency(inr_amount, currency_key):
    info = CURRENCIES.get(currency_key, CURRENCIES["INR (₹)"])
    converted = float(inr_amount) * info["rate"]
    return f"{info['symbol']}{info['format'].format(converted)}"

# Session State Initialization
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "step" not in st.session_state:
    st.session_state.step = "input"  # 'input', 'review', 'completed'
if "plan_data" not in st.session_state:
    st.session_state.plan_data = {}
if "selected_day_idx" not in st.session_state:
    st.session_state.selected_day_idx = 0
if "user_currency" not in st.session_state:
    st.session_state.user_currency = "INR (₹)"

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Settings")
    api_base_url = st.text_input("Backend API URL", value="http://127.0.0.1:8000")
    
    # Check Backend Health (Cached for 30s to eliminate redundant HTTP calls on every click)
    backend_online = check_backend_health(api_base_url)
    if backend_online:
        st.success("🟢 Backend Connected", icon="✅")
    else:
        st.error("🔴 Backend Offline", icon="❌")
        st.caption("Run in terminal: `uvicorn app.main:app --reload --port 8000`")

    st.markdown("---")
    st.subheader("💱 Global Currency")
    st.session_state.user_currency = st.selectbox(
        "Choose Display Currency",
        options=list(CURRENCIES.keys()),
        index=list(CURRENCIES.keys()).index(st.session_state.user_currency)
    )

    st.markdown("---")
    if st.button("🔄 Start New Trip Plan", use_container_width=True):
        st.session_state.thread_id = None
        st.session_state.step = "input"
        st.session_state.plan_data = {}
        st.session_state.selected_day_idx = 0
        st.rerun()

# Main Header
st.markdown('<div class="main-title">TripMate<span>AI</span></div>', unsafe_allow_html=True)
st.markdown('<div class="tagline">Personalized multi-agent travel itineraries with dynamic budget conversion</div>', unsafe_allow_html=True)

# Clean Navigation (No architecture diagrams)
tab_planner, tab_history = st.tabs(["✈️ Plan Your Trip", "📚 Saved Itineraries"])

# ==========================================
# TAB 1: TRIP PLANNER
# ==========================================
with tab_planner:
    # ----------------------------------------------------
    # STEP 1: USER INPUT FORM
    # ----------------------------------------------------
    if st.session_state.step == "input":
        st.subheader("1. Enter Trip Details")
        
        # 1. Source City
        st.markdown("**Origin / Starting City**")
        source_quick = st.pills(
            "Popular Starting Hubs",
            options=["Delhi", "Bengaluru", "Mumbai", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad", "Jaipur"],
            default="Delhi"
        )
        source_city = st.text_input(
            "Or enter custom starting city:",
            value=source_quick or "Delhi",
            placeholder="e.g. Delhi, Mumbai, Pune, London, New York..."
        )

        st.markdown("---")

        # 2. Destination / Tour Circuit
        st.markdown("**Destination or Popular Circuit**")
        circuit_quick = st.pills(
            "Popular Circuits & Packages",
            options=[
                "Golden Triangle (Delhi - Agra - Jaipur)",
                "Char Dham Yatra",
                "Kerala Backwaters & Hills",
                "Rajasthan Heritage Tour",
                "Varanasi - Ayodhya Spiritual Tour",
                "Kashmir Paradise Tour",
                "Goa Beach Holiday",
                "Himachal Valley Tour"
            ],
            default="Golden Triangle (Delhi - Agra - Jaipur)"
        )
        destination_input = st.text_input(
            "Or enter your custom destination / circuit:",
            value=circuit_quick or "Golden Triangle (Delhi - Agra - Jaipur)",
            placeholder="e.g. Golden Triangle, Char Dham, Kerala, Paris, Bali, Ladakh..."
        )

        st.markdown("---")

        # 3. Dates, Days & Travelers
        col_date, col_days, col_travelers = st.columns(3)
        with col_date:
            departure_date = st.date_input("Date of Departure", value=date.today() + timedelta(days=7))
        with col_days:
            num_days = st.number_input("Number of Days", min_value=1, max_value=25, value=4, step=1)
        with col_travelers:
            travelers_count = st.number_input("Number of Travelers", min_value=1, max_value=20, value=2, step=1)

        # 4. Extra Preferences
        extra_pref = st.text_input(
            "Special Requests / Preferences (Optional)",
            placeholder="e.g. Vegetarian food, comfortable 4-star hotels, private AC cab, focus on photography..."
        )

        st.markdown("<br>", unsafe_allow_html=True)
        btn_disabled = not backend_online or not source_city.strip() or not destination_input.strip()
        
        if st.button("🚀 Fetch Places & Available Flights", type="primary", disabled=btn_disabled, use_container_width=True):
            with st.spinner("🤖 Searching available flights and analyzing tour route..."):
                try:
                    payload = {
                        "source": source_city.strip(),
                        "destination": destination_input.strip(),
                        "departure_date": str(departure_date),
                        "num_days": int(num_days),
                        "travelers": int(travelers_count),
                        "preferences": extra_pref.strip()
                    }
                    res = requests.post(f"{api_base_url}/plan", json=payload, timeout=60)
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.thread_id = data.get("thread_id")
                        st.session_state.plan_data = data
                        st.session_state.step = "review"
                        st.rerun()
                    else:
                        st.error(f"Error from API ({res.status_code}): {res.text}")
                except Exception as e:
                    st.error(f"Connection to backend failed: {e}")

    # ----------------------------------------------------
    # STEP 2: HUMAN-IN-THE-LOOP (HITL) REVIEW & FLIGHT SELECT
    # ----------------------------------------------------
    elif st.session_state.step == "review":
        data = st.session_state.plan_data
        places = data.get("places_covered", data.get("destination", ""))
        src = data.get("source", "Origin")
        dest = data.get("destination", "Destination")
        days = data.get("num_days", 4)
        dep_date = data.get("departure_date", "")

        st.info("✋ **Human-in-the-Loop Review**: Select your flight and review your tour stops before generating the day-by-day plan.")
        
        st.subheader("2. Review Your Tour Circuit & Select Flight")
        
        circuit_card = (
            f'<div style="background: rgba(245, 158, 11, 0.12); border: 1.5px solid #FCD34D; border-radius: 10px; padding: 1.2rem; margin-bottom: 1.2rem;">'
            f'<div style="font-size: 0.85rem; color: #F59E0B; font-weight: 700; text-transform: uppercase;">Identified Route & Circuit</div>'
            f'<div style="font-size: 1.4rem; font-weight: 800; color: #F59E0B; margin: 0.2rem 0;">{dest}</div>'
            f'<div style="font-size: 1.0rem; color: var(--text-color, #E2E8F0); margin-bottom: 0.4rem;"><strong>Proposed Stops:</strong> {places}</div>'
            f'<div style="color: var(--text-color, #94A3B8); font-size: 0.92rem;">🛫 <strong>From:</strong> {src} &nbsp;|&nbsp; 📅 <strong>Departure Date:</strong> {dep_date} &nbsp;|&nbsp; ⏱️ <strong>Duration:</strong> {days} Days</div>'
            f'</div>'
        )
        st.html(circuit_card)

        # ----------------------------------------------------
        # FLIGHT SELECTION SECTION
        # ----------------------------------------------------
        st.markdown(f"### ✈️ Available Flights on {dep_date}")
        st.caption("Select your flight. Day 1's itinerary timeline and pickup schedule will be designed based on this flight's landing time!")

        flights_list = data.get("available_flights", [])
        chosen_flight = None
        
        if flights_list:
            flight_labels = []
            for f in flights_list:
                airline = f.get('airline', 'Flight')
                dep = f.get('departure_time', 'N/A')
                land = f.get('landing_time', 'N/A')
                dur = f.get('duration', 'N/A')
                fare = f.get('price_inr', 0)
                slot = f.get('slot', 'Flight')
                label = f"🛫 {airline} | Dep: {dep} ➔ Lands: {land} ({dur}) — ₹{fare:,} per person ({slot})"
                flight_labels.append(label)

            selected_label = st.radio(
                "Choose Your Flight:",
                options=flight_labels,
                index=0,
                key="radio_flight_select"
            )
            chosen_flight = flights_list[flight_labels.index(selected_label)].copy()
            st.caption(f"Selected: **{chosen_flight.get('airline')}** (Departs: {chosen_flight.get('departure_time')} ➔ Lands: **{chosen_flight.get('landing_time')}**) — Day 1 timetable will commence directly upon arrival.")
        else:
            chosen_flight = {
                "airline": "Scheduled Commercial Flight",
                "departure_time": "06:30 AM",
                "landing_time": "09:15 AM",
                "duration": "2h 45m",
                "price_inr": 4850,
                "slot": "Morning Flight"
            }
            st.info(f"Default flight assigned: {chosen_flight['airline']} (Lands: {chosen_flight['landing_time']})")

        with st.expander("🕒 Or customize landing / arrival time (Optional)"):
            c_land = st.text_input("Enter custom landing time (e.g., 08:30 AM, 01:15 PM, 06:45 PM):", placeholder="09:15 AM")
            if c_land.strip() and chosen_flight:
                chosen_flight["landing_time"] = c_land.strip()
                chosen_flight["airline"] = f"{chosen_flight.get('airline', 'Flight')} (Custom Landing: {c_land.strip()})"

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Option 1: Approve Circuit & Flight")
            st.write(f"Proceed with **{dest}** and flight landing at **{chosen_flight.get('landing_time', '09:15 AM')}**.")
            if st.button("✅ Approve & Generate Itinerary", type="primary", use_container_width=True):
                with st.spinner(f"⚡ Generating itinerary with Day 1 timeline starting from landing time ({chosen_flight.get('landing_time')})..."):
                    try:
                        feedback_payload = {
                            "places_covered": places,
                            "selected_flight": chosen_flight
                        }
                        res = requests.post(
                            f"{api_base_url}/resume/{st.session_state.thread_id}",
                            json={"feedback": json.dumps(feedback_payload)},
                            timeout=120
                        )
                        if res.status_code == 200:
                            res_data = res.json()
                            if res_data.get("status") == "completed":
                                st.session_state.plan_data = res_data.get("trip")
                                st.session_state.step = "completed"
                                st.session_state.selected_day_idx = 0
                                st.rerun()
                            else:
                                st.warning(f"Status: {res_data.get('status')}")
                        else:
                            st.error(f"Error resuming graph ({res.status_code}): {res.text}")
                    except Exception as e:
                        st.error(f"Request failed: {e}")

        with col2:
            st.markdown("#### Option 2: Edit Stops / Places")
            st.write("Want to customize tour cities or stops? Type your revised route below:")
            custom_stops = st.text_input("Custom stops/route", value=places)
            if st.button("✈️ Update Route & Generate Itinerary", disabled=not custom_stops.strip(), use_container_width=True):
                with st.spinner(f"⚡ Updating route and generating itinerary with landing time ({chosen_flight.get('landing_time')})..."):
                    try:
                        feedback_payload = {
                            "places_covered": custom_stops.strip(),
                            "selected_flight": chosen_flight
                        }
                        res = requests.post(
                            f"{api_base_url}/resume/{st.session_state.thread_id}",
                            json={"feedback": json.dumps(feedback_payload)},
                            timeout=120
                        )
                        if res.status_code == 200:
                            res_data = res.json()
                            if res_data.get("status") == "completed":
                                st.session_state.plan_data = res_data.get("trip")
                                st.session_state.step = "completed"
                                st.session_state.selected_day_idx = 0
                                st.rerun()
                            else:
                                st.warning(f"Status: {res_data.get('status')}")
                        else:
                            st.error(f"Error resuming graph ({res.status_code}): {res.text}")
                    except Exception as e:
                        st.error(f"Request failed: {e}")

    # ----------------------------------------------------
    # STEP 3: PROPER ITINERARY DISPLAY & CURRENCY CONVERTER
    # ----------------------------------------------------
    elif st.session_state.step == "completed" and st.session_state.plan_data:
        trip = st.session_state.plan_data
        dest = trip.get("destination", "Your Destination")
        src = trip.get("source", "Origin")
        days = trip.get("num_days", len(trip.get("itinerary_days", [])))
        travelers = trip.get("travelers", 2)
        budget = trip.get("budget", {})
        itinerary_days = trip.get("itinerary_days", [])
        currency = st.session_state.user_currency

        # Success message
        st.success(f"🎉 Complete {days}-Day Travel Plan generated for **{dest}** (Starting from {src})!")

        # Prominent Flight Badge
        sel_fl = trip.get("selected_flight") or {}
        if sel_fl:
            flight_box = (
                f'<div style="background: rgba(59, 130, 246, 0.12); border: 1.5px solid #60A5FA; border-radius: 8px; padding: 0.85rem 1.1rem; margin-bottom: 1.1rem;">'
                f'<span style="font-weight: 700; color: #60A5FA;">✈️ Booked Flight:</span> <strong style="color: var(--text-color, #F8FAFC);">{sel_fl.get("airline", "Scheduled Flight")}</strong> &nbsp;|&nbsp; '
                f'<span style="color: var(--text-color, #E2E8F0);">🛫 Departs: <strong>{sel_fl.get("departure_time", "N/A")}</strong></span> &nbsp;➔&nbsp; '
                f'<span style="color: var(--text-color, #E2E8F0);">🛬 <strong>Lands: {sel_fl.get("landing_time", "N/A")}</strong></span> &nbsp;|&nbsp; '
                f'<span style="color: var(--text-color, #E2E8F0);">⏱️ Duration: {sel_fl.get("duration", "N/A")}</span> &nbsp;|&nbsp; '
                f'<span style="color: #F59E0B; font-weight: 700;">💰 Fare: ₹{sel_fl.get("price_inr", 0):,} per person</span>'
                f'<div style="color: #93C5FD; font-size: 0.85rem; margin-top: 0.35rem;">ℹ️ Day 1\'s schedule commences immediately upon landing at <strong>{sel_fl.get("landing_time", "N/A")}</strong>.</div>'
                f'</div>'
            )
            st.html(flight_box)

        # ----------------------------------------------------
        # DYNAMIC BUDGET CALCULATION & CONVERSION CARD
        # ----------------------------------------------------
        st.markdown("### 💰 Calculated Budget & Currency Converter")
        
        # Extract base INR amounts
        total_inr = budget.get("total_inr", 40000)
        per_person_inr = budget.get("per_person_inr", total_inr // max(travelers, 1))
        breakdown = budget.get("breakdown", {})
        acc_inr = breakdown.get("accommodation_inr", int(total_inr * 0.45))
        trans_inr = breakdown.get("transportation_inr", int(total_inr * 0.35))
        food_inr = breakdown.get("food_and_activities_inr", int(total_inr * 0.20))

        # Currency bar
        col_cur_sel, col_total, col_pp = st.columns([1.5, 1.5, 1.5])
        with col_cur_sel:
            selected_cur = st.selectbox(
                "Convert Currency To:",
                options=list(CURRENCIES.keys()),
                index=list(CURRENCIES.keys()).index(currency),
                key="active_currency_selector"
            )
            st.session_state.user_currency = selected_cur
        with col_total:
            formatted_total = format_currency(total_inr, selected_cur)
            st.metric("Total Trip Cost", formatted_total, f"{travelers} Travelers")
        with col_pp:
            formatted_pp = format_currency(per_person_inr, selected_cur)
            st.metric("Cost Per Person", formatted_pp)

        # Itemized breakdown pills
        budget_card_html = (
            f'<div style="background: var(--secondary-background-color, rgba(255, 255, 255, 0.05)); border: 1px solid rgba(128, 128, 128, 0.25); border-radius: 10px; padding: 1.2rem; margin-bottom: 1.2rem;">'
            f'<div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 10px; text-align: center;">'
            f'<div><div style="color: var(--text-color, #94A3B8); font-size: 0.85rem;">🏨 Accommodation</div><div style="font-weight: 700; font-size: 1.15rem; color: #F59E0B;">{format_currency(acc_inr, selected_cur)}</div></div>'
            f'<div><div style="color: var(--text-color, #94A3B8); font-size: 0.85rem;">🚗 Transport / Flights</div><div style="font-weight: 700; font-size: 1.15rem; color: #F59E0B;">{format_currency(trans_inr, selected_cur)}</div></div>'
            f'<div><div style="color: var(--text-color, #94A3B8); font-size: 0.85rem;">🍽️ Food & Activities</div><div style="font-weight: 700; font-size: 1.15rem; color: #F59E0B;">{format_currency(food_inr, selected_cur)}</div></div>'
            f'</div>'
            f'</div>'
        )
        st.html(budget_card_html)

        st.markdown("---")

        # ----------------------------------------------------
        # PROPER DAY-BY-DAY ITINERARY (MATCHING AGENCY IMAGE)
        # ----------------------------------------------------
        st.markdown("### 🗺️ Day-by-Day Itinerary")
        
        if itinerary_days:
            col_nav, col_view = st.columns([1, 2.2])

            with col_nav:
                st.markdown("**Select Day:**")
                for idx, d in enumerate(itinerary_days):
                    route_text = d.get("route") or f"Day {d.get('day', idx+1)} : {d.get('title', 'Tour')}"
                    is_active = (idx == st.session_state.selected_day_idx)
                    
                    if st.button(
                        route_text,
                        key=f"btn_day_sel_{idx}",
                        type="primary" if is_active else "secondary",
                        use_container_width=True
                    ):
                        if st.session_state.selected_day_idx != idx:
                            st.session_state.selected_day_idx = idx
                            st.rerun()

            with col_view:
                selected_idx = min(st.session_state.selected_day_idx, len(itinerary_days) - 1)
                cur_day = itinerary_days[selected_idx]
                day_num = cur_day.get("day", selected_idx + 1)
                day_title = cur_day.get("title", f"Day {day_num}")
                day_desc = cur_day.get("description", "Activities planned for this day.")
                overnight_stay = cur_day.get("overnight", dest)
                timetable_items = cur_day.get("timetable", [])

                # Format Timetable rows with pure HTML and robust inline styling (Zero Markdown parsing issues)
                tt_html = ""
                if timetable_items:
                    row_items = []
                    for t_item in timetable_items:
                        if isinstance(t_item, dict):
                            t_time = t_item.get("time", "")
                            t_act = t_item.get("activity", "")
                        else:
                            t_time = ""
                            t_act = str(t_item)
                        row_items.append(
                            f'<div style="display: flex; align-items: flex-start; padding: 7px 0; border-bottom: 1px dashed #FDE68A;">'
                            f'<span style="background: #F59E0B; color: #FFFFFF; font-weight: 700; font-size: 0.8rem; padding: 3px 8px; border-radius: 4px; white-space: nowrap; margin-right: 12px; min-width: 82px; text-align: center; display: inline-block;">{t_time}</span>'
                            f'<span style="color: #374151; font-size: 0.94rem; line-height: 1.45;">{t_act}</span>'
                            f'</div>'
                        )
                    tt_html = (
                        f'<div style="background: #FFFFFF; border: 1px solid #FCD34D; border-radius: 8px; padding: 14px 18px; margin-top: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">'
                        f'<div style="font-size: 1.05rem; font-weight: 700; color: #92400E; margin-bottom: 10px; display: flex; align-items: center; gap: 6px;">🕒 Daily Timetable & Schedule</div>'
                        f'{"".join(row_items)}'
                        f'</div>'
                    )

                # Build clean agency card matching reference image (fcedb9/fef3c7 card + golden circle badge)
                card_html = (
                    f'<div style="background-color: #FEF3C7; border: 1.5px solid #FDE68A; border-radius: 12px; padding: 26px 28px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); margin-bottom: 16px;">'
                    f'<div style="display: flex; align-items: center; justify-content: center; width: 68px; height: 68px; border-radius: 50%; background-color: #F59E0B; color: #FFFFFF; font-weight: 800; font-size: 1.05rem; letter-spacing: 0.05em; margin-bottom: 14px; box-shadow: 0 4px 6px -1px rgba(245, 158, 11, 0.35);">DAY {day_num}</div>'
                    f'<div style="font-size: 1.45rem; font-weight: 700; color: #1F2937; margin-bottom: 8px;">{day_title}</div>'
                    f'<div style="font-size: 1.02rem; line-height: 1.65; color: #374151; margin-bottom: 14px;">{day_desc}</div>'
                    f'<div style="display: inline-block; background: #FDE68A; color: #92400E; padding: 5px 12px; border-radius: 6px; font-weight: 600; font-size: 0.88rem; margin-bottom: 12px;">🏨 Overnight Stay: <strong>{overnight_stay}</strong></div>'
                    f'{tt_html}'
                    f'</div>'
                )
                st.html(card_html)

            # Option to view all days at a glance
            with st.expander("📋 View Complete All-Days Summary with Timetables"):
                for d in itinerary_days:
                    d_route = d.get('route') or f"Day {d.get('day', 1)}"
                    st.markdown(f"**{d_route}: {d.get('title', '')}**")
                    st.write(d.get("description", ""))
                    st.caption(f"🏨 Overnight stay: {d.get('overnight', '')}")
                    if d.get("timetable"):
                        st.markdown("**🕒 Timetable:**")
                        for t_item in d.get("timetable", []):
                            if isinstance(t_item, dict):
                                st.write(f"- `{t_item.get('time', '')}` : {t_item.get('activity', '')}")
                            else:
                                st.write(f"- {t_item}")
                    st.markdown("---")
        else:
            st.info(trip.get("itinerary", "Itinerary details available."))

        st.markdown("---")

        # ----------------------------------------------------
        # TRANSIT & HOTELS
        # ----------------------------------------------------
        col_fl, col_ht = st.columns(2)
        with col_fl:
            st.markdown("### 🛫 Transit & Connections")
            flights_info = trip.get("flights", "No transit data available.")
            st.info(flights_info)
        with col_ht:
            st.markdown("### 🏨 Recommended Hotels")
            hotels_info = trip.get("hotels", "").strip()
            if hotels_info:
                st.markdown(hotels_info)
            else:
                st.info("Hotel recommendations not available for this trip.")

        st.markdown("---")

        # Actions: PDF Download (Prominent), Markdown, JSON, Restart
        st.markdown("### 📥 Download & Export Your Itinerary")
        c_pdf, c_down, c_json, c_restart = st.columns([1.4, 1, 1, 1])
        
        with c_pdf:
            pdf_bytes = get_cached_pdf(
                trip_json_str=json.dumps(trip, sort_keys=True),
                currency_str=selected_cur,
                formatted_budget=format_currency(total_inr, selected_cur),
                formatted_pp=format_currency(per_person_inr, selected_cur)
            )
            st.download_button(
                "📄 Download Itinerary (PDF)",
                data=pdf_bytes,
                file_name=f"TripMate_{dest.replace(' ', '_')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

        with c_down:
            md_text = trip.get("itinerary", "")
            download_md = f"""# {dest} Tour Package ({days} Days)
**Starting from:** {src}
**Departure Date:** {trip.get('departure_date', '')}
**Travelers:** {travelers}
**Total Cost:** {format_currency(total_inr, selected_cur)} ({selected_cur})

## Day-by-Day Itinerary
{md_text}

## Transit Options
{flights_info}

## Hotel Recommendations
{hotels_info}

---
*Generated by TripMateAI on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
            st.download_button(
                "📥 Download Markdown (.md)",
                data=download_md,
                file_name=f"TripMate_{dest.replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True
            )

        with c_json:
            st.download_button(
                "📦 Export Full JSON",
                data=json.dumps(trip, indent=2),
                file_name=f"TripMate_{dest.replace(' ', '_')}.json",
                mime="application/json",
                use_container_width=True
            )

        with c_restart:
            if st.button("✨ Plan Another Trip", use_container_width=True):
                st.session_state.thread_id = None
                st.session_state.step = "input"
                st.session_state.plan_data = {}
                st.session_state.selected_day_idx = 0
                st.rerun()

# ==========================================
# TAB 2: SAVED ITINERARIES
# ==========================================
with tab_history:
    st.subheader("📚 Saved Trips & Packages")
    st.caption("Past travel plans stored securely in the PostgreSQL database.")

    if st.button("🔄 Refresh Trips Database"):
        fetch_saved_trips.clear()
        st.rerun()

    if backend_online:
        try:
            trips_data = fetch_saved_trips(api_base_url)
            if not trips_data:
                st.info("No saved trips found yet. Complete a trip plan above to save one!")
            else:
                for t in trips_data:
                    d_name = t.get("destination", "Trip")
                    s_name = t.get("source", "N/A")
                    d_days = t.get("num_days", "N/A")
                    c_date = t.get("created_at", "")[:19] if t.get("created_at") else ""
                    with st.expander(f"📍 {d_name} (From: {s_name}, {d_days} Days) — {c_date}"):
                        b_raw = t.get("budget", "")
                        try:
                            b_obj = json.loads(b_raw) if isinstance(b_raw, str) else b_raw
                            if isinstance(b_obj, dict) and "total_inr" in b_obj:
                                st.metric("Total Cost (INR)", f"₹{b_obj['total_inr']:,}")
                        except Exception:
                            pass
                        
                        st.markdown("**Itinerary Details:**")
                        st.write(t.get("itinerary", "N/A"))
                        st.markdown("**Transit:**")
                        st.write(t.get("flights", "N/A"))
                        st.markdown("**Hotels:**")
                        st.write(t.get("hotels", "N/A"))

                        # PDF Download button for saved trip
                        t_days = []
                        try:
                            raw_itin = t.get("itinerary", "")
                            if isinstance(raw_itin, str) and raw_itin.strip().startswith("["):
                                t_days = json.loads(raw_itin)
                        except Exception:
                            t_days = []

                        saved_trip_dict = {
                            "destination": d_name,
                            "source": s_name,
                            "num_days": d_days,
                            "departure_date": t.get("departure_date", "Saved Date"),
                            "travelers": t.get("travelers", 2),
                            "itinerary_days": t_days,
                            "flights": t.get("flights", ""),
                            "hotels": t.get("hotels", "")
                        }
                        saved_pdf = get_cached_pdf(json.dumps(saved_trip_dict, sort_keys=True), "INR (₹)", "Stored in DB", "Stored in DB")
                        st.download_button(
                            "📄 Download Itinerary (PDF)",
                            data=saved_pdf,
                            file_name=f"Trip_{d_name.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_{t.get('id', d_name)}_{c_date}"
                        )
        except Exception as e:
            st.error(f"Database query error: {e}")
    else:
        st.warning("Please start the backend server to load saved trips.")
