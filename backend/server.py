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


STRONG_CLUBS = {
    "real madrid", "barcelona", "manchester city", "liverpool", "bayern",
    "paris saint-germain", "manchester united", "arsenal", "chelsea",
    "juventus", "milan", "inter", "borussia dortmund", "atletico",
    "atl\u00e9tico", "tottenham", "napoli", "benfica", "porto", "ajax", "sporting",
    "roma", "lazio", "sevilla", "villarreal", "leicester", "west ham",
    "newcastle", "aston villa", "marseille", "lyon", "monaco", "leverkusen",
    "rb leipzig", "wolfsburg", "fiorentina", "atalanta", "real sociedad",
    "athletic", "betis", "fenerbah\u00e7e", "galatasaray", "be\u015fikta\u015f",
    "trabzonspor", "river plate", "boca juniors", "flamengo", "palmeiras",
    "celtic", "rangers", "psv", "club brugge", "shakhtar", "dynamo kyiv",
    "zenit", "olympiacos", "panathinaikos", "slavia", "red bull salzburg",
    "braga", "lille", "rennes", "nice", "frankfurt", "hoffenheim",
    "brighton", "crystal palace", "everton", "fulham", "bournemouth",
    "nottingham forest",
}

TOP_COMPETITIONS = {
    "uefa champions league", "premier league", "la liga", "serie a",
    "bundesliga", "ligue 1", "uefa europa league",
}

MID_COMPETITIONS = {
    "championship", "copa libertadores", "eredivisie", "primeira liga",
    "uefa europa conference league", "serie b", "2. bundesliga",
}


def is_strong(team_name):
    name = (team_name or "").lower()
    return any(club in name for club in STRONG_CLUBS)


def get_comp_tier(comp_name):
    name = (comp_name or "").lower()
    if any(c in name for c in TOP_COMPETITIONS):
        return "top"
    if any(c in name for c in MID_COMPETITIONS):
        return "mid"
    return "lower"


