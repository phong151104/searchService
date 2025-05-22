import traceback
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup

from common_service import CommonService


class StockInfoService(CommonService):
    service_name = "stock_info_service"

    def __init__(self):
        super().__init__()

    def process(self, json_data, log):
        response = {
            "message": "",
            "status": 200,
            "change": None,
            "name": None,
            "stock_code": None,
            "trading_date": None,
            "per_change": None,
            "last_price": None,
            "full_name": None,
            "trading_status_name": None,
            "url": None,
            "summary": {},
            "chart_data": [],
            "chart_data_day": [],
            "formated_context": ""
        }

        try:
            # 1) Đọc query và symbol
            query = (json_data.get("query") or json_data.get("message") or "").strip()
            if not query:
                response.update({"message": "Bạn chưa cung cấp chuỗi tìm kiếm.", "status": 400})
                return response

            symbol = query.split()[-1].upper()
            response["stock_code"] = symbol

            # 2) Lấy URL chi tiết từ serp
            raw_results = self.serp.search(message=query, num_results=1)
            if not raw_results:
                response.update({
                    "message": f"Không tìm thấy kết quả cho '{query}'.",
                    "status": 404
                })
                return response

            first = raw_results[0]
            url = first["link"] if isinstance(first, dict) else first
            if not url:
                response.update({
                    "message": "Không tìm thấy link trong kết quả.",
                    "status": 404
                })
                return response
            response["url"] = url

            # 3) Fetch & parse HTML
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            # 4) Lấy vùng chứa giá
            row = soup.select_one("div.row.stock-price-info")
            if not row:
                raise ValueError("Không tìm thấy khu vực stock-price-info trên trang.")

            # — last_price —
            el_price = row.select_one("h2#stockprice span.price")
            last_price = None
            if el_price:
                try:
                    last_price = float(el_price.text.replace(",", ""))
                except:
                    pass
            response["last_price"] = last_price

            # — change & per_change —
            change = per_change = None
            el_change = row.select_one("div#stockchange")
            if el_change:
                txt = el_change.get_text(" ", strip=True)
                m = re.search(r"([+\-]?[0-9,\.]+)\s*\(\s*([+\-]?[0-9\.]+)%\s*\)", txt)
                if m:
                    change = float(m.group(1).replace(",", ""))
                    per_change = float(m.group(2))
                else:
                    try:
                        change = float(txt.replace(",", "").split()[0])
                    except:
                        pass
            response["change"] = change
            response["per_change"] = per_change

            # — trading_date —
            trading_date = None
            el_date = row.select_one("div#tradedate")
            if el_date:
                dt_txt = el_date.get_text(strip=True)
                datetime.strptime(dt_txt, "%d/%m/%Y %H:%M")
                trading_date = dt_txt
            response["trading_date"] = trading_date

            # — trading_status_name —
            trading_status = None
            el_status = row.select_one("small#tradingstatus")
            if el_status:
                trading_status = el_status.get_text(strip=True)
            response["trading_status_name"] = trading_status

            # — full_name & name —
            full_el = soup.select_one("h2.title-2.text")
            full_name = full_el.get_text(strip=True) if full_el else None
            response["full_name"] = full_name
            response["name"] = symbol

            # 5) Lấy summary
            summary = {}
            for p in row.select("p.p8"):
                b = p.find("b")
                if not b:
                    continue
                value = b.get_text(strip=True)
                key = p.get_text("|||", strip=True).split("|||")[0].strip(": ")
                summary[key] = value
            response["summary"] = summary

            # Prepare session & token
            stock_url = f"https://finance.vietstock.vn/{symbol}-ctcp-{symbol.lower()}.htm"
            session = requests.Session()
            session.headers.update({"User-Agent": "Mozilla/5.0"})
            r = session.get(stock_url)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            token_input = soup.find("input", {"name": "__RequestVerificationToken"})
            token = token_input["value"] if token_input else session.cookies.get("__RequestVerificationToken", "")
            cookies = session.cookies.get_dict()
            post_headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
                "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items())
            }

            # 6) Lấy dữ liệu biểu đồ 12 tháng
            chart_url = "https://finance.vietstock.vn/data/getstockdealdetailbytime"
            chart_payload = {
                "code": symbol,
                "seq": 0,
                "timetype": "1Y",
                "tradingDate": "",
                "__RequestVerificationToken": token
            }
            cj = session.post(chart_url, data=chart_payload, headers=post_headers)
            cj.raise_for_status()
            chart_js = cj.json()
            data = chart_js if isinstance(chart_js, list) else chart_js.get("Data", [])
            # Format & trim chart_data
            for d in data:
                if d.get("TradingDate", "").startswith("/Date("):
                    ts = int(d["TradingDate"].split("(")[1].split(")")[0]) // 1000
                    d["TradingDate"] = datetime.fromtimestamp(ts).strftime("%d/%m/%Y")
                for k in ("Min", "Max", "Package", "Timetype", "TradingDateStr"):
                    d.pop(k, None)
            response["chart_data"] = data

            # 6.1) Lấy dữ liệu biểu đồ ngày
            daily_chart_url = "https://finance.vietstock.vn/data/getstockdealdetailchart"
            daily_payload = {
                "code": symbol,
                "interval": 1,
                "__RequestVerificationToken": token
            }
            dj = session.post(daily_chart_url, data=daily_payload, headers=post_headers)
            dj.raise_for_status()
            daily_js = dj.json()
            daily_data = daily_js if isinstance(daily_js, list) else daily_js.get("Data", [])
            # Format & trim chart_data_day
            for d in daily_data:
                raw = d.get("TradingDate", "")
                if raw.startswith("/Date(") and raw.endswith(")/"):
                    ms = int(raw[6:-2])
                    dt = datetime.fromtimestamp(ms / 1000)
                    d["TradingDateStr"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    d["TradingDateStr"] = None
                # Xóa các trường không mong muốn
                for k in ("isBuy", "IsBuy", "stockcode", "StockCode", "Stockcode", "TradingDate", "Package", "TotalVal", "TotalVol"):
                    d.pop(k, None)
            response["chart_data_day"] = daily_data

            # 7) Tạo formated_context (không bao gồm chart_data_day)
            #    Sắp xếp chart_data theo ngày giảm dần
            sorted_chart = []
            for d in response["chart_data"]:
                try:
                    dt = datetime.strptime(d["TradingDate"], "%d/%m/%Y")
                except:
                    dt = datetime.min
                sorted_chart.append((dt, d))
            sorted_chart.sort(key=lambda x: x[0], reverse=True)

            parts = [
                f"Mã cổ phiếu: {response['stock_code']}",
                f"Tên đầy đủ: {response['full_name']}",
                f"Ngày giao dịch: {response['trading_date']}",
                f"Giá hiện tại: {response['last_price']}",
                f"Chênh lệch: {response['change']} ({response['per_change']}%)",
                f"Trạng thái: {response['trading_status_name']}"
            ]
            for key, val in response["summary"].items():
                parts.append(f"{key}: {val}")
            # Thêm chart_data (1 năm) từ gần nhất
            for _, d in sorted_chart:
                parts.append(f"{d['TradingDate']}: Price {d.get('Price')} - Vol {d.get('Vol')}")

            response["formated_context"] = "; ".join(parts)
            response["message"] = "Success!"
        except Exception as e:
            log.error(traceback.format_exc())
            response.update({"message": str(e), "status": 500})

        return response