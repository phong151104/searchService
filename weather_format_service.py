import traceback
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
import re

from common_service import CommonService  # hoặc from .common_service import CommonService nếu bạn đang để trong package

class WeatherFormatService(CommonService):
    service_name = "weather_format_service"

    # Mapping từ icon_id sang title tiếng Việt
    ICON_TITLES = {
        "1": "trời nắng", "30": "trời nắng",
        "2": "nắng nhẹ và có mây", "3": "nắng nhẹ và có mây", "4": "nắng nhẹ và có mây", "5": "nắng nhẹ và có mây", "6": "nắng nhẹ và có mây",
        "7": "nhiều mây", "32": "mây rải rác", "33": "mây rải rác", "34": "mây rải rác", "35": "mây rải rác", "36": "mây rải rác", "37": "mây rải rác", "38": "mây rải rác",
        "8": "nhiều mây", "11": "nhiều mây",
        "12": "mưa nhẹ, trời nhiều mây", "13": "mưa nhẹ, trời nhiều mây", "14": "mưa nhẹ, trời nhiều mây", "39": "mưa nhẹ, trời nhiều mây", "40": "mưa nhẹ, trời nhiều mây",
        "15": "mưa to có sấm sét", "16": "mưa to có sấm sét", "17": "mưa to có sấm sét", "41": "mưa to có sấm sét", "42": "mưa to có sấm sét",
        "18": "trời mưa",
        "29": "mưa có tuyết",
        "19": "có tuyết", "20": "có tuyết", "21": "có tuyết", "22": "có tuyết", "23": "có tuyết", "24": "có tuyết",
        "25": "có tuyết", "26": "có tuyết", "31": "có tuyết", "43": "có tuyết", "44": "có tuyết",
    }

    def __init__(self):
        super(WeatherFormatService, self).__init__()

    def process(self, json_data, log):
        response = {"message": "Success", "status": 200}

        try:
            city = json_data.get("city", "").strip()
            if not city:
                response.update(message="Bạn chưa cung cấp thành phố.", status=400)
                return response

            log.debug(f"Truy vấn thời tiết format cho thành phố: [{city}]")
            weather_data = self.get_weather_from_accuweather(city)

            if "error" in weather_data:
                response.update(
                    message=weather_data["error"],
                    status=500,
                    source=weather_data.get("source", "")
                )
            else:
                formatted_context = self.format_weather_context(weather_data)
                markdown_table = self.build_markdown_table(weather_data.get("10_day_forecast", []))

                weather_data.update(
                    formatted_context=formatted_context,
                    markdown_table=markdown_table
                )
                response.update({"city": city, **weather_data})

        except Exception as e:
            log.error("WeatherFormatService lỗi:", exc_info=True)
            response.update(
                message="Internal error",
                status=500,
                error=repr(e),
                trace=traceback.format_exc()
            )

        return response

    @staticmethod
    def build_markdown_table(forecast_list):
        # Header của bảng
        lines = [
            "| Date | Day     | Day Forecast                 | High | Low | Night Forecast                | Precipitation |",
            "| ---- | ------- | ---------------------------- | ---- | --- | ----------------------------- | ------------- |"
        ]
        for day in forecast_list:
            date = day.get("date", "-") or "-"
            dow = day.get("day", "-") or "-"
            
            day_fc = day.get("day_forecast", "-") or "-"
            # Loại bỏ phần night forecast dính trong day_forecast
            if "Night:" in day_fc:
                day_fc = day_fc.split("Night:")[0].strip()
            # Tách day_forecast và night_forecast nếu bị dính không có "Night:"
            day_fc = re.sub(r'([a-z])([A-Z])', r'\1<br>\2', day_fc)
            
            high_temp = day.get("high_temp", "-") or "-"
            
            low_temp = day.get("low_temp", "-") or "-"
            # Sửa giá trị low_temp không hợp lệ thành dấu gạch ngang
            if not re.match(r'^\d+°$', low_temp):
                low_temp = "–"
            
            night_fc = day.get("night_forecast", "-") or "-"
            if night_fc == "-":
                night_fc = "–"
            elif night_fc.startswith("Night:"):
                night_fc = night_fc[6:].strip()
            
            precip = day.get("precipitation", "-") or "-"
            
            lines.append(f"| {date:<5} | {dow:<7} | {day_fc:<28} | {high_temp:<4} | {low_temp:<3} | {night_fc:<28} | {precip:<12} |")
            
        return "\n".join(lines)


    @staticmethod
    def get_accuweather_url(city="Hanoi"):
        encoded = quote(city)
        search_url = f"https://www.accuweather.com/en/search-locations?query={encoded}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        results = soup.select_one("div.locations-list.content-module")
        if not results:
            return None

        first = results.select_one("a[href]")
        if not first:
            return None

        href = first["href"]
        if href.startswith("/web-api/three-day-redirect"):
            redirect = requests.get(
                urljoin("https://www.accuweather.com", href),
                headers=headers,
                allow_redirects=False
            )
            loc = redirect.headers.get("Location")
            return urljoin("https://www.accuweather.com", loc) if loc else None

        return urljoin("https://www.accuweather.com", href)

    @staticmethod
    def parse_10_day_forecast(soup):
        data = []
        for item in soup.select("a.daily-list-item"):
            try:
                date_text = item.select_one("div.date > p:nth-child(2)").get_text(strip=True)
                day_name  = item.select_one("div.date > p.day").get_text(strip=True)
                temp_text = item.select_one("div.temp").get_text(strip=True)
                temps     = temp_text.split("°")
                high      = temps[0] + "°" if temps else None
                low       = temps[1] + "°" if len(temps)>1 else None
                phrase    = item.select_one("div.phrase").get_text(strip=True)
                night     = item.select_one("span.night").get_text(strip=True) if item.select_one("span.night") else None
                precip    = item.select_one("div.precip").get_text(strip=True)
                data.append({
                    "day": day_name,
                    "date": date_text,
                    "high_temp": high,
                    "low_temp": low,
                    "day_forecast": phrase,
                    "night_forecast": night,
                    "precipitation": precip
                })
            except Exception:
                data.append({"error": "parse error"})
        return data

    @staticmethod
    def parse_accuweather_weather(url):
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        def safe_text(sel):
            el = soup.select_one(sel)
            return el.text.strip() if el else None

        def find_label(lbl):
            for blk in soup.select("div.spaced-content.detail"):
                l = blk.select_one("span.label")
                v = blk.select_one("span.value")
                if l and v and l.text.strip().lower() == lbl.lower():
                    return v.text.strip()
            return None

        # RealFeel
        rf = safe_text("div.real-feel")
        realfeel = re.search(r"\d+°", rf).group(0) if rf and re.search(r"\d+°", rf) else None

        # Allergy
        allergy_type = allergy_level = None
        hi = soup.select_one("a.health-activities__item.show")
        if hi:
            name = hi.select_one("span.health-activities__item__name")
            cat = hi.select_one("span.health-activities__item__category")
            allergy_type = name.get_text(strip=True) if name else None
            allergy_level = cat.get_text(strip=True) if cat else None

        # Today forecast
        body = soup.select("div.today-forecast-card.content-module div.body-item")
        day_fc   = " ".join(p.get_text(strip=True) for p in (body[0].select("p") if len(body)>0 else []))
        night_fc = " ".join(p.get_text(strip=True) for p in (body[1].select("p") if len(body)>1 else []))

        # 10-day
        forecast_10d = WeatherFormatService.parse_10_day_forecast(soup)

        # Icon + title
        icon_el = soup.select_one("svg.weather-icon")
        path    = icon_el.get("data-src") if icon_el else None
        icon_url= urljoin("https://www.accuweather.com", path) if path else None
        icon_id = title = None
        if path:
            m = re.search(r"/(\d+)\.svg", path)
            if m:
                icon_id = m.group(1)
                title   = WeatherFormatService.ICON_TITLES.get(icon_id)

        return {
            "temperature":  safe_text("div.temp-container > div.temp"),
            "realfeel":     realfeel,
            "description":  safe_text("span.phrase"),
            "wind":         find_label("Wind"),
            "wind_gusts":   find_label("Wind Gusts"),
            "air_quality":  find_label("Air Quality"),
            "allergy_type": allergy_type,
            "allergy_level":allergy_level,

            "icon_url": icon_url,
            "icon_id":  icon_id,
            "title":    title,

            "day_forecast":   day_fc,
            "night_forecast": night_fc,

            "today_date":      forecast_10d[0].get("date")      if forecast_10d else None,
            "today_day_name":  forecast_10d[0].get("day")       if forecast_10d else None,
            "today_high_temp": forecast_10d[0].get("high_temp")if forecast_10d else None,
            "today_low_temp":  forecast_10d[0].get("low_temp") if forecast_10d else None,
            "today_precip":    forecast_10d[0].get("precipitation") if forecast_10d else None,

            "10_day_forecast": forecast_10d,

            # đây là bảng markdown
            "markdown_table": None,  # sẽ được set bên ngoài

            "source": url
        }

    @classmethod
    def get_weather_from_accuweather(cls, city="Hanoi"):
        url = cls.get_accuweather_url(city)
        if not url:
            return {"error": f"Không tìm được thông tin thời tiết cho thành phố: {city}"}
        data = cls.parse_accuweather_weather(url)
        # sau khi có forecast_10d, build markdown_table
        if "10_day_forecast" in data:
            data["markdown_table"] = cls.build_markdown_table(data["10_day_forecast"])
        return data

    @staticmethod
    def format_weather_context(weather_data):
        parts = []
        parts.append("Thời tiết hiện tại tại địa phương:")
        parts.append(f"- Tiêu đề: {weather_data.get('title')}.")
        parts.append(f"- Nhiệt độ: {weather_data.get('temperature')}, cảm giác như {weather_data.get('realfeel')}.")
        parts.append(f"- Trạng thái: {weather_data.get('description')}.")
        wind = weather_data.get('wind')
        gust = weather_data.get('wind_gusts')
        if wind:
            parts.append(f"- Gió: {wind}" + (f", giật {gust}" if gust else "") + ".")
        if weather_data.get('air_quality'):
            parts.append(f"- Chất lượng không khí: {weather_data.get('air_quality')}.")

        parts.append("\nDự báo hôm nay:")
        parts.append(f"- Ban ngày: {weather_data.get('day_forecast')}.")
        parts.append(f"- Ban đêm: {weather_data.get('night_forecast')}.")

        flist = weather_data.get("10_day_forecast", [])
        if flist:
            parts.append("\nDự báo chi tiết 10 ngày tới:")
            for day in flist:
                d = day.get('date')
                dn= day.get('day')
                ht= day.get('high_temp')
                lt= day.get('low_temp')
                df= day.get('day_forecast')
                nf= day.get('night_forecast')
                pp= day.get('precipitation')
                parts.append(f"Ngày {d} ({dn}):")
                parts.append(f"  - Dự báo ban ngày: {df}.")
                parts.append(f"  - Dự báo ban đêm: {nf}.")
                parts.append(f"  - Nhiệt độ cao nhất: {ht}.")
                parts.append(f"  - Nhiệt độ thấp nhất: {lt}.")
                parts.append(f"  - Xác suất mưa: {pp}.")

        return "\n".join(parts)