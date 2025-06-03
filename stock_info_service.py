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
            # 1) Đọc query
            query = (json_data.get("query") or json_data.get("message") or "").strip()
            if not query:
                response.update({"message": "Bạn chưa cung cấp chuỗi tìm kiếm.", "status": 400})
                return response

            # 2) Lấy min_date, max_date
            min_date_str = (json_data.get("min_date") or "").strip()
            max_date_str = (json_data.get("max_date") or "").strip()
            min_dt = datetime.strptime(min_date_str, "%d/%m/%Y") if min_date_str else None
            max_dt = datetime.strptime(max_date_str, "%d/%m/%Y") if max_date_str else None

            # 3) Lấy URL chi tiết từ SERP
            # Chuẩn hóa lại query trước khi search
            q_parts = query.split()
            if len(q_parts) > 1:
                q_parts[-1] = q_parts[-1].upper()
                query = " ".join(q_parts)
            # sau đó gọi search
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

            # ---- LẤY SYMBOL CHUẨN TỪ URL ----
            m = re.search(r"https://finance\.vietstock\.vn/([A-Z0-9]+)-", url, re.I)
            if m:
                symbol = m.group(1).upper()
            else:
                symbol = query.split()[-1].upper()
            response["stock_code"] = symbol
            response["name"] = symbol

            # 4) Fetch & parse HTML
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            # 5) Lấy vùng chứa giá
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

            # — trading_date (DD/MM/YYYY HH:MM) —
            trading_date = None
            el_date = row.select_one("div#tradedate")
            if el_date:
                dt_txt = el_date.get_text(strip=True)  # ví dụ "17/05/2025 15:30"
                datetime.strptime(dt_txt, "%d/%m/%Y %H:%M")  # kiểm tra đúng định dạng
                trading_date = dt_txt
            response["trading_date"] = trading_date

            # — trading_status_name —
            trading_status = None
            el_status = row.select_one("small#tradingstatus")
            if el_status:
                trading_status = el_status.get_text(strip=True)
            response["trading_status_name"] = trading_status

            # — full_name —
            full_el = soup.select_one("h2.title-2.text")
            full_name = full_el.get_text(strip=True) if full_el else None
            response["full_name"] = full_name

            # 6) Lấy summary
            summary = {}
            for p in row.select("p.p8"):
                b = p.find("b")
                if not b:
                    continue
                value = b.get_text(strip=True)
                key = p.get_text("|||", strip=True).split("|||")[0].strip(": ")
                summary[key] = value
            response["summary"] = summary

            # 7) Lấy dữ liệu biểu đồ 12 tháng
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
            orig_data = chart_js if isinstance(chart_js, list) else chart_js.get("Data", [])

            # Format & trim chart_data (TradingDate → DD/MM/YYYY)
            for d in orig_data:
                if d.get("TradingDate", "").startswith("/Date("):
                    ts = int(d["TradingDate"].split("(")[1].split(")")[0]) // 1000
                    d["TradingDate"] = datetime.fromtimestamp(ts).strftime("%d/%m/%Y")
                for k in ("Min", "Max", "Package", "Timetype", "TradingDateStr"):
                    d.pop(k, None)

            # --- Lọc chart_data theo khoảng ngày nếu có ---
            filtered = orig_data
            if min_dt or max_dt:
                filtered = []
                for d in orig_data:
                    try:
                        dt = datetime.strptime(d["TradingDate"], "%d/%m/%Y")
                    except:
                        continue
                    if (min_dt is None or dt >= min_dt) and (max_dt is None or dt <= max_dt):
                        filtered.append(d)
                # nếu rỗng và chỉ hỏi 1 ngày duy nhất → fallback nearest
                if not filtered and min_dt and max_dt and min_dt == max_dt:
                    target = min_dt
                    closest = min(
                        orig_data,
                        key=lambda d: abs(
                            datetime.strptime(d["TradingDate"], "%d/%m/%Y") - target
                        )
                    )
                    filtered = [closest]
            response["chart_data"] = filtered
            # -----------------------------------------------------

            # 8) Lấy dữ liệu biểu đồ ngày
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

            # Format & trim chart_data_day (TradingDateStr → DD/MM/YYYY HH:MM:SS)
            for d in daily_data:
                raw = d.get("TradingDate", "")
                if raw.startswith("/Date(") and raw.endswith(")/"):
                    ms = int(raw[6:-2])
                    dt = datetime.fromtimestamp(ms / 1000)
                    d["TradingDate"] = dt.strftime("%d/%m/%Y %H:%M:%S")
                else:
                    d["TradingDate"] = None
                if "TradingDateStr" in d:
                    d.pop("TradingDateStr")
                for k in (
                    "isBuy", "IsBuy", "stockcode", "StockCode",
                    "Stockcode", "Package",
                    "TotalVal", "TotalVol"
                ):
                    d.pop(k, None)
            response["chart_data_day"] = daily_data

            # 9) Tạo formated_context (không bao gồm chart_data_day)
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
            for _, d in sorted_chart:
                parts.append(f"{d['TradingDate']}: Price {d.get('Price')} - Vol {d.get('Vol')}")

            response["formated_context"] = "; ".join(parts)
            response["message"] = "Success!"
        except Exception as e:
            log.error(traceback.format_exc())
            response.update({"message": str(e), "status": 500})

        return response
