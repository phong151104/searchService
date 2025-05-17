import json
import traceback
import datetime
import requests
from bs4 import BeautifulSoup
import re

from common_service import CommonService


class LotteryService(CommonService):
    service_name = 'lottery_service'
    
    def __init__(self):
        super(LotteryService, self).__init__()
        self.lottery_url = 'https://kqxs.vn'
        self.lottery_types = {
            "Miền Bắc": "/mien-bac",
            "Miền Trung": "/mien-trung",
            "Miền Nam": "/mien-nam",
            "Hồ Chí Minh": "/mien-nam/xo-so-ho-chi-minh",
            "Đồng Tháp": "/mien-nam/xo-so-dong-thap",
            "Cà Mau": "/mien-nam/xo-so-ca-mau",
            "Bến Tre": "/mien-nam/xo-so-ben-tre",
            "Vũng Tàu": "/mien-nam/xo-so-vung-tau",
            "Bạc Liêu": "/mien-nam/xo-so-bac-lieu",
            "Đồng Nai": "/mien-nam/xo-so-dong-nai",
            "Cần Thơ": "/mien-nam/xo-so-can-tho",
            "Sóc Trăng": "/mien-nam/xo-so-soc-trang",
            "Tây Ninh": "/mien-nam/xo-so-tay-ninh",
            "An Giang": "/mien-nam/xo-so-an-giang",
            "Bình Thuận": "/mien-nam/xo-so-binh-thuan",
            "Vĩnh Long": "/mien-nam/xo-so-vinh-long",
            "Bình Dương": "/mien-nam/xo-so-binh-duong",
            "Trà Vinh": "/mien-nam/xo-so-tra-vinh",
            "Long An": "/mien-nam/xo-so-long-an",
            "Bình Phước": "/mien-nam/xo-so-binh-phuoc",
            "Hậu Giang": "/mien-nam/xo-so-hau-giang",
            "Tiền Giang": "/mien-nam/xo-so-tien-giang",
            "Kiên Giang": "/mien-nam/xo-so-kien-giang",
            "Đà Lạt": "/mien-nam/xo-so-da-lat",
            "Phú Yên": "/mien-trung/xo-so-phu-yen",
            "Thừa Thiên Huế": "/mien-trung/xo-so-thua-thien-hue",
            "Đắk Lắk": "/mien-trung/xo-so-dac-lac",
            "Quảng Nam": "/mien-trung/xo-so-quang-nam",
            "Đà Nẵng": "/mien-trung/xo-so-da-nang",
            "Khánh Hòa": "/mien-trung/xo-so-khanh-hoa",
            "Quảng Bình": "/mien-trung/xo-so-quang-binh",
            "Bình Định": "/mien-trung/xo-so-binh-dinh",
            "Quảng Trị": "/mien-trung/xo-so-quang-tri",
            "Gia Lai": "/mien-trung/xo-so-gia-lai",
            "Ninh Thuận": "/mien-trung/xo-so-ninh-thuan",
            "Quảng Ngãi": "/mien-trung/xo-so-quang-ngai",
            "Đắk Nông": "/mien-trung/xo-so-dac-nong",
            "Kon Tum": "/mien-trung/xo-so-kon-tum",
            "Mega 6/45": "/xo-so-mega645",
            "Power 6/55": "/xo-so-power655",
        }
    
    def process(self, json_data, log):
        response = {
            "message": "Success",
            "status": 200
        }
        
        try:
            duration = json_data.get("duration.startDate", "")
            lottery_type = json_data.get("lottery_type", "")
            
            # Nếu ko có loại giải, mặc định để miền bắc
            if lottery_type == "":
                lottery_type = "Miền Bắc"
            
            log.debug("Get lottery lottery_type=[{}] duration=[{}]".format(lottery_type, duration))
            
            chosen_lottery = self.lottery_types.get(lottery_type)
            search_url = self.lottery_url + chosen_lottery
            
            if duration:
                search_date = datetime.datetime.strptime(duration, "%d/%m/%Y").strftime("%d-%m-%Y")
                search_url = search_url + "?date={}".format(search_date)
            
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(search_url, headers=headers, verify=False)
            soup = BeautifulSoup(res.text, "html.parser")
            table = soup.find("table", class_="table-fixed tbldata table-result-lottery")
            
            if table is not None:
                if lottery_type == "Miền Bắc":
                    result = self.parse_lottery_table(table)
                    if result:
                        response["result"] = result
                        response["table_result"] = str(table)
                    else:
                        response["message"] = "Không tìm thấy kết quả"
                        response["status"] = 404
                elif lottery_type == "Miền Nam":
                    result = self.parse_lottery_table_mien_nam(table)
                    if result:
                        response["result"] = result
                        response["table_result"] = str(table)
                    else:
                        response["message"] = "Không tìm thấy kết quả"
                        response["status"] = 404
                elif lottery_type == "Miền Trung":
                    result = self.parse_lottery_table_mien_trung(table)
                    if result:
                        response["result"] = result
                        response["table_result"] = str(table)
                    else:
                        response["message"] = "Không tìm thấy kết quả"
                        response["status"] = 404
                elif lottery_type in ["Mega 6/45", "Power 6/55"]:
                    result = self.parse_lottery_table_mega_power(table)
                    if result:
                        response["result"] = result
                        response["table_result"] = str(table)
                    else:
                        response["message"] = "Không tìm thấy kết quả"
                        response["status"] = 404
                else:
                    # Tất cả các tỉnh đều xử lý như miền Bắc
                    result = self.parse_lottery_table(table)
                    if result:
                        response["result"] = result
                        response["table_result"] = str(table)
                    else:
                        response["message"] = "Không tìm thấy kết quả"
                        response["status"] = 404
            else:
                response["message"] = "Không tìm thấy kết quả"
                response["status"] = 404
            
            # Lấy title và ngày từ table/caption
            title = None
            date_value = None
            if not duration:
                title, date_value = self.extract_title_and_date_from_table(table)
            else:
                # Nếu có duration thì lấy ngày từ duration, còn title thì để None
                try:
                    date_value = datetime.datetime.strptime(duration, "%d/%m/%Y").strftime("%d-%m-%Y")
                except:
                    date_value = duration
            response["date"] = date_value if date_value else ""
            if title:
                response["title"] = title
            response["loai_xo_so"] = lottery_type
            response["source"] = search_url
            response["display_type"] = self.get_display_type(chosen_lottery)
            response["formatted_context"] = self.format_result_context(response.get("result"), lottery_type, title)
        
        except Exception as e:
            response["message"] = str(e)
            response["status"] = 500
            
            traceback.print_exc()
        
        return response
    
    @staticmethod
    def parse_lottery_table(table):
        prize_map = {
            "Đặc biệt": "giai_dac_biet",
            "Giải nhất": "giai_nhat",
            "Giải nhì": "giai_nhi",
            "Giải ba": "giai_ba",
            "Giải tư": "giai_tu",
            "Giải năm": "giai_nam",
            "Giải sáu": "giai_sau",
            "Giải bảy": "giai_bay",
            "Giải tám": "giai_tam"
        }
        result = {}
        for row in table.find_all("tr"):
            prize_td = row.find("td", class_="prize")
            results_td = row.find("td", class_="results")
            if prize_td and results_td:
                prize_name = prize_td.get_text(strip=True)
                key = prize_map.get(prize_name)
                if key:
                    numbers = [span.get_text(strip=True) for span in results_td.find_all("span", class_="number")]
                    if key in result:
                        # Nếu đã có, nối thêm vào mảng
                        if isinstance(result[key], list):
                            result[key].extend(numbers)
                        else:
                            result[key] = [result[key]] + numbers
                    else:
                        result[key] = numbers if len(numbers) > 1 else (numbers[0] if numbers else "")
        return result
    
    @staticmethod
    def parse_lottery_table_mien_nam(table):
        # Lấy tên các tỉnh ở dòng đầu tiên
        rows = table.find_all("tr")
        if not rows or len(rows) < 2:
            return None
        header_cells = rows[0].find_all("span", class_="wrap-text")
        provinces = [cell.get_text(strip=True) for cell in header_cells]
        # Map các giải
        prize_map = {
            "Đặc biệt": "dac_biet",
            "Giải nhất": "nhat",
            "Giải nhì": "nhi",
            "Giải ba": "ba",
            "Giải tư": "tu",
            "Giải năm": "nam",
            "Giải sáu": "sau",
            "Giải bảy": "bay",
            "Giải tám": "tam"
        }
        result = {province: {} for province in provinces}
        for row in rows[1:]:
            prize_td = row.find("td", class_="prize")
            results_td = row.find("td", class_="results")
            if prize_td and results_td:
                prize_name = prize_td.get_text(strip=True)
                key = prize_map.get(prize_name)
                if key:
                    numbers = [span.get_text(strip=True) for span in results_td.find_all("span", class_="number")]
                    # Phân bổ số cho từng tỉnh theo thứ tự, lặp lại nếu cần
                    for idx, num in enumerate(numbers):
                        province = provinces[idx % len(provinces)]
                        if key not in result[province]:
                            result[province][key] = []
                        result[province][key].append(num)
        return result
    
    @staticmethod
    def parse_lottery_table_mien_trung(table):
        # Lấy tên các tỉnh ở dòng đầu tiên
        rows = table.find_all("tr")
        if not rows or len(rows) < 2:
            return None
        header_cells = rows[0].find_all("span", class_="wrap-text")
        provinces = [cell.get_text(strip=True) for cell in header_cells]
        # Map các giải
        prize_map = {
            "Đặc biệt": "dac_biet",
            "Giải nhất": "nhat",
            "Giải nhì": "nhi",
            "Giải ba": "ba",
            "Giải tư": "tu",
            "Giải năm": "nam",
            "Giải sáu": "sau",
            "Giải bảy": "bay",
            "Giải tám": "tam"
        }
        result = {province: {} for province in provinces}
        for row in rows[1:]:
            prize_td = row.find("td", class_="prize")
            results_td = row.find("td", class_="results")
            if prize_td and results_td:
                prize_name = prize_td.get_text(strip=True)
                key = prize_map.get(prize_name)
                if key:
                    numbers = [span.get_text(strip=True) for span in results_td.find_all("span", class_="number")]
                    # Phân bổ số cho từng tỉnh theo thứ tự, lặp lại nếu cần
                    for idx, num in enumerate(numbers):
                        province = provinces[idx % len(provinces)]
                        if key not in result[province]:
                            result[province][key] = []
                        result[province][key].append(num)
        return result
    
    @staticmethod
    def parse_lottery_table_mega_power(table):
        # Lấy dãy số trúng
        numbers = []
        vietlott_div = table.find("div", class_="vietlott")
        if vietlott_div:
            ul = vietlott_div.find("ul")
            if ul:
                for li in ul.find_all("li", class_="number"):
                    val = li.get_text(strip=True)
                    if val:
                        numbers.append(val)
        # Lấy danh sách giải thưởng
        prizes = []
        for tr in table.find_all("tr", class_="prize-pool"):
            tds = tr.find_all("td")
            if len(tds) >= 4:
                name = tds[0].get_text(strip=True)
                quantity = tds[2].get_text(strip=True)
                value = tds[3].get_text(strip=True)
                # Bỏ dòng tiêu đề
                if name == "Giải thưởng" and quantity == "Số lượng" and value == "Giá trị giải":
                    continue
                prizes.append({"name": name, "quantity": quantity, "value": value})
        if numbers or prizes:
            return {"numbers": numbers, "prizes": prizes}
        return None
    
    @staticmethod
    def remove_name_kqxs(table_element: str, lottery_type: str):
        
        table_element = table_element.replace('<span class="hidden-sm hidden-xs">Kết quả</span> Xổ số ' + lottery_type + ' ', '')\
                    .replace('<span class="hidden-xs hidden-sm">Kết quả</span> Xổ số ' + lottery_type + ' ', '')\
                    .replace('<span class="hidden-sm hidden-xs">Kết quả </span>Xổ số ' + lottery_type + ' ', '')
        return table_element
    
    @staticmethod
    def get_display_type(chosen_lottery: str):
        if chosen_lottery == "/mien-bac":
            return "mien_bac"
        if chosen_lottery == "/mien-trung":
            return "mien_trung"
        if chosen_lottery == "/mien-nam":
            return "mien_nam"
        if chosen_lottery.startswith("/mien-trung"):
            return "mien_trung_tinh_le"
        if chosen_lottery.startswith("/mien-nam"):
            # Lấy tên tỉnh từ url, ví dụ: /mien-nam/xo-so-kien-giang -> mien_nam_kien_giang
            parts = chosen_lottery.split("/")
            if len(parts) >= 4:
                return f"mien_nam_{parts[-1].replace('xo-so-', '')}"
            return "mien_nam_tinh_le"
        if chosen_lottery == "/xo-so-mega645":
            return "vietlott_mega645"
        if chosen_lottery == "/xo-so-power655":
            return "vietlott_power655"
    
    @staticmethod
    def format_result_context(result, lottery_type, title=None):
        if not result:
            return "Không có kết quả."
        lines = []
        if title:
            lines.append(title)
        # Nếu là Mega/Power
        if lottery_type in ["Mega 6/45", "Power 6/55"]:
            if isinstance(result, dict):
                if result.get("numbers"):
                    lines.append("Số trúng thưởng: " + ", ".join(result["numbers"]))
                if result.get("prizes"):
                    lines.append("Các giải thưởng:")
                    for prize in result["prizes"]:
                        lines.append(f"  {prize['name']}: {prize['quantity']} giải, mỗi giải {prize['value']}")
            else:
                lines.append(str(result))
        # Nếu là dict các tỉnh (miền Nam/Nam Trung)
        elif isinstance(result, dict) and any(isinstance(v, dict) for v in result.values()):
            for province, prizes in result.items():
                lines.append(f"{province}:")
                for giai, vals in prizes.items():
                    label = giai.replace('_', ' ').capitalize()
                    if isinstance(vals, list):
                        vals = ", ".join(vals)
                    lines.append(f"  {label}: {vals}")
        # Nếu là dict các giải (miền Bắc hoặc tỉnh lẻ)
        else:
            prize_map = {
                "giai_dac_biet": "Giải đặc biệt",
                "giai_nhat": "Giải nhất",
                "giai_nhi": "Giải nhì",
                "giai_ba": "Giải ba",
                "giai_tu": "Giải tư",
                "giai_nam": "Giải năm",
                "giai_sau": "Giải sáu",
                "giai_bay": "Giải bảy",
                "giai_tam": "Giải tám"
            }
            for key, label in prize_map.items():
                if key in result:
                    val = result[key]
                    if isinstance(val, list):
                        val = ", ".join(val)
                    lines.append(f"{label}: {val}")
        return "\n".join(lines)

    def extract_title_and_date_from_table(self, table):
        # Lấy tiêu đề đầy đủ và ngày từ caption hoặc thead
        title = None
        date_str = None
        if table is not None:
            caption = table.find("caption")
            if caption:
                text = caption.get_text(strip=True)
                # Loại bỏ <span class="hidden-sm hidden-xs">Kết quả</span> nếu có
                text = re.sub(r"^Kết quả\s*", "", text)
                title = text
                m = re.search(r"(\d{2}-\d{2}-\d{4})", text)
                if m:
                    date_str = m.group(1)
            if not title or not date_str:
                thead = table.find("thead")
                if thead:
                    text = thead.get_text(strip=True)
                    text = re.sub(r"^Kết quả\s*", "", text)
                    if not title:
                        title = text
                    if not date_str:
                        m = re.search(r"(\d{2}-\d{2}-\d{4})", text)
                        if m:
                            date_str = m.group(1)
        return title, date_str