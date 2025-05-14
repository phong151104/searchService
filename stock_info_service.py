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
                except Exception:
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
                dt = datetime.strptime(dt_txt, "%d/%m/%Y %H:%M")
                trading_date = dt_txt  # hoặc str(int(dt.timestamp()*1000)) nếu cần epoch
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
                # Lấy key là phần text trước <b>
                key = p.get_text("|||", strip=True).split("|||")[0].strip(": ")
                summary[key] = value
            response["summary"] = summary

            # 6) Lấy dữ liệu biểu đồ 12 tháng
            chart_url = "https://finance.vietstock.vn/data/getstockdealdetailbytime"
            stock_url = f"https://finance.vietstock.vn/{symbol}-ctcp-{symbol.lower()}.htm"
            session = requests.Session()
            get_headers = {"User-Agent": "Mozilla/5.0"}
            r = session.get(stock_url, headers=get_headers)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            token_input = soup.find("input", {"name": "__RequestVerificationToken"})
            token = token_input["value"] if token_input else session.cookies.get_dict().get("__RequestVerificationToken", "")
            cookies = session.cookies.get_dict()
            chart_payload = {
                "code": symbol,
                "seq": 0,
                "timetype": "1Y",
                "tradingDate": "",
                "__RequestVerificationToken": token
            }
            post_headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0",
                "X-Requested-With": "XMLHttpRequest",
                "Cookie": "; ".join([f"{k}={v}" for k, v in cookies.items()])
            }
            cj = session.post(chart_url, data=chart_payload, headers=post_headers)
            cj.raise_for_status()
            chart_js = cj.json()
            data = chart_js if isinstance(chart_js, list) else chart_js.get("Data", [])
            # Format lại TradingDate
            for d in data:
                if "TradingDate" in d and d["TradingDate"].startswith("/Date("):
                    try:
                        ts = int(d["TradingDate"].split("(")[1].split(")")[0]) // 1000
                        d["TradingDate"] = datetime.fromtimestamp(ts).strftime("%d/%m/%Y")
                    except:
                        pass
            response["chart_data"] = data

            # 6.5) Tạo formated_context tổng hợp (trừ chart_data)
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
            response["formated_context"] = "; ".join(parts)

            # 7) Đổ message
            response["message"] = "Success!"

        except Exception as e:
            log.error(traceback.format_exc())
            response.update({"message": str(e), "status": 500})

        return response