import traceback
import requests
from datetime import datetime
from bs4 import BeautifulSoup

from common_service import CommonService

class GoldPriceService(CommonService):
    service_name = "gold_price_service"

    def __init__(self):
        super(GoldPriceService, self).__init__()

    def process(self, json_data, log):
        response = {"message": "Success", "status": 200}

        try:
            # 1. Lấy date từ payload
            raw_date = json_data.get("date")
            date = raw_date.strip() if isinstance(raw_date, str) and raw_date.strip() else None
            log.debug(f"Payload raw_date: {raw_date!r}, dùng date: {date!r}")

            # 2. Xác định URL
            base_url = "https://www.24h.com.vn/gia-vang-hom-nay-c425.html"
            url = f"{base_url}?ngaythang={date}" if date else base_url
            log.debug(f"Sử dụng URL: {url}")

            # 3. Fetch và parse bảng
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.select("table.gia-vang-search-data-table tbody tr")

            prices = []
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                name = cols[0].get_text(strip=True)

                # Giá mua hôm nay & change_buy
                buy_cell = cols[1]
                tbuy_el = buy_cell.select_one("span.fixW")
                tbuy_str = tbuy_el.text.strip() if tbuy_el else ""
                change_el = buy_cell.select_one("span.colorRed, span.colorGreen")
                if change_el:
                    change_buy = int(change_el.text.strip().replace(",", ""))
                    if "colorRed" in change_el["class"]:
                        change_buy = -abs(change_buy)
                else:
                    change_buy = 0

                # Giá bán hôm nay & change_sell
                sell_cell = cols[2]
                tsell_el = sell_cell.select_one("span.fixW")
                tsell_str = tsell_el.text.strip() if tsell_el else cols[2].get_text(strip=True)
                change_sell_el = sell_cell.select_one("span.colorRed, span.colorGreen")
                if change_sell_el:
                    change_sell = int(change_sell_el.text.strip().replace(",", ""))
                    if "colorRed" in change_sell_el["class"]:
                        change_sell = -abs(change_sell)
                else:
                    change_sell = 0

                # Giá mua ngày trước & giá bán ngày trước
                ybuy_str  = cols[3].get_text(strip=True)
                ysell_str = cols[4].get_text(strip=True)

                prices.append({
                    "name":            name,
                    "today_buy":       tbuy_str,
                    "change_buy":      change_buy,
                    "today_sell":      tsell_str,
                    "change_sell":     change_sell,
                    "yesterday_buy":   ybuy_str,
                    "yesterday_sell":  ysell_str,
                })

            # 4. Tạo formated_context với 000 cho các số
            ref_date = date or datetime.today().strftime("%Y-%m-%d")
            def add_zeros(val):
                return val.replace(",", "") + "000" if val else ""

            def add_comma_and_zeros(val):
                if not val: return ""
                s = val.replace(",", "")
                try:
                    n = int(s)
                    return f"{n:,}000".replace(",", ",")
                except:
                    return val + "000"

            parts = [f"Giá vàng ngày {ref_date} theo nguồn 24h.com.vn như sau:"]
            for p in prices:
                today_buy_full       = f"{p['today_buy']}000 Việt Nam đồng trên 1 lượng"
                today_sell_full      = f"{p['today_sell']}000 Việt Nam đồng trên 1 lượng"
                yesterday_buy_full   = f"{p['yesterday_buy']}000 Việt Nam đồng trên 1 lượng"
                yesterday_sell_full  = f"{p['yesterday_sell']}000 Việt Nam đồng trên 1 lượng"
                change_buy_full      = f"{p['change_buy']}000 Việt Nam đồng" if p['change_buy'] != 0 else "0 Việt Nam đồng"
                change_sell_full     = f"{p['change_sell']}000 Việt Nam đồng" if p['change_sell'] != 0 else "0 Việt Nam đồng"
                parts.append(
                    f"{p['name']} mua vào {today_buy_full} (thay đổi: {change_buy_full}), "
                    f"bán ra {today_sell_full} (thay đổi: {change_sell_full}); "
                    f"ngày hôm trước mua vào {yesterday_buy_full}, bán ra {yesterday_sell_full}."
                )
            context_formated = " ".join(parts)

            # 5. Trả về
            response.update({
                "date":             ref_date,
                "prices":           prices,
                "context_formated": context_formated,
                "source":           url
            })

        except Exception as e:
            log.error(traceback.format_exc())
            response.update({"message": str(e), "status": 500})

        return response