import traceback
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup

from common_service import CommonService

class CalendarService(CommonService):
    service_name = "calendar_service"

    def process(self, json_data, log):
        response = {"status": 200, "message": "Success"}
        try:
            # 1) Đọc params
            convert_type = json_data.get("type", "duong_sang_am")
            day   = int(json_data.get("day",   1))
            month = int(json_data.get("month", 1))
            year  = int(json_data.get("year",  2025))
            type_num = 1 if convert_type == "am_sang_duong" else 0

            # 2) Gọi API chuyển lịch
            url = "https://lichngaytot.com/Ajax/DoiNgayAmDuongAjax"
            params = {"Date": day, "Month": month, "Year": year, "Type": type_num}
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            # 3) Đọc toàn bộ kết quả thô vào dict 'raw'
            raw = {}
            main_table = soup.select_one("table.table1")
            if main_table:
                for tr in main_table.select("tr"):
                    tds = tr.find_all("td")
                    if len(tds) == 2:
                        k = tds[0].get_text(strip=True)
                        v = tds[1].get_text(strip=True)
                        raw[k] = v

            # 4) Tách Can chi thành lunarDay, lunarMonth, lunarYear
            cc = raw.get("Can chi", "")
            lunar_day = lunar_month = lunar_year = None
            m = re.search(r"Ngày\s*([^,]+)", cc)
            if m: lunar_day = m.group(1).strip()
            m = re.search(r"Tháng\s*([^,]+)", cc)
            if m: lunar_month = m.group(1).strip()
            m = re.search(r"năm\s*([^,]+)", cc, re.IGNORECASE)
            if m: lunar_year = m.group(1).strip()

            # 5) Parse giờ hoàng đạo/hắc đạo
            good_hours, bad_hours = [], []
            for tbl in soup.select("table.table1"):
                title = tbl.select_one(".th-title")
                if title and "Giờ hoàng đạo" in title.get_text():
                    mode = None
                    for row in tbl.select("tbody > tr"):
                        h3 = row.select_one("h3.td-title")
                        if h3:
                            txt = h3.get_text(strip=True)
                            mode = "good" if "Hoàng đạo" in txt else "bad"
                            continue
                        cols = row.find_all("td")
                        if len(cols)==3:
                            item = {
                                "time": cols[0].get_text(strip=True),
                                "chi":  cols[1].get_text(strip=True),
                                "star": cols[2].get_text(strip=True)
                            }
                            (good_hours if mode=="good" else bad_hours).append(item)
            if not bad_hours:
                for tbl in soup.select("table.table1"):
                    rows = tbl.select("tbody > tr")
                    if not rows: continue
                    if rows[0].select_one("h3.td-title") and "Hắc đạo" in rows[0].get_text():
                        for row in rows[1:]:
                            cols = row.find_all("td")
                            if len(cols)==3:
                                bad_hours.append({
                                    "time": cols[0].get_text(strip=True),
                                    "chi":  cols[1].get_text(strip=True),
                                    "star": cols[2].get_text(strip=True)
                                })
                        break

            # 6) Lấy trực ngày
            daily_duty = None
            for tbl in soup.select("table.table1"):
                h3 = tbl.select_one("h3.td-title")
                if h3 and "trực" in h3.get_text(strip=True).lower():
                    trs = tbl.select("tbody > tr")
                    if len(trs)>1:
                        daily_duty = trs[1].get_text(strip=True)
                    break

            # 7) Parse sao tốt/xấu
            good_stars, bad_stars = [], []
            for tbl in soup.select("table.table1"):
                th = tbl.select_one(".th-title")
                if th and "ngọc hạp thông thư" in th.get_text(strip=True).lower():
                    mode = None
                    for row in tbl.select("tbody > tr"):
                        h3s = row.select("h3.td-title")
                        if h3s:
                            txt = h3s[0].get_text(strip=True)
                            mode = "good" if "Sao tốt" in txt else "bad"
                            continue
                        cols = row.find_all("td")
                        if len(cols)==2:
                            item = {"star": cols[0].get_text(strip=True),
                                    "desc": cols[1].get_text(strip=True)}
                            (good_stars if mode=="good" else bad_stars).append(item)
            for tbl in soup.select("table.table1"):
                rows = tbl.select("tbody > tr")
                if rows and rows[0].select_one("h3.td-title") and "Sao xấu" in rows[0].get_text():
                    for row in rows[1:]:
                        cols = row.find_all("td")
                        if len(cols)==2:
                            bad_stars.append({
                                "star": cols[0].get_text(strip=True),
                                "desc": cols[1].get_text(strip=True)
                            })
                    break

            # 8) Hướng xuất hành
            auspicious_dirs = None
            for tbl in soup.select("table.table1"):
                th = tbl.select_one(".th-title")
                if th and "hướng xuất hành" in th.get_text(strip=True).lower():
                    td = tbl.select_one("tbody > tr:not(.bg-td) > td")
                    if td:
                        html = td.decode_contents().replace("<br>", "\n")
                        auspicious_dirs = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
                    break

            # 9) Khổng Minh
            kong_ming = None
            for tbl in soup.select("table.table1"):
                h3 = tbl.select_one("h3.td-title")
                if h3 and "khổng minh" in h3.get_text(strip=True).lower():
                    td = tbl.select_one("tbody > tr:not(.bg-td) > td")
                    if td:
                        html = td.decode_contents().replace("<br>", "\n")
                        html = html.replace("<i>", "*").replace("</i>", "*")
                        kong_ming = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
                    break

            # 10) Trích solarDate
            solar_raw = raw.get("Dương lịch","")
            solar_date = None
            if solar_raw:
                parts = solar_raw.split("ngày")
                if len(parts)>=2:
                    solar_date = parts[1].strip()

            # 11) Kết quả tiếng Anh
            # Lấy lunarDate chỉ là số ngày
            lunar_date_num = None
            lunar_raw = raw.get("Âm lịch", "")
            m = re.search(r"Ngày\s*(\d+)", lunar_raw)
            if m:
                lunar_date_num = m.group(1)

            result_en = {
                "solarDate":         solar_date,
                "lunarDay":          lunar_day,
                "lunarMonth":        lunar_month,
                "lunarYear":         lunar_year,
                "lunarDate":         lunar_date_num,
                "stemBranch":        raw.get("Can chi"),
                "element":           raw.get("Ngũ hành"),
                "solarTerm":         raw.get("Tiết Khí"),
                "auspiciousHours":   good_hours,
                "inauspiciousHours": bad_hours,
                "dailyDuty":         daily_duty,
                "goodStars":         good_stars,
                "badStars":          bad_stars,
                "auspiciousDirs":    auspicious_dirs,
                "kongMingAdvice":    kong_ming
            }
            response["result"] = result_en

            # 12) Tạo formatted_context
            def join_hours_vi(hours):
                return ", ".join(f"{h['time']} - {h['chi']} ({h['star']})" for h in hours)
            def join_stars_vi(stars):
                return "; ".join(f"{s['star']}: {s['desc']}" for s in stars)

            ctx_vi = []
            if result_en["solarDate"]:
                ctx_vi.append(f"Ngày dương: {result_en['solarDate']}")
            if lunar_date_num and lunar_month and lunar_year:
                ctx_vi.append(f"Ngày âm: {lunar_date_num} tháng {lunar_month} năm {lunar_year}")
            elif lunar_day and lunar_month and lunar_year:
                ctx_vi.append(f"Ngày âm: {lunar_day} tháng {lunar_month} năm {lunar_year}")
            if result_en["stemBranch"]:
                ctx_vi.append(f"Can chi: {result_en['stemBranch']}")
            if result_en["element"]:
                ctx_vi.append(f"Ngũ hành: {result_en['element']}")
            if result_en["solarTerm"]:
                ctx_vi.append(f"Tiết khí: {result_en['solarTerm']}")
            if good_hours:
                ctx_vi.append(f"Giờ hoàng đạo: {join_hours_vi(good_hours)}")
            if bad_hours:
                ctx_vi.append(f"Giờ hắc đạo: {join_hours_vi(bad_hours)}")
            if daily_duty:
                ctx_vi.append(f"Trực ngày: {daily_duty}")
            if good_stars:
                ctx_vi.append(f"Sao tốt: {join_stars_vi(good_stars)}")
            if bad_stars:
                ctx_vi.append(f"Sao xấu: {join_stars_vi(bad_stars)}")
            if auspicious_dirs:
                ctx_vi.append(f"Hướng xuất hành: {auspicious_dirs}")
            if kong_ming:
                ctx_vi.append(f"Khổng Minh: {kong_ming}")

            response["formatted_context"] = "\n".join(ctx_vi)

        except Exception as e:
            log.error(traceback.format_exc())
            response["status"]  = 500
            response["message"] = str(e)

        return response