from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import httpx
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FOOTBALL_API_BASE = "https://api.football-data.org/v4"


def get_headers():
    token = os.environ.get("FOOTBALL_DATA_API_TOKEN")
    if not token:
        raise HTTPException(
            status_code=503,
            detail="FOOTBALL_DATA_API_TOKEN ayarlanmam\u0131\u015f. L\u00fctfen backend/.env dosyan\u0131za API anahtar\u0131n\u0131z\u0131 ekleyin."
        )
    return {"X-Auth-Token": token}


@app.get("/api/matches")
async def get_matches():
    headers = get_headers()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{FOOTBALL_API_BASE}/matches",
                headers=headers,
                timeout=15.0
            )
            if resp.status_code == 403:
                raise HTTPException(status_code=403, detail="API anahtar\u0131 ge\u00e7ersiz veya yetkisiz.")
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Ma\u00e7 verileri al\u0131namad\u0131.")
            return resp.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="API iste\u011fi zaman a\u015f\u0131m\u0131na u\u011frad\u0131.")


@app.get("/api/match/{match_id}")
async def get_match(match_id: int):
    headers = get_headers()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{FOOTBALL_API_BASE}/matches/{match_id}",
                headers=headers,
                timeout=15.0
            )
            if resp.status_code == 403:
                raise HTTPException(status_code=403, detail="API anahtar\u0131 ge\u00e7ersiz veya yetkisiz.")
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Ma\u00e7 verisi al\u0131namad\u0131.")
            return resp.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="API iste\u011fi zaman a\u015f\u0131m\u0131na u\u011frad\u0131.")


@app.get("/api/health")
async def health():
    token = os.environ.get("FOOTBALL_DATA_API_TOKEN")
    return {
        "status": "ok",
        "api_token_configured": bool(token)
    }
