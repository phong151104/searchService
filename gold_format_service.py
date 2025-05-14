import traceback
import requests
from datetime import datetime
from bs4 import BeautifulSoup

from common_service import CommonService

class GoldFormatService(CommonService):
    service_name = "gold_format_service"

    def __init__(self):
        super(GoldFormatService, self).__init__()

    def process(self, json_data, log):
        response = {
            "message": "Success",
            "status": 200
        }

        try:
            # 1. Lấy giá trị "date" từ payload, có thể None hoặc chuỗi
            raw_date = json_data.get("date")
            # Nếu raw_date là None hoặc chỉ khoảng trắng thì coi như không có ngày
            date = raw_date.strip() if isinstance(raw_date, str) and raw_date.strip() else None
            log.debug(f"Payload raw_date: {raw_date!r}, dùng date: {date!r}")

            # 2. Xác định URL
            base_url = "https://www.24h.com.vn/gia-vang-hom-nay-c425.html"
            if date:
                url = f"{base_url}?ngaythang={date}"
            else:
                url = base_url
            log.debug(f"Sử dụng URL: {url}")

            # 3. Request và parse bảng giá
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers)
            if res.status_code != 200:
                response.update({
                    "message": f"Không tải được trang giá vàng, status_code: {res.status_code}",
                    "status": 500,
                    "source": url
                })
                return response

            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.select("table.gia-vang-search-data-table tbody tr")

            prices = []
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 5:
                    prices.append({
                        "name":           cols[0].get_text(strip=True),
                        "today_buy":      cols[1].get_text(strip=True),
                        "today_sell":     cols[2].get_text(strip=True),
                        "yesterday_buy":  cols[3].get_text(strip=True),
                        "yesterday_sell": cols[4].get_text(strip=True),
                    })

            # 4. Sinh context_formated
            #    Nếu không có date thì dùng ngày hôm nay
            ref_date = date or datetime.today().strftime("%Y-%m-%d")
            parts = [f"Giá vàng ngày {ref_date} theo nguồn 24h.com.vn như sau:"]
            for p in prices:
                parts.append(
                    f"{p['name']} mua vào {p['today_buy']}, bán ra {p['today_sell']}; "
                    f"ngày hôm trước mua vào {p['yesterday_buy']}, bán ra {p['yesterday_sell']}."
                )
            context_formated = " ".join(parts)

            # 5. Trả về kết quả
            response.update({
                "date":             ref_date,
                "prices":           prices,
                "context_formated": context_formated,
                "source":           url
            })

        except Exception as e:
            traceback.print_exc()
            response["message"] = str(e)
            response["status"]  = 500

        return response
