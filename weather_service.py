import traceback
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re
from urllib.parse import urljoin

from common_service import CommonService  # hoặc from .common_service import CommonService nếu bạn đang để trong package

class AccuweatherScraper:
    @staticmethod
    def get_accuweather_url(city="Hanoi"):
        encoded_city = quote(city)
        search_url = f"https://www.accuweather.com/en/search-locations?query={encoded_city}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        # Lấy đúng container kết quả
        results = soup.select_one("div.locations-list.content-module")
        if not results:
            return None

        first = results.select_one("a[href]")
        if not first:
            return None

        href = first["href"]

        # Nếu là redirect endpoint
        if href.startswith("/web-api/three-day-redirect"):
            redirect_resp = requests.get(
                urljoin("https://www.accuweather.com", href),
                headers=headers,
                allow_redirects=False
            )
            location = redirect_resp.headers.get("Location")
            # GHÉP domain nếu cần
            return urljoin("https://www.accuweather.com", location) if location else None

        # Ngược lại là link trực tiếp tới weather-forecast
        return urljoin("https://www.accuweather.com", href)

    @staticmethod
    def parse_10_day_forecast(soup):
        data = []
        for item in soup.select("a.daily-list-item"):
            try:
                date_text = item.select_one("div.date > p:nth-child(2)").get_text(strip=True)
                day_name  = item.select_one("div.date > p.day").get_text(strip=True)
                temps = item.select_one("div.temp").get_text(strip=True).split("°")
                phrase = item.select_one("div.phrase").get_text(strip=True)
                night = item.select_one("span.night")
                precip = item.select_one("div.precip").get_text(strip=True)
                data.append({
                    "day": day_name,
                    "date": date_text,
                    "high_temp": temps[0] + "°",
                    "low_temp":  temps[1] + "°",
                    "day_forecast": phrase,
                    "night_forecast": night.get_text(strip=True) if night else None,
                    "precipitation": precip
                })
            except Exception as e:
                data.append({"error": str(e)})
        return data

    @staticmethod
    def parse_accuweather_weather(url):
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        def safe(sel):
            e = soup.select_one(sel)
            return e.get_text(strip=True) if e else None

        def find_val(label):
            for blk in soup.select("div.spaced-content.detail"):
                lbl = blk.select_one("span.label")
                val = blk.select_one("span.value")
                if lbl and val and lbl.get_text(strip=True).lower() == label.lower():
                    return val.get_text(strip=True)
            return None

        try:
            realfeel = None
            rf = safe("div.real-feel")
            if rf:
                m = re.search(r"\d+°", rf)
                realfeel = m.group(0) if m else None

            # allergy
            allergy_type = allergy_level = None
            itm = soup.select_one("a.health-activities__item.show")
            if itm:
                name = itm.select_one("span.health-activities__item_name")
                cat  = itm.select_one("span.health-activities__item_category:not(.--unsupported)")
                allergy_type  = name.get_text(strip=True) if name else None
                allergy_level = cat .get_text(strip=True) if cat  else None

            # today forecast
            bodies = soup.select("div.today-forecast-card.content-module div.body-item")
            day_fc   = " ".join(p.get_text(strip=True) for p in bodies[0].select("p")) if len(bodies)>0 else None
            night_fc = " ".join(p.get_text(strip=True) for p in bodies[1].select("p")) if len(bodies)>1 else None

            ten_day = AccuweatherScraper.parse_10_day_forecast(soup)

            return {
                "temperature": safe("div.temp-container > div.temp"),
                "realfeel": realfeel,
                "description": safe("span.phrase"),
                "wind": find_val("Wind"),
                "wind_gusts": find_val("Wind Gusts"),
                "air_quality": find_val("Air Quality"),
                "allergy_type": allergy_type,
                "allergy_level": allergy_level,
                "day_forecast": day_fc,
                "night_forecast": night_fc,
                "10_day_forecast": ten_day,
                "source": url
            }
        except Exception as e:
            return {"error": f"Không lấy được dữ liệu: {e}", "source": url}

    @classmethod
    def get_weather_from_accuweather(cls, city="Hanoi"):
        url = cls.get_accuweather_url(city)
        if not url:
            return {"error": f"Không tìm thấy thời tiết cho {city}"}
        return cls.parse_accuweather_weather(url)


class WeatherServicePhong(CommonService):
    service_name = "weather_service_phong"

    def __init__(self):
        super().__init__()

    def process(self, json_data, log):
        response = {"message": "Success", "status": 200}
        try:
            city = json_data.get("city", "Hanoi")
            log.debug(f"[WeatherServicePhong] City = {city}")
            data = AccuweatherScraper.get_weather_from_accuweather(city)
            response["data"] = data
        except Exception as e:
            response["message"] = str(e)
            response["status"] = 500
            traceback.print_exc()
        return response
