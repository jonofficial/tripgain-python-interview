# flight_search_api.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from playwright_web import scrape_flights
import uvicorn

app = FastAPI(title="BudgetTicket Flight Scraper")

@app.get("/flight-search")
def flight_search(
    origin: str = Query("Bangalore", description="Origin city"),
    destination: str = Query("Delhi", description="Destination city"),
    journey_date: str = Query(None, description="Journey date (YYYY-MM-DD or DD-MM-YYYY)"),
    headless: bool = Query(True, description="Run browser in headless mode")
):
    try:
        result = scrape_flights(origin=origin, destination=destination, journey_date=journey_date, headless=headless)
        return JSONResponse(content=result["results"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("flight_search_api:app", host="127.0.0.1", port=8000, reload=True)
