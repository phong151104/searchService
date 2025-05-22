import traceback
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from common_service import CommonService

class GoldPriceService(CommonService):
    service_name = "gold_price_service"
    
    # Cache data
    _cache = {}
    _cache_lock = threading.Lock()
    _cache_timeout = 300  # 5 minutes
    
    def __init__(self):
        super(GoldPriceService, self).__init__()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive"
        })

    def _get_cached_data(self, key):
        with self._cache_lock:
            if key in self._cache:
                data, timestamp = self._cache[key]
                if datetime.now() - timestamp < timedelta(seconds=self._cache_timeout):
                    return data
            return None

    def _set_cached_data(self, key, data):
        with self._cache_lock:
            self._cache[key] = (data, datetime.now())

    def _get_24h_data(self, date, log):
        """Lấy dữ liệu từ 24h.com.vn"""
        try:
            # Xác định URL
            base_url = "https://www.24h.com.vn/gia-vang-hom-nay-c425.html"
            url = f"{base_url}?ngaythang={date}" if date else base_url
            
            # Check cache
            cache_key = f"24h_{date}" if date else "24h_latest"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data, url

            # Fetch và parse bảng
            res = self.session.get(url, timeout=10)
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
                change_text = change_el.text.strip().replace(",", "") if change_el else ""
                if change_text:
                    change_buy = int(change_text)
                    if "colorRed" in change_el["class"]:
                        change_buy = -abs(change_buy)
                else:
                    change_buy = 0

                # Giá bán hôm nay & change_sell
                sell_cell = cols[2]
                tsell_el = sell_cell.select_one("span.fixW")
                tsell_str = tsell_el.text.strip() if tsell_el else cols[2].get_text(strip=True)
                change_sell_el = sell_cell.select_one("span.colorRed, span.colorGreen")
                change_text = change_sell_el.text.strip().replace(",", "") if change_sell_el else ""
                if change_text:
                    change_sell = int(change_text)
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
            
            self._set_cached_data(cache_key, prices)
            return prices, url
        except Exception as e:
            log.error(f"Error getting 24h data: {str(e)}")
            return None, None

    def _get_cafef_data(self, date, log):
        """Lấy dữ liệu từ cafef.vn"""
        try:
            cafef_url = "https://cafef.vn/du-lieu/gia-vang-hom-nay/trong-nuoc.chn"
            
            # Check cache
            cache_key = f"cafef_{date}" if date else "cafef_latest"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data

            # Khởi tạo Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Khởi tạo driver
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(cafef_url)
            
            # Đợi cho các element load xong
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.ID, "gia_mua_vao")))
            
            # Lấy HTML sau khi JavaScript đã chạy
            html = driver.page_source
            driver.quit()
            
            # Parse HTML
            cafef_soup = BeautifulSoup(html, "html.parser")
            
            # Lấy tab vàng miếng SJC và nhẫn
            def parse_tab(tab, prefix=""):
                if not tab:
                    return None, None
                title = tab.select_one(".title_name_tab_mieng_nhan")
                name = title.text.strip() if title else ("sjc" if not prefix else "nhan")
                
                # Tìm giá trong div.bang_gia_vang_mieng_nhan
                bang_gia = tab.select_one(f".bang_gia_vang_mieng_nhan#bang_gia_hien_tai_trong_nuoc{prefix}")
                if not bang_gia:
                    return name, None
                    
                # Lấy giá mua vào và bán ra
                mua_vao = bang_gia.select_one(f"p#gia_mua_vao{prefix}")
                ban_ra = bang_gia.select_one(f"p#gia_ban_ra{prefix}")
                
                # Lấy thay đổi giá
                change_mua = bang_gia.select_one(f"p#gia_thay_doi_mua{prefix}")
                change_ban = bang_gia.select_one(f"p#gia_thay_doi_ban{prefix}")
                
                # Xử lý text của thay đổi giá (loại bỏ icon và format lại)
                def clean_change(el):
                    if not el:
                        return None
                    text = el.text.strip()
                    if not text:
                        return None
                    # Loại bỏ icon và khoảng trắng
                    text = text.replace("iconDown", "").replace("iconUp", "").strip()
                    return text
                    
                return name, {
                    "mua_vao": mua_vao.text.strip() if mua_vao else None,
                    "ban_ra": ban_ra.text.strip() if ban_ra else None,
                    "change_mua": clean_change(change_mua),
                    "change_ban": clean_change(change_ban)
                }
            
            sjc_tab = cafef_soup.find("div", id="name_tab_vang_mieng")
            nhan_tab = cafef_soup.find("div", id="name_tab_vang_nhan")
            gold_types = {}
            name_sjc, sjc = parse_tab(sjc_tab, "")
            if name_sjc and sjc:
                gold_types[name_sjc] = sjc
            name_nhan, nhan = parse_tab(nhan_tab, "_nhan")
            if name_nhan and nhan:
                gold_types[name_nhan] = nhan
            
            # Lấy chênh lệch vàng thế giới
            sapo_chart = cafef_soup.find("div", class_="sapo_chart_dien_bien")
            chenh_lech = None
            if sapo_chart:
                chenh_lech_text = sapo_chart.text.strip()
                chenh_lech_span = sapo_chart.find("span", class_="color_note_chenh_lech")
                if chenh_lech_span:
                    chenh_lech = chenh_lech_text
            
            cafef_data = {
                "gold_types": gold_types,
                "world_gold_price_difference": chenh_lech,
                "cafef_source": cafef_url
            }
            self._set_cached_data(cache_key, cafef_data)
            return cafef_data
        except Exception as e:
            log.error(f"Error getting cafef data: {str(e)}")
            return {"cafef_error": str(e)}

    def _get_world_gold_data(self, date, log):
        """Lấy giá vàng thế giới từ cafef.vn bằng Selenium"""
        try:
            # Check cache
            cache_key = f"world_gold_{date}" if date else "world_gold_latest"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data

            cafef_url = "https://cafef.vn/du-lieu/gia-vang-hom-nay/the-gioi.chn#data"
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(cafef_url)

            # Đợi phần giá vàng quốc tế xuất hiện
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "gia_vang_hien_tai"))
            )
            html = driver.page_source
            driver.quit()

            soup = BeautifulSoup(html, "html.parser")

            # Tìm container chính
            price_box = soup.find("div", class_="gia_vang_hien_tai")
            if not price_box:
                return {"world_gold_error": "Không tìm thấy box giá vàng quốc tế"}

            # Lấy giá USD
            price_usd = None
            price_usd_div = price_box.find("div", class_="price_vang_dola")
            if price_usd_div:
                try:
                    price_usd = float(price_usd_div.text.replace(",", "").strip())
                except:
                    pass

            # Lấy thay đổi và phần trăm
            change_usd = None
            change_percent = None
            price_change_div = price_box.find("div", class_="priceChange_vang_dola")
            if price_change_div:
                change_text = price_change_div.find("div", class_="down")
                if change_text:
                    try:
                        change_parts = change_text.text.strip().split()
                        if len(change_parts) >= 2:
                            change_usd = float(change_parts[0])
                            change_percent = change_parts[1].strip("()%")
                    except:
                        pass

            # Lấy thời gian cập nhật
            updated_at = None
            time_div = price_box.find("div", id="time_update_gia_vang")
            if time_div:
                updated_at = time_div.text.replace("Cập nhật lúc", "").strip()

            # Lấy giá quy đổi VND
            price_vnd = None
            note_div = price_box.find("div", class_="note_gia_vang_quoc_te")
            if note_div:
                for li in note_div.find_all("li"):
                    if "1 Ounce =" in li.text:
                        vnd_text = li.text.split("=")[1].strip()
                        price_vnd = vnd_text.replace("VNĐ", "").strip()
                        break

            formatted_data = {
                "world_gold": {
                    "price_usd": price_usd,
                    "change_usd": change_usd,
                    "change_percent": change_percent,
                    "price_vnd": price_vnd,
                    "updated_at": updated_at,
                    "source": cafef_url
                }
            }
            self._set_cached_data(cache_key, formatted_data)
            return formatted_data
        except Exception as e:
            log.error(f"Error getting world gold data: {str(e)}")
            return {"world_gold_error": str(e)}

    def _format_world_gold_context(self, world_gold_data):
        """Format world gold price data into readable text"""
        try:
            if not world_gold_data or "world_gold" not in world_gold_data:
                return None
                
            world_gold = world_gold_data["world_gold"]
            
            # Format price changes with direction indicators
            change_direction = "tăng" if world_gold.get("change_usd", 0) > 0 else "giảm"
            change_abs = abs(world_gold.get("change_usd", 0)) if world_gold.get("change_usd") is not None else None
            
            parts = ["Giá vàng thế giới:"]
            
            # Add USD price
            if world_gold.get("price_usd"):
                parts.append(f"- Giá hiện tại: {world_gold['price_usd']:,.2f} USD/Ounce")
            
            # Add price changes
            if change_abs is not None and world_gold.get("change_percent"):
                parts.append(f"- Biến động: {change_direction} {change_abs:.2f} USD ({world_gold['change_percent']}%)")

            # Add price difference if available
            if "world_gold_price_difference" in world_gold_data:
                parts.append(f"- Giá vàng trong nước chênh lệch với giá vàng thế giới ở mức: {world_gold_data['world_gold_price_difference']}")
                
            return "\n".join(parts)
        except Exception:
            return None

    def process(self, json_data, log):
        response = {"message": "Success", "status": 200}

        try:
            # 1. Lấy date từ payload
            raw_date = json_data.get("date")
            date = raw_date.strip() if isinstance(raw_date, str) and raw_date.strip() else None
            log.debug(f"Payload raw_date: {raw_date!r}, dùng date: {date!r}")

            # 2. Chạy song song việc lấy dữ liệu từ 3 nguồn
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_24h = executor.submit(self._get_24h_data, date, log)
                future_cafef = executor.submit(self._get_cafef_data, date, log)
                future_world = executor.submit(self._get_world_gold_data, date, log)
                
                # Lấy kết quả
                prices, url = future_24h.result()
                cafef_data = future_cafef.result() or {}
                world_gold_data = future_world.result() or {}

            if not prices:
                raise Exception("Không lấy được dữ liệu từ 24h.com.vn")

            # 3. Tạo formated_context với 000 cho các số
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

            # 4. Format world gold context
            context_formated_2 = self._format_world_gold_context(world_gold_data)

            # 5. Trả về tất cả nguồn
            response.update({
                "date": ref_date,
                "prices": prices,
                "context_formated": context_formated,
                "context_formated_2": context_formated_2,
                "source": url,
                **cafef_data,
                **world_gold_data
            })

        except Exception as e:
            log.error(traceback.format_exc())
            response.update({"message": str(e), "status": 500})

        return response