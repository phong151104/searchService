import traceback
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

from common_service import CommonService

class WikiSearchService(CommonService):
    service_name = "wiki_search_service"
    
    # Sử dụng Wikipedia tiếng Việt
    WIKI_API_URL = "https://vi.wikipedia.org/w/api.php"
    
    def __init__(self):
        super(WikiSearchService, self).__init__()

    def process(self, json_data, log):
        response = {
            "message": "Success",
            "status": 200
        }

        try:
            query = json_data.get("query", "").strip()
            if not query:
                response.update({
                    "message": "Bạn chưa cung cấp từ khóa tìm kiếm.",
                    "status": 400
                })
                return response

            log.debug(f"Searching Wikipedia for: {query}")

            # 1. Search Wikipedia
            search_results = self.search_wikipedia(query)
            if not search_results:
                response.update({
                    "message": f"Không tìm thấy kết quả cho '{query}'.",
                    "status": 404
                })
                return response

            # 2. Get detailed content for all results
            pageids = [str(item["pageid"]) for item in search_results]
            titles = {str(item["pageid"]): item["title"] for item in search_results}
            details = self.get_multiple_wiki_contents(pageids, titles)

            # 3. Merge details into results
            full_results = []
            for item in search_results:
                detail = details.get(str(item["pageid"]), {})
                merged = {**item, **detail}
                # Lấy HTML cho từng bài
                html = self.get_html_content(item["title"])
                # merged["html"] = html
                merged["html_cleaned"] = self.clean_html_content(html)
                # Parse HTML để lấy đoạn văn đầu và bảng
                parsed = self.parse_html_content(html)
                merged["first_paragraph"] = parsed["first_paragraph"]
                # merged["tables"] = parsed["tables"]
                full_results.append(merged)

            response.update({
                "query": query,
                "results": full_results,
                "source": full_results[0].get("url", "") if full_results else ""
            })

        except Exception as e:
            log.error(traceback.format_exc())
            response.update({
                "message": str(e),
                "status": 500
            })

        return response

    def search_wikipedia(self, query):
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srlimit": 5,
            "srprop": "snippet|title|pageid"
        }
        response = requests.get(self.WIKI_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        results = []
        if "query" in data and "search" in data["query"]:
            for item in data["query"]["search"]:
                results.append({
                    "title": item["title"],
                    "snippet": BeautifulSoup(item["snippet"], "html.parser").get_text(),
                    "pageid": item["pageid"],
                    "url": f"https://en.wikipedia.org/?curid={item['pageid']}"
                })
        return results

    def get_multiple_wiki_contents(self, pageids, titles=None):
        # Lấy nội dung chi tiết cho nhiều pageid cùng lúc, có xử lý redirect
        params = {
            "action": "query",
            "format": "json",
            "pageids": "|".join(pageids),
            "prop": "extracts|info",
            "explaintext": True,
            "inprop": "url",
            "redirects": 1
        }
        response = requests.get(self.WIKI_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        details = {}
        missing_titles = []
        if "query" in data and "pages" in data["query"]:
            for pid, page in data["query"]["pages"].items():
                extract = page.get("extract", "")
                details[pid] = {
                    "extract": extract,
                    "fullurl": page.get("fullurl", ""),
                }
                if not extract and titles:
                    missing_titles.append(titles[pid])
        # Nếu có bài bị thiếu extract, thử lấy lại theo title và có redirect
        if missing_titles:
            params = {
                "action": "query",
                "format": "json",
                "titles": "|".join(missing_titles),
                "prop": "extracts|info",
                "explaintext": True,
                "inprop": "url",
                "redirects": 1
            }
            response = requests.get(self.WIKI_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            if "query" in data and "pages" in data["query"]:
                for page in data["query"]["pages"].values():
                    title = page.get("title", "")
                    extract = page.get("extract", "")
                    for pid, t in titles.items():
                        if t == title and not details[pid]["extract"]:
                            details[pid]["extract"] = extract
                            details[pid]["fullurl"] = page.get("fullurl", "")
        return details

    def get_html_content(self, title):
        params = {
            "action": "parse",
            "format": "json",
            "page": title,
            "prop": "text",
            "redirects": 1
        }
        response = requests.get(self.WIKI_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        html = ""
        if "parse" in data and "text" in data["parse"]:
            html = data["parse"]["text"]["*"]
        return html

    def parse_html_content(self, html):
        soup = BeautifulSoup(html, "html.parser")
        # Lấy đoạn văn đầu tiên (không nằm trong infobox)
        first_paragraph = ""
        for p in soup.select(".mw-parser-output > p"):
            text = p.get_text(strip=True)
            if text:
                first_paragraph = text
                break

        # Lấy tất cả các bảng (dưới dạng HTML)
        tables = []
        for table in soup.select(".mw-parser-output > table"):
            tables.append(str(table))

        return {
            "first_paragraph": first_paragraph,
            "tables": tables
        }

    def clean_html_content(self, html):
        soup = BeautifulSoup(html, "html.parser")
        main_content = soup.select_one(".mw-parser-output")
        if not main_content:
            return ""

        # Remove unnecessary elements but preserve content
        for tag in main_content.find_all(["script", "style", "nav", "footer", "form", "aside", "noscript", "link"]):
            # If the tag contains important text, extract it before removing
            if tag.get_text(strip=True):
                new_tag = soup.new_tag("p")
                new_tag.string = tag.get_text(strip=True)
                tag.replace_with(new_tag)
            else:
                tag.decompose()

        # Remove elements with specific classes but preserve their content
        for cls in ["mw-editsection", "reference", "reflist", "navbox", "metadata", "ambox", 
                   "infobox-above", "mw-empty-elt", "noprint", "navbox-styles"]:
            for el in main_content.select(f'.{cls}'):
                # Preserve text content if it exists
                if el.get_text(strip=True):
                    new_tag = soup.new_tag("p")
                    new_tag.string = el.get_text(strip=True)
                    el.replace_with(new_tag)
                else:
                    el.decompose()

        # Remove comments
        for comment in main_content.find_all(text=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()

        # Clean up remaining elements while preserving structure
        for tag in main_content.find_all():
            # Keep important attributes for structure
            if tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # Preserve heading levels
                continue
            elif tag.name == 'a':
                # Keep href and title for links
                attrs = dict(tag.attrs)
                for attr in attrs:
                    if attr not in ['href', 'title']:
                        del tag.attrs[attr]
            elif tag.name == 'img':
                # Keep src and alt for images
                attrs = dict(tag.attrs)
                for attr in attrs:
                    if attr not in ['src', 'alt']:
                        del tag.attrs[attr]
            else:
                # Remove unnecessary attributes but keep content
                for attr in ['class', 'style', 'id', 'data-*', 'typeof', 'rel']:
                    if attr in tag.attrs:
                        del tag.attrs[attr]

        # Remove truly empty elements (no text and no children)
        for tag in main_content.find_all():
            if not tag.get_text(strip=True) and not tag.find_all():
                tag.decompose()

        # Preserve list structure
        for ul in main_content.find_all('ul'):
            if not ul.get_text(strip=True):
                ul.decompose()

        for ol in main_content.find_all('ol'):
            if not ol.get_text(strip=True):
                ol.decompose()

        return str(main_content)
