import traceback
import requests
from bs4 import BeautifulSoup
from common_service import CommonService

class TuViService(CommonService):
    service_name = "tuvi_service"

    def process(self, json_data, log):
        response = {"status": 200, "message": "Success", "data": []}
        try:
            month = int(json_data.get("month", 5))
            year = int(json_data.get("year", 2025))
            url = f"http://xemtuong.net/xem_ngay/tot_trong_thang/index.php?month={month:02d}&year={year}&submit=Xem"
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            r.raise_for_status()
            with open("debug_xemtuong.html", "w", encoding="utf-8") as f:
                f.write(r.text)
            soup = BeautifulSoup(r.text, "html.parser")

            for tr in soup.select('div.bs-example table.table.table-bordered > tbody > tr'):
                tds = tr.find_all('td')
                if len(tds) != 2:
                    continue
                div = tds[1].find('div', align='left')
                if not div:
                    continue
                html = str(div)
                # 1. date_info
                date_info = ""
                b_tags = div.find_all('b')
                if b_tags and len(b_tags) >= 2:
                    date_info = b_tags[0].get_text(strip=True) + " - " + b_tags[1].get_text(strip=True)
                # 2. good_hours
                good_hours = ""
                for line in div.stripped_strings:
                    if "Giờ tốt trong ngày:" in line:
                        good_hours = line.replace("Giờ tốt trong ngày:", "").strip()
                        break
                # 3. should_do (nội dung sau các span đánh giá)
                should_do = ""
                for span in div.find_all('span'):
                    if span.get('class') and ('tot' in span.get('class') or 'trung' in span.get('class') or 'xau' in span.get('class')):
                        # Lấy text phía sau span
                        next_text = span.next_sibling
                        if next_text:
                            should_do = str(next_text).strip()
                        break
                # 4. note (Rất Tốt, Trung Bình, ...)
                note = ""
                for span in div.find_all('span'):
                    if span.get('class') and ('tot' in span.get('class') or 'trung' in span.get('class') or 'xau' in span.get('class')):
                        note = span.get_text(strip=True)
                        break

                if date_info:
                    response["data"].append({
                        "date_info": date_info,
                        "good_hours": good_hours,
                        "should_do": should_do,
                        "note": note
                    })
        except Exception as e:
            log.error(traceback.format_exc())
            response["status"] = 500
            response["message"] = str(e)
        return response 