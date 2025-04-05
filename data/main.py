import os
import requests
from pymongo import MongoClient
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from datetime import datetime, timezone
import time

# .env laden
load_dotenv()

api_key = os.getenv("TANKERKOENIG_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")

# Liste von Städten
staedte = [
    "Berlin", "Hamburg", "München", "Köln", "Frankfurt", "Stuttgart", "Düsseldorf",
    "Leipzig", "Dortmund", "Essen", "Bremen", "Dresden", "Hannover", "Nürnberg",
    "Duisburg", "Bochum", "Wuppertal", "Bielefeld", "Bonn", "Münster"
]

RADIUS = 25
SORTIERUNG = "dist"
TYPE = "all"

geolocator = Nominatim(user_agent="benzinprojekt")

# Heutiges UTC-Datum (ohne Uhrzeit)
heute = datetime.now(timezone.utc).date()

client = MongoClient(MONGODB_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["benzinprojekt"]
collection = db["tankstellen"]

# Nur Einträge mit heutigem Datum löschen
result = collection.delete_many({
    "timestamp": {
        "$gte": datetime.combine(heute, datetime.min.time(), tzinfo=timezone.utc),
        "$lt": datetime.combine(heute, datetime.max.time(), tzinfo=timezone.utc)
    }
})
print(f"{result.deleted_count} Einträge von heute gelöscht.")

gesamtanzahl = 0

for ort in staedte:
    location = geolocator.geocode(ort)

    if not location:
        print(f"Ort '{ort}' nicht gefunden.")
        continue

    lat, lng = location.latitude, location.longitude

    url = (
        "https://creativecommons.tankerkoenig.de/json/list.php"
        f"?lat={lat}&lng={lng}&rad={RADIUS}&sort={SORTIERUNG}&type={TYPE}&apikey={api_key}"
    )

    print(f"📡 Anfrage für {ort} wird gesendet...")
    response = requests.get(url)
    data = response.json()

    if not data.get("ok"):
        print(f"Fehler bei der API für {ort}: {data}")
        continue

    stations = data.get("stations", [])
    print(f"✅ {len(stations)} Tankstellen in {ort} gefunden.")

    timestamp = datetime.now(timezone.utc)

    for station in stations:
        station["timestamp"] = timestamp
        station["ort"] = ort

    if stations:
        collection.insert_many(stations)
        gesamtanzahl += len(stations)

    time.sleep(1.5)

print(f"Gesamt: {gesamtanzahl} neue Einträge hinzugefügt.")
