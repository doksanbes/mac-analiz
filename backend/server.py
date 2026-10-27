from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import httpx
import os
import asyncio
import time
from pathlib import Path

load_dotenv(Path(__file__).with_name('.env'), override=False)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.environ.get(
        'ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000'
    ).split(',') if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

FOOTBALL_API_BASE = "https://api.football-data.org/v4"

_cache = {}
CACHE_TTL = 120


def cache_get(key):
    entry = _cache.get(key)
    if entry and time.time() - entry["t"] < CACHE_TTL:
        return entry["d"]
    return None


def cache_set(key, data):
    _cache[key] = {"d": data, "t": time.time()}


def get_headers():
    token = os.environ.get("FOOTBALL_DATA_API_TOKEN")
    if not token:
        raise HTTPException(
            status_code=503,
            detail="FOOTBALL_DATA_API_TOKEN ayarlanmam\u0131\u015f. L\u00fctfen backend/.env dosyan\u0131za API anahtar\u0131n\u0131z\u0131 ekleyin."
        )
    return {"X-Auth-Token": token}


async def fetch_provider_object(path, headers):
    """Read a provider object without exposing its body, token or transport details."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(FOOTBALL_API_BASE + path, headers=headers, timeout=15.0)
            if response.status_code == 403:
                raise HTTPException(status_code=403, detail="API anahtarı geçersiz veya yetkisiz.")
            if response.status_code == 429:
                raise HTTPException(status_code=429, detail="API istek limiti aşıldı. Lütfen daha sonra tekrar deneyin.")
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Maç verileri alınamadı.")
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError('Expected a provider object')
            return data
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="API isteği zaman aşımına uğradı.") from None
        except (httpx.RequestError, ValueError):
            raise HTTPException(status_code=502, detail="Veri sağlayıcıdan geçerli bir yanıt alınamadı. Tekrar deneyin.") from None


@app.get("/api/matches")
async def get_matches():
    cached = cache_get("matches_list")
    if cached:
        return cached
    data = await fetch_provider_object('/matches', get_headers())
    if not isinstance(data.get('matches'), list):
        raise HTTPException(status_code=502, detail="Veri sağlayıcıdan geçerli bir maç listesi alınamadı. Tekrar deneyin.")
    cache_set("matches_list", data)
    return data


@app.get("/api/match/{match_id}")
async def get_match(match_id: int):
    cached = cache_get(f"match_{match_id}")
    if cached:
        return cached
    data = await fetch_provider_object(f'/matches/{match_id}', get_headers())
    cache_set(f"match_{match_id}", data)
    return data


STRONG_CLUBS = {
    "real madrid", "barcelona", "manchester city", "liverpool", "bayern",
    "paris saint-germain", "manchester united", "arsenal", "chelsea",
    "juventus", "milan", "inter", "borussia dortmund", "atletico",
    "atl\u00e9tico", "tottenham", "napoli", "benfica", "porto", "ajax", "sporting",
    "roma", "lazio", "sevilla", "villarreal", "west ham",
    "newcastle", "aston villa", "marseille", "lyon", "monaco", "leverkusen",
    "rb leipzig", "wolfsburg", "fiorentina", "atalanta", "real sociedad",
    "athletic", "betis", "fenerbah\u00e7e", "galatasaray", "be\u015fikta\u015f",
    "trabzonspor", "river plate", "boca juniors", "flamengo", "palmeiras",
    "celtic", "rangers", "psv", "club brugge", "shakhtar",
    "braga", "lille", "rennes", "nice", "frankfurt",
    "brighton", "crystal palace", "nottingham forest",
}

TOP_COMPETITIONS = {
    "uefa champions league", "premier league", "la liga", "serie a",
    "bundesliga", "ligue 1", "uefa europa league",
}

MID_COMPETITIONS = {
    "championship", "copa libertadores", "eredivisie", "primeira liga",
    "uefa europa conference league", "serie b", "2. bundesliga",
}

KNOCKOUT_STAGES = {
    "LAST_16", "ROUND_OF_16", "QUARTER_FINALS", "SEMI_FINALS", "PLAYOFF",
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


async def fetch_team_recent(team_id, api_headers):
    if not team_id:
        return []
    cached = cache_get(f"team_{team_id}")
    if cached is not None:
        return cached
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{FOOTBALL_API_BASE}/teams/{team_id}/matches",
                params={"status": "FINISHED", "limit": 15},
                headers=api_headers,
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json().get("matches", [])
                cache_set(f"team_{team_id}", data)
                return data
        except Exception:
            pass
    return []


async def fetch_h2h(match_id, api_headers):
    cached = cache_get(f"h2h_{match_id}")
    if cached is not None:
        return cached
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{FOOTBALL_API_BASE}/matches/{match_id}/head2head",
                params={"limit": 10},
                headers=api_headers,
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                cache_set(f"h2h_{match_id}", data)
                return data
        except Exception:
            pass
    return None


def calc_team_stats(team_id, matches):
    s = {
        "played": 0, "wins": 0, "draws": 0, "losses": 0,
        "gf": 0, "ga": 0,
        "kg": 0, "over25": 0, "cs": 0, "fts": 0,
        "form": [],
    }
    for m in matches:
        if m.get("status") != "FINISHED":
            continue
        ft = m.get("score", {}).get("fullTime", {})
        hs, aws = ft.get("home"), ft.get("away")
        if hs is None or aws is None:
            continue
        is_home = m.get("homeTeam", {}).get("id") == team_id
        gf = hs if is_home else aws
        ga = aws if is_home else hs
        s["played"] += 1
        s["gf"] += gf
        s["ga"] += ga
        if gf > ga:
            s["wins"] += 1
            s["form"].append("G")
        elif gf == ga:
            s["draws"] += 1
            s["form"].append("B")
        else:
            s["losses"] += 1
            s["form"].append("M")
        if hs > 0 and aws > 0:
            s["kg"] += 1
        if hs + aws > 2:
            s["over25"] += 1
        if ga == 0:
            s["cs"] += 1
        if gf == 0:
            s["fts"] += 1
    n = max(s["played"], 1)
    s["avg_gf"] = round(s["gf"] / n, 1)
    s["avg_ga"] = round(s["ga"] / n, 1)
    s["kg_pct"] = round(s["kg"] / n * 100)
    s["over25_pct"] = round(s["over25"] / n * 100)
    s["form_str"] = "".join(s["form"][:5])
    return s


def calc_h2h_stats(home_id, h2h_data):
    if not h2h_data:
        return None
    agg = h2h_data.get("aggregates", {})
    matches = h2h_data.get("matches", [])
    if not matches and not agg:
        return None
    ha = agg.get("homeTeam", {})
    aa = agg.get("awayTeam", {})
    s = {
        "played": agg.get("numberOfMatches", 0),
        "total_goals": agg.get("totalGoals", 0),
        "home_wins": ha.get("wins", 0),
        "away_wins": aa.get("wins", 0),
        "draws": ha.get("draws", 0),
        "kg": 0, "over25": 0,
    }
    for m in matches:
        ft = m.get("score", {}).get("fullTime", {})
        hs, aws = ft.get("home"), ft.get("away")
        if hs is None or aws is None:
            continue
        if hs > 0 and aws > 0:
            s["kg"] += 1
        if hs + aws > 2:
            s["over25"] += 1
    nm = max(len(matches), 1)
    s["avg_goals"] = round(s["total_goals"] / max(s["played"], 1), 1)
    s["kg_pct"] = round(s["kg"] / nm * 100)
    s["over25_pct"] = round(s["over25"] / nm * 100)
    return s


def detect_two_leg(match_data, h2h_data):
    stage = match_data.get("stage", "")
    if stage not in KNOCKOUT_STAGES:
        return None
    if not h2h_data or not h2h_data.get("matches"):
        return None
    match_id = match_data.get("id")
    comp_id = match_data.get("competition", {}).get("id")
    away_id = match_data.get("awayTeam", {}).get("id")
    for m in h2h_data["matches"]:
        if m.get("id") == match_id or m.get("competition", {}).get("id") != comp_id:
            continue
        if m.get("status") != "FINISHED":
            continue
        ft = m.get("score", {}).get("fullTime", {})
        hs, aws = ft.get("home"), ft.get("away")
        if hs is None or aws is None:
            continue
        fl_home_id = m.get("homeTeam", {}).get("id")
        if fl_home_id == away_id:
            return {
                "score": f"{hs}-{aws}",
                "home_first_away": aws,
                "away_first_home": hs,
                "home_leads": aws > hs,
                "away_leads": hs > aws,
                "tied": hs == aws,
            }
    return None


def f(v):
    if v == int(v):
        return str(int(v))
    return str(round(v, 1))


def generate_analysis(match_data, home_stats, away_stats, h2h_stats, two_leg):
    home = match_data.get("homeTeam", {})
    away = match_data.get("awayTeam", {})
    comp = match_data.get("competition", {})
    status = match_data.get("status", "")
    score = match_data.get("score", {})

    hn = home.get("shortName") or home.get("name") or "Ev Sahibi"
    an = away.get("shortName") or away.get("name") or "Deplasman"
    cn = comp.get("name") or ""
    tier = get_comp_tier(cn)
    h_str = is_strong(home.get("name", ""))
    a_str = is_strong(away.get("name", ""))

    ft_h = score.get("fullTime", {}).get("home")
    ft_a = score.get("fullTime", {}).get("away")
    has_sc = ft_h is not None and ft_a is not None
    done = status == "FINISHED"
    live = status in ("IN_PLAY", "PAUSED")

    hp = home_stats["played"] if home_stats else 0
    ap = away_stats["played"] if away_stats else 0
    has_data = hp >= 3 and ap >= 3

    # ========== MA\u00c7 \u00d6ZET\u0130 ==========
    oz = []
    if done and has_sc:
        if ft_h > ft_a:
            oz.append(f"{hn}, sahas\u0131nda {an} kar\u015f\u0131s\u0131nda {ft_h}-{ft_a} galip.")
        elif ft_a > ft_h:
            oz.append(f"{an}, deplasmanda {hn}'yi {ft_a}-{ft_h} ma\u011flup etti.")
        else:
            oz.append(f"{hn} - {an} m\u00fccadelesi {ft_h}-{ft_a} beraberlikle sonu\u00e7land\u0131.")
    elif live and has_sc:
        oz.append(f"{hn} - {an} devam ediyor. Anl\u0131k skor: {ft_h}-{ft_a}.")
    else:
        oz.append(f"{cn} kapsam\u0131nda {hn} ile {an} kar\u015f\u0131 kar\u015f\u0131ya.")
    if has_data:
        oz.append(
            f"{hn} son {hp} ma\u00e7ta {home_stats['wins']}G-{home_stats['draws']}B-{home_stats['losses']}M "
            f"(ma\u00e7 ba\u015f\u0131 ort. {f(home_stats['avg_gf'])} gol at\u0131yor, {f(home_stats['avg_ga'])} gol yiyor). "
            f"{an} son {ap} ma\u00e7ta {away_stats['wins']}G-{away_stats['draws']}B-{away_stats['losses']}M "
            f"(ma\u00e7 ba\u015f\u0131 ort. {f(away_stats['avg_gf'])} gol at\u0131yor, {f(away_stats['avg_ga'])} gol yiyor)."
        )
        oz.append(f"Form: {hn} [{home_stats['form_str']}] \u2013 {an} [{away_stats['form_str']}].")
    elif h_str and a_str:
        oz.append("Her iki tak\u0131m da kaliteli kadroya sahip, \u00e7eki\u015fmeli bir ma\u00e7 bekleniyor.")
    elif h_str:
        oz.append(f"{hn} kadro kalitesi ve ev sahibi avantaj\u0131yla \u00f6ne \u00e7\u0131k\u0131yor.")
    elif a_str:
        oz.append(f"{an} kadro kalitesiyle \u00f6ne \u00e7\u0131ksa da deplasman fakt\u00f6r\u00fc dengeleyici.")
    if two_leg:
        oz.append(f"\u0130ki ayakl\u0131 e\u015fle\u015fmenin ikinci ma\u00e7\u0131. \u0130lk ma\u00e7 sonucu: {two_leg['score']}.")
        if two_leg["home_leads"]:
            oz.append(f"{hn} toplamda \u00f6nde, kontroll\u00fc bir oyun tercih edebilir.")
        elif two_leg["away_leads"]:
            oz.append(f"{an} toplamda \u00f6nde. {hn} a\u00e7\u0131lmak zorunda kalabilir.")
        else:
            oz.append("Toplam skor e\u015fit, her \u015fey bu ma\u00e7ta belirlenecek.")
    if h2h_stats and h2h_stats["played"] >= 3:
        oz.append(
            f"Kar\u015f\u0131l\u0131kl\u0131 ge\u00e7mi\u015f (son {h2h_stats['played']} ma\u00e7): "
            f"{hn} {h2h_stats['home_wins']}G, {h2h_stats['draws']}B, {an} {h2h_stats['away_wins']}G."
        )

    # ========== KG ANAL\u0130Z\u0130 ==========
    kp = []
    if has_data:
        avg_kg = (home_stats["kg_pct"] + away_stats["kg_pct"]) / 2
        kp.append(
            f"{hn} son {hp} ma\u00e7\u0131n\u0131n %{home_stats['kg_pct']}'inde, "
            f"{an} son {ap} ma\u00e7\u0131n\u0131n %{away_stats['kg_pct']}'inde kar\u015f\u0131l\u0131kl\u0131 gol var."
        )
        if h2h_stats and h2h_stats["played"] >= 3:
            kp.append(f"Kar\u015f\u0131l\u0131kl\u0131 ma\u00e7larda KG oran\u0131: %{h2h_stats['kg_pct']}.")
        if avg_kg >= 65:
            kp.append(
                "KG Var taraf\u0131 daha mant\u0131kl\u0131 g\u00f6r\u00fcn\u00fcyor. "
                "Her iki tak\u0131m da gol bulma e\u011filiminde."
            )
        elif avg_kg >= 45:
            kp.append(
                "KG Var ihtimali biraz daha a\u011f\u0131r bas\u0131yor "
                "ancak net bir e\u011filim yok. Temkinli yakla\u015f\u0131lmal\u0131."
            )
        else:
            kp.append(
                "KG Yok taraf\u0131 daha olas\u0131 duruyor. "
                "En az bir tak\u0131m\u0131n gol bulmakta zorland\u0131\u011f\u0131 g\u00f6r\u00fcl\u00fcyor."
            )
        if home_stats["fts"] >= 2:
            kp.append(f"{hn} son {hp} ma\u00e7ta {home_stats['fts']} kez gols\u00fcz kald\u0131.")
        if away_stats["fts"] >= 2:
            kp.append(f"{an} son {ap} ma\u00e7ta {away_stats['fts']} kez gols\u00fcz kald\u0131.")
        if home_stats["cs"] >= 3:
            kp.append(f"{hn} savunmada sa\u011flam: son {hp} ma\u00e7ta {home_stats['cs']} kez gol yemedi.")
        if away_stats["cs"] >= 3:
            kp.append(f"{an} savunmada sa\u011flam: son {ap} ma\u00e7ta {away_stats['cs']} kez gol yemedi.")
    else:
        if h_str and a_str:
            kp.append("Her iki tak\u0131m da kaliteli h\u00fccum hatt\u0131na sahip. KG Var daha mant\u0131kl\u0131 g\u00f6r\u00fcn\u00fcyor.")
        elif h_str or a_str:
            strong_n = hn if h_str else an
            weak_n = an if h_str else hn
            kp.append(f"{strong_n} gol bulma konusunda sorun ya\u015famaz, {weak_n}'nin gol kapasitesi belirleyici.")
        else:
            kp.append("Detayl\u0131 istatistik verisi mevcut de\u011fil. Ma\u00e7\u0131n ba\u011flam\u0131na g\u00f6re de\u011ferlendirilmeli.")
    if two_leg:
        if two_leg["away_leads"]:
            kp.append(
                f"Toplamda geride olan {hn} gol aramak zorunda. "
                "Bu durum KG Var ihtimalini art\u0131r\u0131yor."
            )
        elif two_leg["home_leads"]:
            kp.append(
                f"{an} skor bulmak zorunda, bu a\u00e7\u0131lmaya neden olabilir. "
                "Kontr atak f\u0131rsatlar\u0131yla KG Var ihtimali y\u00fckseliyor."
            )

    # ========== GOL ANAL\u0130Z\u0130 (2.5 \u00dcST/ALT) ==========
    gp = []
    if has_data:
        combined = home_stats["avg_gf"] + away_stats["avg_gf"]
        avg_o25 = (home_stats["over25_pct"] + away_stats["over25_pct"]) / 2
        gp.append(
            f"{hn} ma\u00e7 ba\u015f\u0131na ort. {f(home_stats['avg_gf'])} gol at\u0131yor, "
            f"{f(home_stats['avg_ga'])} gol yiyor. "
            f"{an} ort. {f(away_stats['avg_gf'])} gol at\u0131yor, "
            f"{f(away_stats['avg_ga'])} gol yiyor."
        )
        gp.append(
            f"2.5 \u00dcst ger\u00e7ekle\u015fme: {hn} %{home_stats['over25_pct']}, "
            f"{an} %{away_stats['over25_pct']}."
        )
        if h2h_stats and h2h_stats["played"] >= 3:
            gp.append(
                f"Kar\u015f\u0131l\u0131kl\u0131 ma\u00e7larda ort. {f(h2h_stats['avg_goals'])} gol, "
                f"2.5 \u00dcst oran\u0131: %{h2h_stats['over25_pct']}."
            )
        if avg_o25 >= 65:
            gp.append(
                "2.5 \u00dcst taraf\u0131 daha olas\u0131 duruyor. "
                "Her iki tak\u0131m\u0131n ma\u00e7lar\u0131 da goll\u00fc ge\u00e7iyor."
            )
        elif avg_o25 >= 45:
            gp.append(
                "2.5 s\u0131n\u0131r\u0131nda bir ma\u00e7 bekleniyor. "
                "Ma\u00e7\u0131n ak\u0131\u015f\u0131na g\u00f6re \u00fcst veya alt ger\u00e7ekle\u015febilir."
            )
        else:
            gp.append(
                "D\u00fc\u015f\u00fck skorlu ma\u00e7 senaryosu daha yak\u0131n. "
                "Her iki tak\u0131m\u0131n ma\u00e7lar\u0131 da az goll\u00fc ge\u00e7me e\u011filiminde."
            )
        if combined > 3.0:
            gp.append(f"Toplam gol ort. ({f(combined)}) y\u00fcksek. Goll\u00fc ma\u00e7 ihtimali g\u00fc\u00e7l\u00fc.")
        elif combined < 2.0:
            gp.append(f"Toplam gol ort. ({f(combined)}) d\u00fc\u015f\u00fck. K\u0131s\u0131r bir ma\u00e7 beklenebilir.")
    else:
        if h_str and a_str:
            gp.append("\u0130ki g\u00fc\u00e7l\u00fc tak\u0131m aras\u0131nda temkinli ba\u015flang\u0131\u00e7 olur. 2.5 Alt ihtimali hafif \u00f6ne \u00e7\u0131k\u0131yor.")
        elif tier == "top":
            gp.append("\u00dcst d\u00fczey lig ma\u00e7lar\u0131nda gol ortalamalar\u0131 genelde y\u00fcksektir. 2.5 \u00dcst de\u011ferlendirilebilir.")
        else:
            gp.append("Detayl\u0131 istatistik mevcut de\u011fil. Ma\u00e7\u0131n ba\u011flam\u0131na g\u00f6re de\u011ferlendirilmeli.")
    if two_leg:
        if two_leg["away_leads"] or two_leg["home_leads"]:
            gp.append(
                "Geride olan tak\u0131m\u0131n a\u00e7\u0131lma zorunlulu\u011fu "
                "ma\u00e7\u0131n temposunu y\u00fckseltebilir. \u00dcst ihtimali artabilir."
            )
        elif two_leg["tied"]:
            gp.append("Toplam skor e\u015fit. \u0130ki tak\u0131m da avantaj isteyecek, gol say\u0131s\u0131 artabilir.")

    # ========== MA\u00c7 SONUCU E\u011e\u0130L\u0130M\u0130 ==========
    mp = []
    if done and has_sc:
        if ft_h > ft_a:
            mp.append(f"Ma\u00e7 {hn} galibiyetiyle sonu\u00e7land\u0131 ({ft_h}-{ft_a}).")
        elif ft_a > ft_h:
            mp.append(f"Ma\u00e7 {an} galibiyetiyle sonu\u00e7land\u0131 ({ft_a}-{ft_h} deplasman lehine).")
        else:
            mp.append(f"Ma\u00e7 {ft_h}-{ft_a} beraberlikle sona erdi.")
    elif has_data:
        h_wp = round(home_stats["wins"] / max(hp, 1) * 100)
        a_wp = round(away_stats["wins"] / max(ap, 1) * 100)
        mp.append(
            f"{hn} galibiyet oran\u0131: %{h_wp} (son {hp} ma\u00e7). "
            f"{an} galibiyet oran\u0131: %{a_wp} (son {ap} ma\u00e7)."
        )
        diff = (h_wp + 10) - a_wp
        if diff > 25:
            mp.append(
                f"Ev sahibi {hn} bir ad\u0131m \u00f6nde. "
                f"Form ve ev sahibi avantaj\u0131 {hn} lehine ciddi bir fark olu\u015fturuyor."
            )
        elif diff > 10:
            mp.append(
                f"{hn} ev sahibi avantaj\u0131yla hafif favori konumunda. "
                "Ancak fark b\u00fcy\u00fck de\u011fil, beraberlik ihtimali g\u00f6z ard\u0131 edilmemeli."
            )
        elif diff > -10:
            mp.append(
                "Dengeli bir ma\u00e7 g\u00f6r\u00fcnt\u00fcs\u00fc var. "
                "Beraberlik ihtimali en az di\u011fer sonu\u00e7lar kadar g\u00fc\u00e7l\u00fc duruyor."
            )
        elif diff > -25:
            mp.append(
                f"{an} formda ve deplasmanda bile hafif favori. "
                f"Ancak ev sahibi avantaj\u0131 {hn}'yi dengeye getiriyor."
            )
        else:
            mp.append(
                f"{an} a\u00e7\u0131k ara formda. "
                f"Deplasman olmas\u0131na ra\u011fmen {an} galibiyeti daha olas\u0131."
            )
        if h2h_stats and h2h_stats["played"] >= 3:
            hw, aw, dr = h2h_stats["home_wins"], h2h_stats["away_wins"], h2h_stats["draws"]
            if hw > aw:
                mp.append(f"Kar\u015f\u0131l\u0131kl\u0131 ge\u00e7mi\u015fte {hn} \u00fcst\u00fcn: {hw}G-{dr}B-{aw}M.")
            elif aw > hw:
                mp.append(f"Kar\u015f\u0131l\u0131kl\u0131 ge\u00e7mi\u015fte {an} \u00fcst\u00fcn: {aw}G-{dr}B-{hw}M.")
            else:
                mp.append(f"Kar\u015f\u0131l\u0131kl\u0131 ge\u00e7mi\u015f dengeli: {hw}-{dr}-{aw}.")
    else:
        if h_str and not a_str:
            mp.append(f"{hn} galibiyeti \u00f6ne \u00e7\u0131kan ihtimal. Ev sahibi avantaj\u0131 ve kadro kalitesi belirleyici.")
        elif a_str and not h_str:
            mp.append(f"{an} deplasmanda da favori ancak ev sahibi s\u00fcrprizi m\u00fcmk\u00fcn.")
        elif h_str and a_str:
            mp.append("Dengeli e\u015fle\u015fme. Ev sahibi avantaj\u0131 k\u00fc\u00e7\u00fck fark yaratabilir, beraberlik de g\u00fc\u00e7l\u00fc ihtimal.")
        else:
            mp.append(f"Ev sahibi avantaj\u0131 {hn} lehine k\u0131smi bir fark yaratabilir. Sonu\u00e7 a\u00e7\u0131k.")
    if two_leg:
        if two_leg["home_leads"]:
            mp.append(
                f"{hn} toplamda \u00f6nde, defansif oynayabilir. "
                f"D\u00fc\u015f\u00fck skorlu ma\u00e7 veya {an} galibiyeti ihtimali artabilir."
            )
        elif two_leg["away_leads"]:
            mp.append(
                f"{hn} a\u00e7\u0131lmak zorunda. "
                f"Ma\u00e7\u0131n a\u00e7\u0131k ge\u00e7mesi beklenir, ev sahibi galibiyeti daha olas\u0131 "
                f"ama {an} kontr atakla da skorla d\u00f6nebilir."
            )

    # ========== R\u0130SK NOTU ==========
    rp = []
    if done:
        rp.append("Ma\u00e7 sona erdi. Bu analiz geriye d\u00f6n\u00fck de\u011ferlendirme i\u00e7indir.")
    elif live:
        rp.append("Ma\u00e7 devam ediyor. Canl\u0131 skor durumu anl\u0131k de\u011fi\u015febilir.")
    else:
        if has_data:
            hf5 = home_stats["form_str"][:5]
            af5 = away_stats["form_str"][:5]
            if hf5.count("G") <= 1 and hf5.count("M") >= 2:
                rp.append(f"{hn} son d\u00f6nemde tutars\u0131z performans sergiliyor. S\u00fcrpriz sonu\u00e7lar olas\u0131.")
            if af5.count("G") <= 1 and af5.count("M") >= 2:
                rp.append(f"{an} son d\u00f6nemde istikrars\u0131z. Beklenmedik sonu\u00e7lar \u00e7\u0131kabilir.")
            if home_stats["draws"] >= hp * 0.4:
                rp.append(f"{hn} s\u0131k berabere kal\u0131yor (son {hp} ma\u00e7ta {home_stats['draws']} beraberlik).")
            if away_stats["draws"] >= ap * 0.4:
                rp.append(f"{an} s\u0131k berabere kal\u0131yor (son {ap} ma\u00e7ta {away_stats['draws']} beraberlik).")
        cl = cn.lower()
        if "champions league" in cl or "europa" in cl:
            rp.append("Avrupa kupalar\u0131nda beklenmedik sonu\u00e7lar s\u0131kl\u0131kla g\u00f6r\u00fcl\u00fcr. Motivasyon ve taktik de\u011fi\u015fiklikler belirleyici olabilir.")
        if "libertadores" in cl:
            rp.append("G\u00fcney Amerika kupalar\u0131nda deplasman ma\u00e7lar\u0131 son derece zorludur.")
        if tier == "top" and h_str and a_str:
            rp.append("\u00dcst d\u00fczey e\u015fle\u015fmelerde k\u00fc\u00e7\u00fck detaylar b\u00fcy\u00fck fark yarat\u0131r. K\u0131rm\u0131z\u0131 kart, penalt\u0131 gibi anl\u0131k olaylar sonucu de\u011fi\u015ftirebilir.")
        if two_leg:
            rp.append(
                "\u0130ki ayakl\u0131 e\u015fle\u015fmelerde toplamda \u00f6nde olan tak\u0131m tempoya h\u00fckmedebilir, "
                "bu da beklenen ma\u00e7 ak\u0131\u015f\u0131n\u0131 de\u011fi\u015ftirir."
            )
        if not rp:
            rp.append(
                "Her ma\u00e7 farkl\u0131 dinamiklere sahiptir. "
                "Sakatl\u0131klar, hava ko\u015fullar\u0131, hakem fakt\u00f6r\u00fc ve motivasyon gibi "
                "\u00f6ng\u00f6r\u00fclemeyen de\u011fi\u015fkenler sonu\u00e7lar\u0131 etkileyebilir."
            )

    # ========== HIZLI BAKI\u015e ==========
    qk = {}

    # Ana Senaryo
    if has_data:
        avg_kg = (home_stats["kg_pct"] + away_stats["kg_pct"]) / 2
        avg_o25 = (home_stats["over25_pct"] + away_stats["over25_pct"]) / 2
        if avg_kg >= 60:
            qk["ana_senaryo"] = "KG Var daha mant\u0131kl\u0131"
        elif avg_kg <= 35:
            qk["ana_senaryo"] = "KG Yok daha mant\u0131kl\u0131"
        elif avg_o25 >= 60:
            qk["ana_senaryo"] = "2.5 \u00dcst daha olas\u0131"
        elif avg_o25 <= 35:
            qk["ana_senaryo"] = "2.5 Alt daha olas\u0131"
        else:
            qk["ana_senaryo"] = "\u00c7eki\u015fmeli ma\u00e7, net e\u011filim yok"
    elif h_str and a_str:
        qk["ana_senaryo"] = "KG Var de\u011ferlendirilebilir"
    elif h_str or a_str:
        fav = hn if h_str else an
        qk["ana_senaryo"] = f"{fav} galibiyeti \u00f6ne \u00e7\u0131k\u0131yor"
    else:
        qk["ana_senaryo"] = "Ev sahibi avantaj\u0131 k\u0131smi fark yaratabilir"

    # Alternatif
    if has_data:
        if avg_kg >= 60 and avg_o25 >= 55:
            qk["alternatif"] = "2.5 \u00dcst de\u011ferlendirilebilir"
        elif avg_kg >= 60:
            qk["alternatif"] = "D\u00fc\u015f\u00fck skorlu KG Var ihtimali var"
        elif avg_o25 >= 60:
            qk["alternatif"] = "KG Var ile kombine d\u00fc\u015f\u00fcn\u00fclebilir"
        elif avg_kg <= 35:
            qk["alternatif"] = "2.5 Alt senaryosu yak\u0131n"
        else:
            qk["alternatif"] = "Beraberlik ihtimali g\u00f6z ard\u0131 edilmemeli"
    else:
        qk["alternatif"] = "Beraberlik ihtimali g\u00f6z ard\u0131 edilmemeli"

    # Taraf E\u011filimi
    if done and has_sc:
        if ft_h > ft_a:
            qk["taraf_egilimi"] = f"{hn} galip"
        elif ft_a > ft_h:
            qk["taraf_egilimi"] = f"{an} galip"
        else:
            qk["taraf_egilimi"] = "Beraberlik"
    elif has_data:
        h_wp = round(home_stats["wins"] / max(hp, 1) * 100)
        a_wp = round(away_stats["wins"] / max(ap, 1) * 100)
        diff = (h_wp + 10) - a_wp
        if diff > 25:
            qk["taraf_egilimi"] = f"{hn} bir ad\u0131m \u00f6nde"
        elif diff > 10:
            qk["taraf_egilimi"] = f"{hn} hafif favori"
        elif diff > -10:
            qk["taraf_egilimi"] = "Beraberlik ihtimali g\u00fc\u00e7l\u00fc"
        elif diff > -25:
            qk["taraf_egilimi"] = f"{an} hafif favori"
        else:
            qk["taraf_egilimi"] = f"{an} \u00f6ne \u00e7\u0131k\u0131yor"
    elif h_str and not a_str:
        qk["taraf_egilimi"] = f"{hn} bir ad\u0131m \u00f6nde"
    elif a_str and not h_str:
        qk["taraf_egilimi"] = f"{an} hafif favori"
    else:
        qk["taraf_egilimi"] = "Dengeli e\u015fle\u015fme"

    if two_leg:
        if two_leg["home_leads"]:
            qk["taraf_egilimi"] = f"{hn} toplamda \u00f6nde"
        elif two_leg["away_leads"]:
            qk["taraf_egilimi"] = f"{an} toplamda \u00f6nde, {hn} a\u00e7\u0131lmak zorunda"

    # Risk Seviyesi
    risk_count = len(rp)
    is_cup = "champions" in cn.lower() or "europa" in cn.lower() or "libertadores" in cn.lower()
    if done or live:
        qk["risk_seviyesi"] = "Ma\u00e7 tamamland\u0131" if done else "Ma\u00e7 devam ediyor"
    elif risk_count >= 3 or (is_cup and h_str and a_str):
        qk["risk_seviyesi"] = "Y\u00fcksek"
    elif risk_count >= 2 or is_cup:
        qk["risk_seviyesi"] = "Orta-Y\u00fcksek"
    elif risk_count >= 1:
        qk["risk_seviyesi"] = "Orta"
    else:
        qk["risk_seviyesi"] = "D\u00fc\u015f\u00fck"

    return {
        "hizli_bakis": qk,
        "home_form": home_stats["form_str"] if home_stats and home_stats["played"] > 0 else "",
        "away_form": away_stats["form_str"] if away_stats and away_stats["played"] > 0 else "",
        "mac_ozeti": " ".join(oz),
        "kg_analizi": " ".join(kp),
        "gol_analizi": " ".join(gp),
        "ms_egilimi": " ".join(mp),
        "risk_notu": " ".join(rp),
    }


@app.get("/api/match/{match_id}/analysis")
async def get_match_analysis(match_id: int):
    cached_analysis = cache_get(f"analysis_{match_id}")
    if cached_analysis:
        return cached_analysis

    headers = get_headers()

    match_data = await get_match(match_id)

    home_id = match_data.get("homeTeam", {}).get("id")
    away_id = match_data.get("awayTeam", {}).get("id")

    home_matches, away_matches, h2h_data = await asyncio.gather(
        fetch_team_recent(home_id, headers),
        fetch_team_recent(away_id, headers),
        fetch_h2h(match_id, headers),
    )

    home_stats = calc_team_stats(home_id, home_matches) if home_matches else None
    away_stats = calc_team_stats(away_id, away_matches) if away_matches else None
    h2h_stats = calc_h2h_stats(home_id, h2h_data)
    two_leg = detect_two_leg(match_data, h2h_data)

    result = generate_analysis(match_data, home_stats, away_stats, h2h_stats, two_leg)
    cache_set(f"analysis_{match_id}", result)
    return result


@app.get("/api/matches/form")
async def get_matches_form():
    cached = cache_get("all_form")
    if cached is not None:
        return cached
    matches_data = await get_matches()
    headers = get_headers()
    matches = matches_data.get("matches", [])
    team_ids = set()
    for m in matches:
        hid = m.get("homeTeam", {}).get("id")
        aid = m.get("awayTeam", {}).get("id")
        if hid:
            team_ids.add(hid)
        if aid:
            team_ids.add(aid)
    tasks = [fetch_team_recent(tid, headers) for tid in team_ids]
    results = await asyncio.gather(*tasks)
    team_forms = {}
    for tid, team_matches in zip(team_ids, results):
        if team_matches:
            stats = calc_team_stats(tid, team_matches)
            team_forms[tid] = stats["form_str"]
    out = {}
    for m in matches:
        mid = str(m.get("id"))
        hid = m.get("homeTeam", {}).get("id")
        aid = m.get("awayTeam", {}).get("id")
        out[mid] = {
            "home_form": team_forms.get(hid, ""),
            "away_form": team_forms.get(aid, ""),
        }
    cache_set("all_form", out)
    return out


@app.get("/api/health")
async def health():
    token = os.environ.get("FOOTBALL_DATA_API_TOKEN")
    return {
        "status": "ok",
        "api_token_configured": bool(token)
    }
