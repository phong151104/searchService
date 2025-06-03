import traceback
import requests
from bs4 import BeautifulSoup
from common_service import CommonService
import os
import urllib.parse
import datetime

class VietstockTopStockService(CommonService):
    service_name = "vietstock_top_stock_service"

    MARKET_CATID = {
        "HOSE": "1",
        "HNX": "2",
        "UPCOM": "3"
    }

    _cache = {}
    _cache_date = None

    def serp_search(self, query, log):
        try:
            api_key = os.environ.get('SERPAPI_API_KEY')
            if not api_key:
                log.error("SERPAPI_API_KEY not set")
                return None
            params = {
                "q": query,
                "engine": "google",
                "api_key": api_key,
                "num": 5,
                "hl": "vi"
            }
            res = requests.get("https://serpapi.com/search", params=params, timeout=15)
            res.raise_for_status()
            data = res.json()
            # Lấy link đầu tiên thuộc vietstock.vn
            for item in data.get("organic_results", []):
                link = item.get("link")
                if link and "vietstock.vn" in link:
                    return link
            return None
        except Exception as e:
            log.error(f"SERPAPI search error: {e}")
            return None

    def get_gui_from_detail(self, detail_url, log):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            res = requests.get(detail_url, headers=headers, timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            iframes = soup.find_all("iframe", src=lambda s: s and "gui=" in s)
            guis = []
            for iframe in iframes:
                src = iframe["src"]
                parsed = urllib.parse.urlparse(src)
                qs = urllib.parse.parse_qs(parsed.query)
                gui = qs.get("gui", [None])[0]
                if gui:
                    guis.append(gui)
            return guis
        except Exception as e:
            log.error(f"Lỗi lấy gui từ detail_url: {e}")
            return None

    def convert_vietstock_date(self, date_str):
        # Chuyển từ /Date(1748797200000)/ sang yyyy-mm-dd
        try:
            if not date_str or not date_str.startswith("/Date("):
                return date_str
            timestamp = int(date_str[6:-2]) // 1000
            dt = datetime.datetime.utcfromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d")
        except:
            return date_str

    def format_context(self, data):
        if not isinstance(data, list) or len(data) < 2:
            return "Không có dữ liệu phù hợp."
        tang, giam = data[0], data[1]
        lines = []
        if tang:
            lines.append("Top cổ phiếu tăng giá mạnh nhất:")
            for stock in tang:
                lines.append(f"- {stock.get('StockCode', '')}: giá {stock.get('LastPrice', ''):,} đồng, tăng {stock.get('PerChange', '')}% (KLGD TB: {stock.get('AvgVol', ''):,})")
        if giam:
            lines.append("Top cổ phiếu giảm giá mạnh nhất:")
            for stock in giam:
                lines.append(f"- {stock.get('StockCode', '')}: giá {stock.get('LastPrice', ''):,} đồng, giảm {abs(stock.get('PerChange', 0))}% (KLGD TB: {stock.get('AvgVol', ''):,})")
        return "\n".join(lines)

    def process(self, json_data, log):
        response = {"message": "Success", "status": 200}
        try:
            query = json_data.get("query")
            market = json_data.get("market", "HOSE").upper()
            catid = self.MARKET_CATID.get(market, "1")
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            cache_key = f"{query}|{market}|{today}"
            # Xóa cache nếu sang ngày mới
            if self._cache_date != today:
                self._cache = {}
                self._cache_date = today
            if cache_key in self._cache:
                log.debug(f"Trả về từ cache: {cache_key}")
                return self._cache[cache_key]
            if not query:
                response.update({"message": "Missing 'query' parameter", "status": 400})
                return response
            # 1. Search link bằng SerpAPI
            detail_url = self.serp_search(query, log)
            if not detail_url:
                response.update({"message": "Không tìm được link vietstock.vn phù hợp từ SerpAPI", "status": 404})
                return response
            # 2. Lấy gui từ detail_url
            guis = self.get_gui_from_detail(detail_url, log)
            if not guis:
                response.update({"message": f"Không lấy được gui từ {detail_url}", "status": 500})
                return response
            # 3. Gọi API Vietstock
            url = "https://finance.vietstock.vn/DrawChart/Cms3GetTopStockChange"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            payload = {
                "gui": guis[0],
                "catid": catid
            }
            res = requests.post(url, data=payload, headers=headers, timeout=10)
            res.raise_for_status()
            data = res.json()
            # Chuyển đổi trường ngày
            if isinstance(data, list):
                for group in data:
                    if isinstance(group, list):
                        for item in group:
                            if "LastUpdate" in item:
                                item["LastUpdate"] = self.convert_vietstock_date(item["LastUpdate"])
                            if "TradingDate" in item:
                                item["TradingDate"] = self.convert_vietstock_date(item["TradingDate"])
            response["data"] = data
            response["market"] = market
            response["catid"] = catid
            response["gui"] = guis[0]
            response["detail_url"] = detail_url
            response["source"] = url
            response["formatted_context"] = self.format_context(data)
            # Lưu cache
            self._cache[cache_key] = response.copy()
        except Exception as e:
            log.error(traceback.format_exc())
            response.update({"message": str(e), "status": 500})
        return response 