import uuid
import json
from typing import Any, Union
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from langgraph.types import Command

try:
    from app.db import init_db, close_db, pool
    from app.graph import trip_graph, TripState
except ImportError:
    from db import init_db, close_db, pool
    from graph import trip_graph, TripState

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(title="TripMateAI API", lifespan=lifespan)

# Allow CORS for Streamlit frontend and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PlanRequest(BaseModel):
    source: str = "Delhi"
    destination: str = "Golden Triangle"
    departure_date: str = "2026-11-20"
    num_days: int = 4
    travelers: int = 2
    preferences: str = ""

class ResumeRequest(BaseModel):
    feedback: Union[dict, str]

@app.get("/")
async def root():
    return {
        "message": "TripMateAI API is running!",
        "endpoints": ["/plan", "/resume/{thread_id}", "/trips"]
    }

@app.post("/plan")
async def plan_trip(req: PlanRequest):
    try:
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        initial_state: TripState = {
            "source": req.source,
            "destination": req.destination,
            "departure_date": req.departure_date,
            "num_days": req.num_days,
            "travelers": req.travelers,
            "preferences": req.preferences,
            "places_covered": "",
            "available_flights": [],
            "selected_flight": {},
            "itinerary_days": [],
            "itinerary_markdown": "",
            "budget_data": {},
            "flights": "",
            "hotels": ""
        }
        
        await trip_graph.ainvoke(initial_state, config)
        state = await trip_graph.aget_state(config)
        
        places_covered = state.values.get("places_covered", "")
        available_flights = state.values.get("available_flights", [])
        selected_flight = state.values.get("selected_flight", {})
        prompt = f"Proposed stops for {req.destination}: {places_covered}"
        
        if state.tasks and state.tasks[0].interrupts:
            raw_interrupt = state.tasks[0].interrupts[0].value
            if isinstance(raw_interrupt, dict):
                places_covered = raw_interrupt.get("places_covered", places_covered)
                available_flights = raw_interrupt.get("available_flights", available_flights)
                prompt = raw_interrupt.get("prompt", prompt)
            else:
                prompt = str(raw_interrupt)
        
        return {
            "thread_id": thread_id,
            "status": "waiting",
            "source": req.source,
            "destination": req.destination,
            "departure_date": req.departure_date,
            "num_days": req.num_days,
            "travelers": req.travelers,
            "places_covered": places_covered,
            "available_flights": available_flights,
            "selected_flight": selected_flight,
            "prompt": prompt
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating trip plan: {str(e)}")

@app.post("/resume/{thread_id}")
async def resume_trip(thread_id: str, req: ResumeRequest):
    try:
        config = {"configurable": {"thread_id": thread_id}}
        await trip_graph.ainvoke(Command(resume=req.feedback), config)
        state = await trip_graph.aget_state(config)
        
        if not state.next:
            trip_data = {
                "source": state.values.get("source", ""),
                "destination": state.values.get("destination", ""),
                "departure_date": state.values.get("departure_date", ""),
                "num_days": state.values.get("num_days", 4),
                "travelers": state.values.get("travelers", 2),
                "places_covered": state.values.get("places_covered", ""),
                "selected_flight": state.values.get("selected_flight", {}),
                "available_flights": state.values.get("available_flights", []),
                "itinerary_days": state.values.get("itinerary_days", []),
                "itinerary": state.values.get("itinerary_markdown", ""),
                "budget": state.values.get("budget_data", {}),
                "flights": state.values.get("flights", ""),
                "hotels": state.values.get("hotels", "")
            }
            
            try:
                from db import pool as current_pool
            except ImportError:
                from app.db import pool as current_pool
                
            if current_pool:
                try:
                    await current_pool.execute(
                        """INSERT INTO trips (source, destination, departure_date, num_days, travelers, itinerary, budget, flights, hotels) 
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                        trip_data["source"],
                        trip_data["destination"],
                        trip_data["departure_date"],
                        trip_data["num_days"],
                        trip_data["travelers"],
                        json.dumps(trip_data["itinerary_days"]),
                        json.dumps(trip_data["budget"]),
                        trip_data["flights"],
                        trip_data["hotels"]
                    )
                except Exception as db_err:
                    print(f"Warning: Failed to save trip to database: {db_err}")

            return {"status": "completed", "trip": trip_data}
        return {"status": "still_processing"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resuming trip plan: {str(e)}")

@app.get("/trips")
async def get_trips(limit: int = 10):
    try:
        try:
            from db import pool as current_pool
        except ImportError:
            from app.db import pool as current_pool
            
        if not current_pool:
            return []
            
        rows = await current_pool.fetch("SELECT * FROM trips ORDER BY created_at DESC LIMIT $1", limit)
        results = []
        for r in rows:
            item = dict(r)
            if "created_at" in item and item["created_at"]:
                item["created_at"] = str(item["created_at"])
            results.append(item)
        return results
    except Exception as e:
        print(f"Error fetching trips: {e}")
        return []
