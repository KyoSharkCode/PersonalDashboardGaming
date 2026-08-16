import os
import json
import requests
from urllib.parse import quote

# ================= CONFIGURACIÓN =================
API_KEY    = os.getenv("RIOT_API_KEY", "").strip()
RIOT_NAME  = "Galactic Shark"
RIOT_TAG   = "AYK"
REGION_ACC = "americas"   # Account v1 y Match v5
REGION_LOL = "la1"        # Summoner v4, League v4, Mastery v4, Spectator v5
DDRAGON    = "14.24.1"
# =================================================

HEADERS = {"X-Riot-Token": API_KEY}


def log(msg):
    print(msg, flush=True)


# ─────────────────────────────────────────────────
# PASO 1: PUUID via Account v1
# ─────────────────────────────────────────────────
def obtener_puuid():
    url = (
        f"https://{REGION_ACC}.api.riotgames.com"
        f"/riot/account/v1/accounts/by-riot-id"
        f"/{quote(RIOT_NAME)}/{quote(RIOT_TAG)}"
    )
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code != 200:
        raise Exception(f"❌ Account v1 → {res.status_code}: {res.text}")
    data = res.json()
    log(f"✅ PUUID obtenido: {data['puuid'][:20]}...")
    return data["puuid"]


# ─────────────────────────────────────────────────
# PASO 2: Summoner (icono de perfil)
# ─────────────────────────────────────────────────
def obtener_summoner(puuid):
    url = (
        f"https://{REGION_LOL}.api.riotgames.com"
        f"/lol/summoner/v4/summoners/by-puuid/{puuid}"
    )
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code != 200:
        log(f"⚠️ Summoner v4 → {res.status_code}. Continúa sin ícono.")
        return {}
    log("✅ Summoner obtenido")
    return res.json()


# ─────────────────────────────────────────────────
# PASO 3: Rango SoloQ via League v4 by-puuid
# ─────────────────────────────────────────────────
def obtener_rango(puuid):
    url = (
        f"https://{REGION_LOL}.api.riotgames.com"
        f"/lol/league/v4/entries/by-puuid/{puuid}"
    )
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code != 200:
        log(f"⚠️ League v4 → {res.status_code}")
        return None
    entries = res.json()
    solo = next((e for e in entries if e["queueType"] == "RANKED_SOLO_5x5"), None)
    if solo:
        log(f"✅ Rango: {solo['tier']} {solo['rank']} — {solo['leaguePoints']} LP")
    else:
        log("ℹ️ Sin clasificar en SoloQ")
    return solo


# ─────────────────────────────────────────────────
# PASO 4: Top maestría campeones
# ─────────────────────────────────────────────────
def obtener_maestria(puuid, count=5):
    url = (
        f"https://{REGION_LOL}.api.riotgames.com"
        f"/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top"
        f"?count={count}"
    )
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code != 200:
        log(f"⚠️ Mastery v4 → {res.status_code}")
        return []
    log(f"✅ Top {count} maestría obtenida")
    return res.json()


# ─────────────────────────────────────────────────
# PASO 5: IDs de campeones (DDragon)
# ─────────────────────────────────────────────────
def obtener_champions_map():
    url = f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON}/data/es_ES/champion.json"
    res = requests.get(url, timeout=10)
    if res.status_code != 200:
        log("⚠️ No se pudo cargar el mapa de campeones de DDragon")
        return {}
    champ_data = res.json()["data"]
    champ_map = {v["key"]: v["id"] for v in champ_data.values()}
    log(f"✅ Mapa de {len(champ_map)} campeones cargado")
    return champ_map


# ─────────────────────────────────────────────────
# PASO 6: Últimas 10 partidas ranked
# ─────────────────────────────────────────────────
def obtener_partidas(puuid, count=10):
    url = (
        f"https://{REGION_ACC}.api.riotgames.com"
        f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        f"?queue=420&count={count}"
    )
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code != 200:
        log(f"⚠️ Match v5 IDs → {res.status_code}")
        return []
    match_ids = res.json()
    log(f"✅ {len(match_ids)} partidas encontradas")
    return match_ids


def obtener_detalle_partida(match_id):
    url = (
        f"https://{REGION_ACC}.api.riotgames.com"
        f"/lol/match/v5/matches/{match_id}"
    )
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code != 200:
        return None
    return res.json()


