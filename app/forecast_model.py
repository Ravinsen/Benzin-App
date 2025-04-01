# model/forecast_model.py

import os
from dotenv import load_dotenv
from pymongo import MongoClient
import pandas as pd
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from sklearn.linear_model import LinearRegression
import numpy as np
import locale

# 🌍 Datum auf Deutsch anzeigen (soweit möglich)
try:
    locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "de_DE")
    except locale.Error:
        print("⚠️ Deutsche Locale konnte nicht gesetzt werden – benutze Default-Format.")

# 🔐 MongoDB-Verbindung
load_dotenv()
client = MongoClient(os.getenv("MONGODB_URI"), tls=True, tlsAllowInvalidCertificates=True)
db = client["benzinprojekt"]
collection = db["tankstellen"]

# 📥 Preise für Ort und Radius abrufen
def get_station_prices(ort, kraftstoff="e5", radius_km=5):
    geolocator = Nominatim(user_agent="benzinprojekt")
    location = geolocator.geocode(ort)
    if not location:
        return pd.DataFrame()

    center = (location.latitude, location.longitude)

    data = list(collection.find(
        {
            kraftstoff: {"$exists": True, "$ne": None}  # ✅ nur gültige Werte
        },
        {
            "timestamp": 1,
            "name": 1,
            "brand": 1,
            "place": 1,
            "lat": 1,
            "lng": 1,
            kraftstoff: 1
        }
    ))

    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame()

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date
    df["distance"] = df.apply(lambda row: geodesic(center, (row["lat"], row["lng"])).km, axis=1)
    df = df[df["distance"] <= radius_km]

    return df if not df.empty else pd.DataFrame()

# 🔮 Preisvorhersage für 5 Tage + Empfehlung (inkl. heute)
def predict_prices(df, kraftstoff="e5"):
    if df.empty or len(df["date"].unique()) < 2:
        return [], {}

    forecast_result = []

    for station_id in df["name"].unique():
        sub_df = df[df["name"] == station_id].copy()
        sub_df["day"] = (pd.to_datetime(sub_df["date"]) - pd.to_datetime(sub_df["date"]).min()).dt.days
        X = sub_df["day"].values.reshape(-1, 1)
        y = sub_df[kraftstoff].astype(float).values
        if len(X) < 2:
            continue

        model = LinearRegression().fit(X, y)
        future_days = np.array([sub_df["day"].max() + i for i in range(1, 6)])
        preds = model.predict(future_days.reshape(-1, 1))
        station_info = df[df["name"] == station_id].iloc[0]

        for i, pred in enumerate(preds):
            day = pd.to_datetime(sub_df["date"]).max() + timedelta(days=i + 1)
            pred_rounded = round(pred, 2)
            forecast_result.append({
                "date": day,
                "price": pred_rounded,
                "name": station_info["name"],
                "brand": station_info["brand"],
                "distance": station_info.get("distance", None)
            })

    df_forecast = pd.DataFrame(forecast_result)
    df_today = df[df["date"] == df["date"].max()][["date", kraftstoff, "name", "brand", "distance"]]
    df_today = df_today.rename(columns={kraftstoff: "price"})

    df_combined = pd.concat([df_forecast, df_today], ignore_index=True)
    if df_combined.empty:
        return [], {}

    df_combined["date"] = pd.to_datetime(df_combined["date"])
    best_per_day = df_forecast.loc[df_forecast.groupby("date")["price"].idxmin()].sort_values("date")

    # 🔍 Günstigster Tag (heute oder Prognose)
    best_entry = df_combined.loc[df_combined["price"].idxmin()]
    recommendation = {
        "date": best_entry["date"].strftime("%Y-%m-%d"),
        "price": best_entry["price"],
        "name": best_entry["name"],
        "brand": best_entry["brand"],
        "distance": best_entry.get("distance", None)
    }

    return best_per_day, recommendation
