# Benzinpreis-Prognose-App

Diese Web-App hilft Nutzerinnen und Nutzern dabei, den besten Zeitpunkt zum Tanken zu ermitteln – basierend auf tagesaktuellen Daten deutscher Tankstellen sowie einer datenbasierten Prognose der nächsten fünf Tage. Die Anwendung kombiniert Preistransparenz mit intelligenter Vorhersage, um Autofahrern Einsparpotenziale aufzuzeigen.

## Warum diese App?

Steigende Kraftstoffpreise und regionale Unterschiede machen es zunehmend schwierig, den günstigsten Zeitpunkt und Ort zum Tanken zu identifizieren. Diese App bietet:

- Aktuelle Benzinpreise in über 20 deutschen Städten  
- Eine Prognose der Preise für die kommenden 5 Tage, basierend auf historischen Daten  
- Eine Empfehlung, ob heute oder in den nächsten Tagen der beste Zeitpunkt zum Tanken ist  
- Die Möglichkeit, Umkreis und Kraftstoffart individuell auszuwählen  

## Datenquelle

Die Daten stammen von der Tankerkönig API (https://tankerkoenig.de/), welche Preisinformationen lizenzierter deutscher Tankstellen zur Verfügung stellt. Täglich werden automatisiert rund 5'700 Tankstellen-Datensätze für die Kraftstoffarten E5 (Bleifrei 95), E10 (Bleifrei 98) und Diesel abgerufen und in einer Datenbank gespeichert.

## Features

- Standortbasierte Preisanalyse
- Auswahl des Kraftstofftyps (E5, E10, Diesel)  
- Radiusauswahl (1, 2, 5, 10, 25 km)  
- Tagesaktuelle Anzeige der günstigsten Tankstelle im gewählten Radius  
- Vorhersage der günstigsten Tankstelle für die nächsten 5 Tage  
- Empfehlungen basierend auf Preisprognosen  
- Anzeige aller Tankstellen im gewählten Radius unterhalb der Empfehlung  

## Technologiestack

- Backend: Python, Flask  
- Frontend: HTML, CSS (Inline), Bootstrap-Elemente  
- Machine Learning: Scikit-Learn (Lineare Regression)  
- Deployment: Azure App Service (Container Deployment via Docker)  
- Datenbank: MongoDB Atlas  
- Automatisierung: GitHub Actions (täglicher Datenimport)  
- Datenquelle: Tankerkönig API  

## Performanceoptimierung

- Koordinaten-Caching: Die Koordinaten der 20 Städte werden beim ersten Zugriff in einer coords_cache.json Datei gespeichert. So entfällt der wiederholte API-Aufruf bei weiteren Abfragen.  
- MongoDB-Indexes: Um die Lesegeschwindigkeit zu erhöhen, wurden Indexes auf den Feldern ort, timestamp und den drei Kraftstoffarten gesetzt.  
- Datenfilterung: Für die Vorhersage werden ausschließlich die letzten 60 Tage historischer Daten berücksichtigt.  

## Projektkontext

Diese Anwendung wurde im Rahmen des Projekts "Model Deployment & Maintenance" entwickelt und deckt zentrale Aspekte der Modellbereitstellung, Automatisierung und Cloud-Deployment ab.
