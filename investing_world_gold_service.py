import traceback
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from common_service import CommonService

class InvestingWorldGoldService(CommonService):
    service_name = "investing_world_gold_service"

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive"
        })

    def process(self, json_data, log):
        response = {"message": "Success", "status": 200}
        try:
            url = "https://vn.investing.com/currencies/xau-usd"
            res = self.session.get(url, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            # Giá vàng XAU/USD
            price_el = soup.find("div", {"data-test": "instrument-price-last"})
            price = price_el.text.strip().replace(",", "") if price_el else None

            # Thay đổi và phần trăm thay đổi
            change_el = soup.find("span", {"data-test": "instrument-price-change"})
            change = change_el.text.strip().replace(",", "") if change_el else None
            percent_el = soup.find("span", {"data-test": "instrument-price-change-percent"})
            percent = percent_el.text.strip() if percent_el else None

            # Thời gian cập nhật
            time_el = soup.find("time", {"data-test": "trading-time-label"})
            updated_at = time_el.text.strip() if time_el else None

            # Biên độ ngày
            day_range = None
            day_range_els = soup.find_all("div", string=lambda s: s and "Biên độ ngày" in s)
            if day_range_els:
                parent = day_range_els[0].find_parent()
                if parent:
                    spans = parent.find_all("span")
                    if len(spans) >= 2:
                        day_range = (spans[0].text.strip(), spans[1].text.strip())

            # Biên độ 52 tuần
            week52_range = None
            week52_els = soup.find_all("div", string=lambda s: s and "Biên độ 52 tuần" in s)
            if week52_els:
                parent = week52_els[0].find_parent()
                if parent:
                    spans = parent.find_all("span")
                    if len(spans) >= 2:
                        week52_range = (spans[0].text.strip(), spans[1].text.strip())

            response.update({
                "price": price,
                "change": change,
                "percent": percent,
                "updated_at": updated_at,
                "day_range": day_range,
                "week52_range": week52_range,
                "source": url
            })
        except Exception as e:
            log.error(traceback.format_exc())
            response.update({"message": str(e), "status": 500})
        return response 