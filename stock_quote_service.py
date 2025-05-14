# stock_quote_service.py

import re
import traceback
import requests
from bs4 import BeautifulSoup
from common_service import CommonService

class StockQuoteService(CommonService):
    service_name = "stock_quote_service"
    ROOT_URL     = "https://finance.vietstock.vn"

    def __init__(self):
        super(StockQuoteService, self).__init__()

    def process(self, json_data, log):
        response = {
            "message": "Success!",
            "status": 200,
            "data": [],
            "url": None,
            "top_results": None
        }
        try:
            symbol = (json_data.get("stock_code") or "").strip().upper()
            if not symbol:
                response.update({"message": "Bạn chưa cung cấp mã chứng khoán.", "status": 400})
                return response

            log.debug("Input: %s", json_data)

            # --- Bắt ValueError riêng để trả về 404 ---
            try:
                url = self._resolve_stock_url(symbol)
            except ValueError as e:
                response.update({"message": str(e), "status": 404})
                return response

            response["url"] = url

            # 3. Scrape thông tin
            info = self._get_stock_info(url)
            response["data"].append({
                "symbol": symbol,
                "url":    url,
                "info":   info
            })

            log.debug("Response: %s", response)

        except Exception as e:
            log.error(traceback.format_exc())
            response.update({"message": str(e), "status": 500})

        return response

    def _resolve_stock_url(self, symbol: str) -> str:
        """
        1) GET ROOT_URL, parse datalist hoặc ul.search-suggest để tìm slug
        2) Fallback: scan toàn bộ <a href> để match pattern /<symbol>-...\.htm
        """
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(self.ROOT_URL, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")

        # 1) datalist autocomplete
        dl = soup.find("datalist", id="lstSymbol")
        if dl:
            for opt in dl.find_all("option"):
                val = opt.get("value", "")
                if val.upper().startswith(f"/{symbol}"):
                    return self.ROOT_URL + val

        # 2) UL search-suggest
        for a in soup.select("ul.search-suggest a"):
            if a.text.strip().upper() == symbol:
                return self.ROOT_URL + a["href"]

        # 3) General fallback: scan mọi <a> để match /SYMBOL-...htm
        pattern = re.compile(rf"^/{symbol.lower()}-.+\.htm$")
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if pattern.match(href):
                return self.ROOT_URL + a["href"]

        # Không tìm được slug nào
        raise ValueError(f"Không tìm thấy trang chi tiết cho mã '{symbol}'")

    def _get_stock_info(self, url: str) -> dict:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")

        # ==== Ví dụ selector, bạn cần inspect lại cho chính xác ====
        price   = soup.select_one("div.box-price span.value").get_text(strip=True)
        change  = soup.select_one("div.box-price span.change").get_text(strip=True)
        percent = soup.select_one("div.box-price span.percent").get_text(strip=True)
        time_   = soup.select_one("div.box-price span.time").get_text(strip=True)

        full_name = soup.select_one("h1.company-name").get_text(strip=True)

        stats = {}
        table = soup.select_one("table.table-static")
        if table:
            for row in table.select("tr"):
                cols = [td.get_text(strip=True) for td in row.select("td")]
                if len(cols) >= 2:
                    stats[cols[0]] = cols[1]

        return {
            "price":     price,
            "change":    change,
            "percent":   percent,
            "time":      time_,
            "full_name": full_name,
            **stats
        }
