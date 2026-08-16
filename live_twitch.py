"""
live_twitch.py
Genera live_twitch.json con el estado en vivo de KyoSumiVT en Twitch.
Usa TWITCH_CLIENT_ID y TWITCH_CLIENT_SECRET como variables de entorno (GitHub Secrets).
"""

import os
import json
import requests

CHANNEL = "KyoSumiVT"
CLIENT_ID     = os.getenv("TWITCH_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "")

def log(msg):
    print(msg)

def get_access_token():
    """Obtiene un App Access Token via Client Credentials."""
    res = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type":    "client_credentials"
        },
        timeout=10
    )
    if res.status_code != 200:
        raise Exception(f"Error obteniendo token Twitch → {res.status_code}: {res.text}")
    return res.json()["access_token"]

def check_live(token):
    """Devuelve True si el canal está en vivo, False si no."""
    res = requests.get(
        "https://api.twitch.tv/helix/streams",
        params={"user_login": CHANNEL},
        headers={
            "Client-ID":     CLIENT_ID,
            "Authorization": f"Bearer {token}"
        },
        timeout=10
    )
    if res.status_code != 200:
        raise Exception(f"Error consultando stream → {res.status_code}: {res.text}")

    data = res.json().get("data", [])
    if data:
        stream = data[0]
        return {
            "live":       True,
            "titulo":     stream.get("title", ""),
            "juego":      stream.get("game_name", ""),
            "viewers":    stream.get("viewer_count", 0),
            "thumbnail":  stream.get("thumbnail_url", "").replace("{width}", "320").replace("{height}", "180")
        }
    return {"live": False}

def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        log("⚠️ TWITCH_CLIENT_ID o TWITCH_CLIENT_SECRET no están definidos.")
        resultado = {"live": False}
    else:
        try:
            token     = get_access_token()
            resultado = check_live(token)
            estado    = "🔴 EN DIRECTO" if resultado["live"] else "⚫ offline"
            log(f"✅ Twitch {CHANNEL}: {estado}")
            if resultado["live"]:
                log(f"   🎮 {resultado.get('juego')} · 👁 {resultado.get('viewers')} viewers")
        except Exception as e:
            log(f"⚠️ Error Twitch: {e}")
            resultado = {"live": False}

    with open("live_twitch.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    log("✅ live_twitch.json generado")

if __name__ == "__main__":
    main()