# ─────────────────────────────────────────────────
# PROCESAR: Campeones más jugados y roles
# ─────────────────────────────────────────────────
def procesar_partidas(match_ids, puuid):
    champ_count = {}
    role_count  = {}

    for match_id in match_ids:
        detalle = obtener_detalle_partida(match_id)
        if not detalle:
            continue
        participantes = detalle.get("info", {}).get("participants", [])
        yo = next((p for p in participantes if p.get("puuid") == puuid), None)
        if not yo:
            continue

        champ = yo.get("championName", "")
        role  = yo.get("teamPosition", "")

        if champ:
            champ_count[champ] = champ_count.get(champ, 0) + 1
        if role:
            role_count[role] = role_count.get(role, 0) + 1

    top_champs = sorted(champ_count.items(), key=lambda x: x[1], reverse=True)[:5]
    top_roles  = sorted(role_count.items(),  key=lambda x: x[1], reverse=True)[:3]

    log(f"✅ Campeones más jugados: {[c[0] for c in top_champs]}")
    log(f"✅ Roles más jugados: {[r[0] for r in top_roles]}")

    return top_champs, top_roles


# ─────────────────────────────────────────────────
# MAIN: genera datos_lol.json
# ─────────────────────────────────────────────────
def generar_datos_lol():
    log("\n📦 Generando datos_lol.json...")

    if not API_KEY:
        raise Exception("🚨 No se encontró RIOT_API_KEY en las variables de entorno.")

    puuid     = obtener_puuid()
    summoner  = obtener_summoner(puuid)
    soloQ     = obtener_rango(puuid)
    mastery   = obtener_maestria(puuid, count=5)
    champ_map = obtener_champions_map()
    match_ids = obtener_partidas(puuid, count=10)

    top_champs, top_roles = procesar_partidas(match_ids, puuid)

    # Construir maestría con nombre de campeón
    mastery_out = []
    for m in mastery:
        champ_id = champ_map.get(str(m["championId"]), str(m["championId"]))
        mastery_out.append({
            "championId":   m["championId"],
            "championName": champ_id,
            "points":       m["championPoints"],
            "level":        m["championLevel"]
        })

    datos = {
        "nombre":   f"{RIOT_NAME} #{RIOT_TAG}",
        "region":   REGION_LOL.upper(),
        "summoner": {
            "profileIconId": summoner.get("profileIconId"),
            "summonerLevel": summoner.get("summonerLevel")
        },
        "soloQ": {
            "tier":         soloQ["tier"]         if soloQ else None,
            "rank":         soloQ["rank"]         if soloQ else None,
            "lp":           soloQ["leaguePoints"] if soloQ else 0,
            "wins":         soloQ["wins"]         if soloQ else 0,
            "losses":       soloQ["losses"]       if soloQ else 0,
            "winrate":      round(soloQ["wins"] / max(soloQ["wins"] + soloQ["losses"], 1) * 100) if soloQ else 0
        } if soloQ else None,
        "maestria":       mastery_out,
        "recientes":      [{"champ": c, "partidas": n} for c, n in top_champs],
        "roles":          [{"rol": r, "partidas": n} for r, n in top_roles],
        "ddraggon_ver":   DDRAGON
    }

    with open("datos_lol.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    log("✅ datos_lol.json guardado.\n")


# ─────────────────────────────────────────────────
# VALORANT — usa Riot API oficial (misma key que LoL)
# PUUID ya lo tenemos, solo necesitamos el rango de Valo
# y el historial de partidas competitivas
# ─────────────────────────────────────────────────
def generar_datos_valo():
    log("📦 Generando datos_valo.json...")

    if not API_KEY:
        raise Exception("🚨 No se encontró RIOT_API_KEY en las variables de entorno.")

    # PUUID (mismo que LoL — misma cuenta Riot)
    url_acc = (
        f"https://{REGION_ACC}.api.riotgames.com"
        f"/riot/account/v1/accounts/by-riot-id"
        f"/{quote(RIOT_NAME)}/{quote(RIOT_TAG)}"
    )
    acc_res = requests.get(url_acc, headers=HEADERS, timeout=10)
    if acc_res.status_code != 200:
        log(f"⚠️ Account v1 → {acc_res.status_code}. Saltando Valorant.")
        with open("datos_valo.json", "w", encoding="utf-8") as f:
            json.dump({"error": "Cuenta no encontrada"}, f)
        return

    puuid = acc_res.json()["puuid"]
    log(f"✅ PUUID Valo obtenido")

    # Rango Valorant via Riot API oficial
    url_mmr = (
        f"https://la.api.riotgames.com"
        f"/val/ranked/v1/leaderboards/by-act/{{act_id}}"
    )
    # Usamos el endpoint de cuenta de Valorant
    url_account_valo = (
        f"https://la.api.riotgames.com"
        f"/val/content/v1/contents"
    )

    # El rango de Valo no está en la API de dev con key básica.
    # Usamos HenrikDev solo para el rango (es más permisivo con espacios en v1)
    name_enc = RIOT_NAME.replace(" ", "%20")
    tag_enc  = quote(RIOT_TAG)

    mmr_res = requests.get(
        f"https://api.henrikdev.xyz/valorant/v2/by-puuid/mmr/latam/{puuid}",
        timeout=10
    )
    current = {}
    if mmr_res.status_code == 200:
        mmr_data = mmr_res.json().get("data", {})
        current  = mmr_data.get("current_data", {})
        log(f"✅ Rango Valo: {current.get('currenttierpatched', 'Sin clasificar')}")
    else:
        log(f"⚠️ MMR Valo → {mmr_res.status_code}. Sin rango.")

    # Partidas recientes via HenrikDev by-puuid (evita problema de espacios)
    match_res = requests.get(
        f"https://api.henrikdev.xyz/valorant/v1/by-puuid/lifetime/matches/latam/{puuid}?mode=competitive&size=10",
        timeout=15
    )
    matches = []
    if match_res.status_code == 200:
        matches = match_res.json().get("data", [])
        log(f"✅ {len(matches)} partidas Valo encontradas")
    else:
        log(f"⚠️ Partidas Valo → {match_res.status_code}. Sin historial.")

    # Agentes más jugados
    agent_count = {}
    for match in matches:
        stats = match.get("stats", {})
        ag = stats.get("character", {}).get("name", "")
        if ag:
            agent_count[ag] = agent_count.get(ag, 0) + 1

    top_agents = sorted(agent_count.items(), key=lambda x: x[1], reverse=True)[:5]
    log(f"✅ Agentes más jugados: {[a[0] for a in top_agents]}")

    # Roles por clase de agente
    role_map = {
        "Jett":"Duelista","Reyna":"Duelista","Phoenix":"Duelista","Raze":"Duelista",
        "Neon":"Duelista","Iso":"Duelista","Waylay":"Duelista",
        "Brimstone":"Controlador","Viper":"Controlador","Omen":"Controlador",
        "Astra":"Controlador","Harbor":"Controlador","Clove":"Controlador",
        "Sova":"Iniciador","Breach":"Iniciador","Skye":"Iniciador",
        "KAY/O":"Iniciador","Fade":"Iniciador","Gekko":"Iniciador",
        "Killjoy":"Centinela","Cypher":"Centinela","Sage":"Centinela",
        "Chamber":"Centinela","Deadlock":"Centinela","Vyse":"Centinela"
    }
    role_count = {}
    for agent, n in top_agents:
        rol = role_map.get(agent, "Otro")
        role_count[rol] = role_count.get(rol, 0) + n
    top_roles = sorted(role_count.items(), key=lambda x: x[1], reverse=True)[:3]

    datos_valo = {
        "nombre":   f"{RIOT_NAME} #{RIOT_TAG}",
        "account": {
            "level":      account.get("account_level"),
            "card_small": account.get("card", {}).get("small"),
            "card_wide":  account.get("card", {}).get("wide")
        },
        "rango": {
            "tier":          current.get("currenttierpatched"),
            "rr":            current.get("ranking_in_tier", 0),
            "rank_img":      current.get("images", {}).get("small"),
            "elo_total":     current.get("elo")
        } if current else None,
        "agentes": [{"agente": a, "partidas": n} for a, n in top_agents],
        "roles":   [{"rol": r, "partidas": n} for r, n in top_roles]
    }

    with open("datos_valo.json", "w", encoding="utf-8") as f:
        json.dump(datos_valo, f, ensure_ascii=False, indent=2)

    log("✅ datos_valo.json guardado.\n")


# ─────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────
if __name__ == "__main__":
    generar_datos_lol()
    generar_datos_valo()
    log("🎉 ¡Todo actualizado!")
