import traceback
import requests
from bs4 import BeautifulSoup
from common_service import CommonService

class CalendarService(CommonService):
    service_name = "calendar_service"

    def process(self, json_data, log):
        """
        json_data: {
            "type": "duong_sang_am" hoặc "am_sang_duong" (default: duong_sang_am),
            "day": int,
            "month": int,
            "year": int
        }
        """
        response = {"status": 200, "message": "Success"}
        try:
            # Lấy params
            convert_type = json_data.get("type", "duong_sang_am")
            day = int(json_data.get("day", 1))
            month = int(json_data.get("month", 1))
            year = int(json_data.get("year", 2025))
            type_num = 1 if convert_type == "am_sang_duong" else 0

            url = "https://lichngaytot.com/Ajax/DoiNgayAmDuongAjax"
            params = {
                "Date": day,
                "Month": month,
                "Year": year,
                "Type": type_num
            }
            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            result = {}
            # Parse bảng chính (dương lịch, âm lịch, can chi, ngũ hành, ngày, tiết khí)
            table = soup.select_one("table.table1")
            if table:
                for row in table.select("tr"):
                    tds = row.find_all("td")
                    if len(tds) == 2:
                        key = tds[0].get_text(strip=True)
                        val = tds[1].get_text(strip=True)
                        result[key] = val
            # Tách Can chi thành 3 trường nếu có
            can_chi = result.get("Can chi")
            if can_chi:
                parts = [p.strip() for p in can_chi.split(",") if p.strip()]
                if len(parts) == 3:
                    result["day_lunar"] = parts[0].replace("Ngày ", "")
                    result["month_lunar"] = parts[1].replace("Tháng ", "")
                    result["year_lunar"] = parts[2].replace("năm ", "")

            # Parse giờ hoàng đạo/hắc đạo
            good_hours, bad_hours = [], []
            for table_hd in soup.select("table.table1"):
                th = table_hd.select_one(".th-title")
                if th and "Giờ hoàng đạo" in th.get_text():
                    rows = table_hd.select("tbody > tr")
                    mode = None
                    for row in rows:
                        h3 = row.select_one("h3.td-title")
                        if h3:
                            text = h3.get_text(strip=True)
                            if "Hoàng đạo" in text:
                                mode = "good"
                            elif "Hắc đạo" in text:
                                mode = "bad"
                            continue
                        tds = row.find_all("td")
                        if len(tds) == 3:
                            item = {
                                "time": tds[0].get_text(strip=True),
                                "chi": tds[1].get_text(strip=True),
                                "sao": tds[2].get_text(strip=True)
                            }
                            if mode == "good":
                                good_hours.append(item)
                            elif mode == "bad":
                                bad_hours.append(item)
            # Nếu chưa có bad_hours, thử tìm bảng riêng cho giờ hắc đạo
            if not bad_hours:
                for table_hd in soup.select("table.table1"):
                    rows = table_hd.select("tbody > tr")
                    if not rows:
                        continue
                    h3 = rows[0].select_one("h3.td-title")
                    if h3 and "Hắc đạo" in h3.get_text():
                        for row in rows[1:]:
                            tds = row.find_all("td")
                            if len(tds) == 3:
                                item = {
                                    "time": tds[0].get_text(strip=True),
                                    "chi": tds[1].get_text(strip=True),
                                    "sao": tds[2].get_text(strip=True)
                                }
                                bad_hours.append(item)
                        break
            result["good_hours"] = good_hours
            result["bad_hours"] = bad_hours

            # Lấy trực ngày
            truc_ngay = None
            for table in soup.select("table.table1"):
                h3 = table.select_one("h3.td-title")
                if h3 and "trực" in h3.get_text(strip=True).lower():
                    trs = table.select("tbody > tr")
                    if len(trs) > 1:
                        truc_ngay = trs[1].get_text(strip=True)
                    break
            result["truc_ngay"] = truc_ngay

            # Lấy sao tốt/xấu và việc nên làm/kỵ
            good_stars, bad_stars = [], []
            for table in soup.select("table.table1"):
                th = table.select_one(".th-title")
                if th and "ngọc hạp thông thư" in th.get_text(strip=True).lower():
                    trs = table.select("tbody > tr")
                    mode = None
                    for row in trs:
                        h3s = row.select("h3.td-title")
                        if h3s:
                            text = h3s[0].get_text(strip=True)
                            if "Sao tốt" in text:
                                mode = "good"
                            elif "Sao xấu" in text:
                                mode = "bad"
                            continue
                        tds = row.find_all("td")
                        if len(tds) == 2:
                            star = tds[0].get_text(strip=True)
                            desc = tds[1].get_text(strip=True)
                            if mode == "good":
                                good_stars.append({"star": star, "desc": desc})
                            elif mode == "bad":
                                bad_stars.append({"star": star, "desc": desc})
            # Lấy thêm các sao xấu/việc nên kỵ từ các bảng có h3.td-title là "Sao xấu"
            for table in soup.select("table.table1"):
                trs = table.select("tbody > tr")
                if trs and trs[0].select_one("h3.td-title") and "Sao xấu" in trs[0].select_one("h3.td-title").get_text(strip=True):
                    for row in trs[1:]:
                        tds = row.find_all("td")
                        if len(tds) == 2:
                            star = tds[0].get_text(strip=True)
                            desc = tds[1].get_text(strip=True)
                            bad_stars.append({"star": star, "desc": desc})
            result["good_stars"] = good_stars
            result["bad_stars"] = bad_stars

            # Lấy hướng xuất hành (ưu tiên bảng có th-title chứa 'hướng xuất hành')
            huong_xuat_hanh = None
            for table in soup.select("table.table1"):
                th = table.select_one(".th-title")
                if th and "hướng xuất hành" in th.get_text(strip=True).lower():
                    td = table.select_one("tbody > tr:not(.bg-td) > td")
                    if td:
                        huong_xuat_hanh = td.decode_contents().replace('<br>', '\n')
                        huong_xuat_hanh = BeautifulSoup(huong_xuat_hanh, "html.parser").get_text("\n", strip=True)
                    break
            result["huong_xuat_hanh"] = huong_xuat_hanh

            # Lấy ngày xuất hành theo Khổng Minh
            xuat_hanh_khong_minh = None
            for table in soup.select("table.table1"):
                h3 = table.select_one("h3.td-title")
                if h3 and "khổng minh" in h3.get_text(strip=True).lower():
                    td = table.select_one("tbody > tr:not(.bg-td) > td")
                    if td:
                        html = td.decode_contents().replace('<br>', '\n')
                        html = html.replace('<i>', '*').replace('</i>', '*')
                        xuat_hanh_khong_minh = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
                    break
            result["xuat_hanh_khong_minh"] = xuat_hanh_khong_minh

            # formatted_context (bổ sung ngày xuất hành theo Khổng Minh)
            def join_stars(stars):
                return "; ".join(f"{s['star']}: {s['desc']}" for s in stars)
            def join_hours(hours):
                return ", ".join(f"{h['time']} ({h['chi']} - {h['sao']})" for h in hours)
            context_lines = []
            if "Dương lịch" in result:
                context_lines.append(f"Dương lịch: {result['Dương lịch']}")
            if "Âm lịch" in result:
                context_lines.append(f"Âm lịch: {result['Âm lịch']}")
            if "Can chi" in result:
                context_lines.append(f"Can chi: {result['Can chi']}")
            if result.get("truc_ngay"):
                context_lines.append(f"Trực ngày: {result['truc_ngay']}")
            if result.get("good_hours"):
                context_lines.append(f"Giờ hoàng đạo: {join_hours(result['good_hours'])}")
            if result.get("bad_hours"):
                context_lines.append(f"Giờ hắc đạo: {join_hours(result['bad_hours'])}")
            if result.get("good_stars"):
                context_lines.append(f"Sao tốt: {join_stars(result['good_stars'])}")
            if result.get("bad_stars"):
                context_lines.append(f"Sao xấu: {join_stars(result['bad_stars'])}")
            if huong_xuat_hanh:
                context_lines.append(f"Hướng xuất hành: {huong_xuat_hanh}")
            if xuat_hanh_khong_minh:
                context_lines.append(f"Ngày xuất hành theo Khổng Minh: {xuat_hanh_khong_minh}")
            result["formatted_context"] = "\n".join(context_lines)

            response["result"] = result
        except Exception as e:
            log.error(traceback.format_exc())
            response["status"] = 500
            response["message"] = str(e)
        return response