def generate_analysis(match_data):
    home = match_data.get("homeTeam", {})
    away = match_data.get("awayTeam", {})
    comp = match_data.get("competition", {})
    status = match_data.get("status", "")
    score = match_data.get("score", {})

    home_name = home.get("shortName") or home.get("name") or "Ev Sahibi"
    away_name = away.get("shortName") or away.get("name") or "Deplasman"
    comp_name = comp.get("name") or "Bilinmeyen Lig"
    comp_tier = get_comp_tier(comp_name)

    home_strong = is_strong(home.get("name", ""))
    away_strong = is_strong(away.get("name", ""))

    home_score = score.get("fullTime", {}).get("home")
    away_score = score.get("fullTime", {}).get("away")
    has_score = home_score is not None and away_score is not None
    is_finished = status == "FINISHED"
    is_live = status in ("IN_PLAY", "PAUSED")

    # --- Ma\u00e7 \u00d6zeti ---
    if is_finished and has_score:
        if home_score > away_score:
            ozet = (
                f"{home_name}, kendi sahas\u0131nda {away_name} kar\u015f\u0131s\u0131nda "
                f"{home_score}-{away_score} skoruyla galip ayr\u0131ld\u0131. "
                f"{comp_name} kapsam\u0131nda oynanan ma\u00e7ta ev sahibi ekip "
                f"beklentilere uygun bir performans sergiledi."
            )
        elif away_score > home_score:
            ozet = (
                f"{away_name}, deplasmanda {home_name} kar\u015f\u0131s\u0131nda "
                f"{away_score}-{home_score} skoruyla galip ayr\u0131ld\u0131. "
                f"Deplasman ekibinin etkili bir performans ortaya koydu\u011fu g\u00f6r\u00fcld\u00fc."
            )
        else:
            ozet = (
                f"{home_name} ile {away_name} aras\u0131ndaki m\u00fccadele "
                f"{home_score}-{away_score} beraberlikle sona erdi. "
                f"Her iki tak\u0131m da birbirine \u00fcst\u00fcnl\u00fck sa\u011flayamad\u0131."
            )
    elif is_live and has_score:
        ozet = (
            f"{home_name} - {away_name} ma\u00e7\u0131 \u015fu an devam ediyor. "
            f"Anl\u0131k skor {home_score}-{away_score}. "
            f"{comp_name} kapsam\u0131nda oynanan kar\u015f\u0131la\u015fma heyecan\u0131n\u0131 koruyor."
        )
    else:
        if home_strong and away_strong:
            ozet = (
                f"{comp_name} kapsam\u0131nda \u00f6nemli bir kar\u015f\u0131la\u015fma. "
                f"{home_name} ve {away_name} her ikisi de g\u00fc\u00e7l\u00fc kadrolar. "
                f"Ev sahibi avantaj\u0131 {home_name} i\u00e7in k\u0131smi bir \u00fcst\u00fcnl\u00fck sa\u011flasa da, "
                f"iki tak\u0131m\u0131n kalitesi dengeyi koruyor."
            )
        elif home_strong:
            ozet = (
                f"{home_name}, kendi sahas\u0131nda {away_name} ile kar\u015f\u0131la\u015facak. "
                f"Kadro kalitesi ve ev sahibi avantaj\u0131 {home_name} lehine g\u00f6r\u00fcn\u00fcyor. "
                f"Ancak futbolda s\u00fcrprizler her zaman m\u00fcmk\u00fcn."
            )
        elif away_strong:
            ozet = (
                f"{away_name}, deplasmanda {home_name} kar\u015f\u0131s\u0131na \u00e7\u0131kacak. "
                f"Kadro kalitesi a\u00e7\u0131s\u0131ndan {away_name} \u00f6ne \u00e7\u0131ksa da, "
                f"ev sahibi avantaj\u0131 dengeleyici bir fakt\u00f6r olabilir."
            )
        else:
            ozet = (
                f"{comp_name} kapsam\u0131nda {home_name} ile {away_name} kar\u015f\u0131 kar\u015f\u0131ya geliyor. "
                f"Her iki tak\u0131m da benzer seviyelerde de\u011ferlendirilebilir. "
                f"Ev sahibi avantaj\u0131 k\u0131smi bir fark yaratabilir."
            )

    # --- \u00d6ne \u00c7\u0131kan Senaryo ---
    if is_finished and has_score:
        if home_score > away_score:
            senaryo = (
                f"Ma\u00e7 {home_name} galibiyetiyle sonu\u00e7land\u0131. "
                f"Ev sahibi tak\u0131m\u0131n sahas\u0131ndaki avantaj\u0131n\u0131 kulland\u0131\u011f\u0131 bir kar\u015f\u0131la\u015fma oldu."
            )
        elif away_score > home_score:
            senaryo = (
                f"Deplasman ekibi {away_name} ma\u00e7tan galip ayr\u0131ld\u0131. "
                f"Ev sahibi avantaj\u0131na ra\u011fmen {away_name} fark\u0131n\u0131 ortaya koydu."
            )
        else:
            senaryo = (
                f"Ma\u00e7 beraberlikle sona erdi. \u0130ki tak\u0131m\u0131n birbirine denk "
                f"g\u00fc\u00e7te oldu\u011fu bir kar\u015f\u0131la\u015fma ya\u015fand\u0131."
            )
    elif home_strong and away_strong:
        senaryo = (
            f"Her iki tak\u0131m da kaliteli kadroya sahip. "
            f"\u00d6ne \u00e7\u0131kan ihtimal d\u00fc\u015f\u00fck skorlu ve \u00e7eki\u015fmeli bir ma\u00e7 olmas\u0131. "
            f"Ev sahibi {home_name} hafif avantajl\u0131 g\u00f6r\u00fcnse de, "
            f"beraberlik ihtimali de g\u00f6z ard\u0131 edilmemeli."
        )
    elif home_strong:
        senaryo = (
            f"{home_name} galibiyeti daha olas\u0131 g\u00f6r\u00fcn\u00fcyor. "
            f"Ev sahibi avantaj\u0131 ve kadro kalitesi {home_name} lehine \u00f6ne \u00e7\u0131kan fakt\u00f6rler. "
            f"Ev sahibi ekibin kontrol\u00fc elinde tuttu\u011fu bir ma\u00e7 beklenebilir."
        )
    elif away_strong:
        senaryo = (
            f"{away_name} deplasmanda da favori konumunda. "
            f"Kadro derinli\u011fi ve kalitesi \u00f6ne \u00e7\u0131kan fakt\u00f6rler. "
            f"Ancak deplasman zorluklar\u0131 g\u00f6z \u00f6n\u00fcnde bulundurulmal\u0131."
        )
    else:
        if comp_tier == "top":
            senaryo = (
                f"\u00dcst d\u00fczey bir ligde oynanan bu ma\u00e7ta ev sahibi avantaj\u0131 belirleyici olabilir. "
                f"{home_name} hafif \u00f6ne \u00e7\u0131ksa da, "
                f"\u00e7eki\u015fmeli bir m\u00fccadele bekleniyor."
            )
        else:
            senaryo = (
                f"Benzer seviyelerdeki iki tak\u0131m aras\u0131nda dengeli bir ma\u00e7 \u00f6ng\u00f6r\u00fclebilir. "
                f"Ev sahibi {home_name} k\u0131smi avantaja sahip olsa da, "
                f"sonu\u00e7 a\u00e7\u0131k."
            )

    # --- Alternatif Senaryo ---
    if is_finished and has_score:
        goal_total = home_score + away_score
        if goal_total >= 3:
            alternatif = (
                f"Toplam {goal_total} gol at\u0131lan ma\u00e7ta hareketli bir futbol izlendi. "
                f"Her iki tak\u0131m\u0131n da gol aray\u0131\u015f\u0131nda oldu\u011fu a\u00e7\u0131k bir kar\u015f\u0131la\u015fmayd\u0131."
            )
        else:
            alternatif = (
                f"D\u00fc\u015f\u00fck skorlu bir ma\u00e7 ya\u015fand\u0131. "
                f"Savunma odakl\u0131 yakla\u015f\u0131mlar\u0131n \u00f6ne \u00e7\u0131kt\u0131\u011f\u0131 bir kar\u015f\u0131la\u015fma oldu."
            )
    elif home_strong and away_strong:
        alternatif = (
            f"Her iki tak\u0131m\u0131n da gol buldu\u011fu a\u00e7\u0131k bir ma\u00e7 da de\u011ferlendirilebilir. "
            f"Kaliteli oyuncular\u0131n bulundu\u011fu kar\u015f\u0131la\u015fmalarda "
            f"y\u00fcksek skorlu sonu\u00e7lar s\u0131kl\u0131kla g\u00f6r\u00fclebilir."
        )
    elif home_strong or away_strong:
        favored = home_name if home_strong else away_name
        underdog = away_name if home_strong else home_name
        alternatif = (
            f"{underdog} savunma odakl\u0131 bir stratejiyle s\u00fcrpriz yapabilir. "
            f"Alt seviye tak\u0131mlar\u0131n disiplinli oyunuyla "
            f"beraberlik elde etti\u011fi ma\u00e7lar az de\u011fildir."
        )
    else:
        alternatif = (
            f"G\u00f6l\u00fc az bir ma\u00e7 ihtimali de g\u00f6z \u00f6n\u00fcnde bulundurulmal\u0131. "
            f"Her iki tak\u0131m da temkinli ba\u015flayabilir ve "
            f"ilk yar\u0131 skorsuz ge\u00e7ebilir."
        )

    # --- Risk Notu ---
    risk_factors = []

    if comp_tier == "top" and home_strong and away_strong:
        risk_factors.append(
            "\u00dcst d\u00fczey kar\u015f\u0131la\u015fmalarda skor tahminleri zorla\u015f\u0131r"
        )
    if away_strong and not home_strong:
        risk_factors.append(
            f"{away_name} deplasmanda zorlanabilir, ev sahibi s\u00fcrpriz yapabilir"
        )
    if home_strong and not away_strong:
        risk_factors.append(
            f"{home_name} motivasyon eksikli\u011fi ya\u015fayabilir"
        )
    if "champions league" in (comp.get("name") or "").lower():
        risk_factors.append(
            "Avrupa kupalar\u0131nda beklenmedik sonu\u00e7lar s\u0131k g\u00f6r\u00fcl\u00fcr"
        )
    if "libertadores" in (comp.get("name") or "").lower():
        risk_factors.append(
            "G\u00fcney Amerika kupalar\u0131nda deplasman ma\u00e7lar\u0131 olduk\u00e7a zorludur"
        )
    if not home_strong and not away_strong:
        risk_factors.append(
            "Her iki tak\u0131m\u0131n da formu net de\u011fil, s\u00fcrpriz sonu\u00e7lar olas\u0131"
        )

    if is_finished:
        risk = "Ma\u00e7 sona erdi. Analiz geriye d\u00f6n\u00fck de\u011ferlendirme i\u00e7indir."
    elif is_live:
        risk = "Ma\u00e7 devam ediyor. Canl\u0131 skor durumu de\u011fi\u015fiklik g\u00f6sterebilir."
    elif risk_factors:
        risk = ". ".join(risk_factors) + ". Bu fakt\u00f6rler g\u00f6z \u00f6n\u00fcnde bulundurulmal\u0131d\u0131r."
    else:
        risk = (
            "Her ma\u00e7 farkl\u0131 dinamiklere sahiptir. "
            "Sakatl\u0131klar, hava ko\u015fullar\u0131 ve motivasyon gibi fakt\u00f6rler "
            "sonu\u00e7lar\u0131 etkileyebilir."
        )

    return {
        "mac_ozeti": ozet,
        "one_cikan_senaryo": senaryo,
        "alternatif_senaryo": alternatif,
        "risk_notu": risk,
    }


@app.get("/api/match/{match_id}/analysis")
async def get_match_analysis(match_id: int):
    headers = get_headers()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{FOOTBALL_API_BASE}/matches/{match_id}",
                headers=headers,
                timeout=15.0
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Ma\u00e7 verisi al\u0131namad\u0131.")
            match_data = resp.json()
            return generate_analysis(match_data)
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="API iste\u011fi zaman a\u015f\u0131m\u0131na u\u011frad\u0131.")


@app.get("/api/health")
async def health():
    token = os.environ.get("FOOTBALL_DATA_API_TOKEN")
    return {
        "status": "ok",
        "api_token_configured": bool(token)
    }
