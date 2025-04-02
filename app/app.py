from flask import Flask, request
import pandas as pd
from pymongo import MongoClient
from bson.regex import Regex
from datetime import datetime
import os
from dotenv import load_dotenv
from forecast_model import get_station_prices, predict_prices

def format_date_de(date_obj):
    days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    months = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
    return f"{days[date_obj.weekday()]}, {date_obj.day:02d}. {months[date_obj.month - 1]} {date_obj.year}"

load_dotenv()

app = Flask(__name__)
client = MongoClient(os.getenv("MONGODB_URI"), tls=True, tlsAllowInvalidCertificates=True)
db = client["benzinprojekt"]
collection = db["tankstellen"]

def get_available_cities():
    return sorted(collection.distinct("ort"))

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>⛽ Benzinpreis-Suche</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #f8fafc;
            color: #333;
            max-width: 900px;
            margin: 40px auto;
            padding: 30px;
        }}
        h1 {{ color: #2b6777; }}
        .card {{
            background: #eef6f9;
            border-left: 6px solid #2b6777;
            margin-bottom: 16px;
            padding: 12px 20px;
            border-radius: 8px;
        }}
        .box {{
            background: #fff3cd;
            padding: 15px 20px;
            border-left: 5px solid #ffca2c;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .forecast-table {{
            display: grid;
            grid-template-columns: 220px 80px 30px auto 60px;
            gap: 3px 10px;
            margin: 15px 0;
        }}
        .forecast-table span {{
            padding: 2px 0;
        }}
        .section-title {{
            font-weight: 600;
            margin-top: 10px;
            margin-bottom: 5px;
        }}
        .filter-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr auto;
            align-items: end;
            gap: 15px;
            margin-bottom: 20px;
        }}
        .filter-grid label {{
            font-weight: 600;
            display: block;
            margin-bottom: 5px;
        }}
        .filter-grid .fuel-group {{
            display: flex;
            gap: 10px;
        }}
        .filter-grid input[type="submit"] {{
            background-color: #2ecc71;
            color: white;
            padding: 8px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <h1>🔍 Benzinpreis-Suche</h1>
    <form method="post">
        <div class="filter-grid">
            <div>
                <label for="ort">Städte</label>
                <select name="ort">
                    {city_options}
                </select>
            </div>
            <div>
                <label>Kraftstoff</label>
                <div class="fuel-group">
                    <label><input type="radio" name="kraftstoff" value="e5" {e5}> E5</label>
                    <label><input type="radio" name="kraftstoff" value="e10" {e10}> E10</label>
                    <label><input type="radio" name="kraftstoff" value="diesel" {diesel}> Diesel</label>
                </div>
            </div>
            <div>
                <label for="radius">Umkreis</label>
                <select name="radius">
                    <option value="1" {r1}>1 km</option>
                    <option value="2" {r2}>2 km</option>
                    <option value="5" {r5}>5 km</option>
                    <option value="10" {r10}>10 km</option>
                    <option value="25" {r25}>25 km</option>
                </select>
            </div>
            <div>
                <input type="submit" value="Suchen">
            </div>
        </div>
        {result}
    </form>
</body>
</html>
'''

@app.route("/", methods=["GET", "POST"])
def index():
    ort = ""
    kraftstoff = "e5"
    radius = 5
    result_html = ""

    cities = get_available_cities()
    if not cities:
        return "❌ Keine Städte gefunden."

    if request.method == "POST":
        ort = request.form.get("ort", cities[0])
        kraftstoff = request.form.get("kraftstoff", "e5")
        radius = int(request.form.get("radius", 5))
        today = datetime.utcnow().date()

        query = {
            "ort": Regex(f"^{ort}$", "i"),
            kraftstoff: {"$ne": None},
            "timestamp": {
                "$gte": datetime(today.year, today.month, today.day),
                "$lt": datetime(today.year, today.month, today.day, 23, 59, 59)
            }
        }
        projection = {"_id": 0, "name": 1, "brand": 1, "street": 1, "postCode": 1, "dist": 1, kraftstoff: 1}
        results = list(collection.find(query, projection))
        results = [r for r in results if isinstance(r.get("dist"), (int, float)) and r["dist"] <= radius]

        df = get_station_prices(ort, kraftstoff=kraftstoff, radius_km=radius)
        forecast_df, recommendation = predict_prices(df, kraftstoff=kraftstoff)

        best_today = None
        if results:
            valid_today = [r for r in results if isinstance(r.get(kraftstoff), (int, float))]
            if valid_today:
                best_today = min(valid_today, key=lambda x: x[kraftstoff])

        if not results and (not isinstance(forecast_df, pd.DataFrame) or forecast_df.empty):
            result_html = f"<p>❌ Keine Tankstellen gefunden für '{ort}' mit diesen Einstellungen.</p>"
        else:
            if best_today:
                result_html += f'''
                <div class='box'>
                    <div class="section-title">🚗 Billigste Tankstelle heute im ausgewählten Umkreis von {radius} km für Kraftstoff {kraftstoff.upper()} in der Stadt {ort.title()}:</div>
                    <div class='forecast-table'>
                        <span>{format_date_de(today)}</span>
                        <span>{best_today[kraftstoff]:.2f} €/L</span>
                        <span>→</span>
                        <span>{best_today.get("brand", "")} – {best_today.get("name", "")}</span>
                        <span>{best_today.get("dist", "?")} km</span>
                    </div>
                </div>
                '''

            if not forecast_df.empty:
                result_html += "<div class='box'><div class='section-title'>🧙 Prognose für die nächsten 5 Tage:</div><div class='forecast-table'>"
                for _, row in forecast_df.iterrows():
                    distance = f"{row['distance']:.1f} km" if "distance" in row and pd.notnull(row["distance"]) else "- km"
                    result_html += f'''
                    <span>{format_date_de(row["date"])}</span>
                    <span>{row["price"]:.2f} €/L</span>
                    <span>→</span>
                    <span>{row["brand"]} – {row["name"]}</span>
                    <span>{distance}</span>
                    '''
                result_html += "</div></div>"
            if best_today and recommendation:
                if best_today[kraftstoff] < recommendation["price"]:
                    recommendation = {
            "date": today.strftime("%Y-%m-%d"),
            "price": best_today[kraftstoff],
            "brand": best_today.get("brand", ""),
            "name": best_today.get("name", ""),
            "distance": best_today.get("dist", "?")
        }
        if recommendation:
            result_html += f'''
            <div class='box'>
                <div class='section-title'>💡 Empfehlung - Bester Tag zum Tanken:</div>
                <div class='forecast-table'>
                    <span>{format_date_de(datetime.strptime(recommendation["date"], "%Y-%m-%d"))}</span>
                    <span>{recommendation["price"]:.2f} €/L</span>
                    <span>→</span>
                    <span>{recommendation["brand"]} – {recommendation["name"]}</span>
                    <span>{recommendation.get("distance", "?"):.1f} km</span>
                </div>
            </div>
        '''


            if results:
                result_html += f"<h2>⛽ {len(results)} Ergebnisse für '{ort.title()}' (Kraftstoff: {kraftstoff.upper()}, Umkreis: {radius} km):</h2>"
                for t in results:
                    preis = f"{t.get(kraftstoff, 0):.2f} €/L" if isinstance(t.get(kraftstoff), (int, float)) else "n/a"
                    dist = f"{t.get('dist', '?')} km"
                    result_html += f"<div class='card'><strong>{t['brand']} – {t['name']}</strong><br>{kraftstoff.upper()}: {preis} – 📍 {dist}</div>"

    flags = {
        "e5": "checked" if kraftstoff == "e5" else "",
        "e10": "checked" if kraftstoff == "e10" else "",
        "diesel": "checked" if kraftstoff == "diesel" else "",
        "r1": "selected" if radius == 1 else "",
        "r2": "selected" if radius == 2 else "",
        "r5": "selected" if radius == 5 else "",
        "r10": "selected" if radius == 10 else "",
        "r25": "selected" if radius == 25 else ""
    }

    city_options = "\n".join([f"<option value='{city}' {'selected' if city == ort else ''}>{city}</option>" for city in cities])

    return HTML_TEMPLATE.format(result=result_html, ort=ort, kraftstoff=kraftstoff, radius=radius, city_options=city_options, **flags)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
