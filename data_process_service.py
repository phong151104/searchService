import json
from common_service import CommonService

class DataProcessService(CommonService):
    service_name = "data_process"

    def flatten_items(self, items, log):
        flat = []
        for item in items:
            item_copy = dict(item)
            doc_citation = item_copy.get("documentCitation", "")
            link = ""
            doc_citation_parsed = []
            if isinstance(doc_citation, str):
                try:
                    doc_citation_parsed = json.loads(doc_citation)
                except Exception:
                    doc_citation_parsed = []
            elif isinstance(doc_citation, list):
                doc_citation_parsed = doc_citation
            if doc_citation_parsed and isinstance(doc_citation_parsed, list):
                for doc in doc_citation_parsed:
                    if isinstance(doc, dict) and doc.get("urlDisplay"):
                        link = doc["urlDisplay"]
                        break
            # Chỉ lấy các trường cần thiết
            filtered_item = {
                "title": item_copy.get("title", ""),
                "question": item_copy.get("question", ""),
                "answer": item_copy.get("answer", ""),
                "questionIndex": item_copy.get("questionIndex", ""),
                "documentCitation": doc_citation,
                "link": link
            }
            flat.append(filtered_item)
            children = item_copy.pop("children", [])
            if isinstance(children, list) and children:
                flat.extend(self.flatten_items(children, log))
        return flat

    def process(self, json_data, log):
        try:
            data_list = json_data.get("data", [])
            result = self.flatten_items(data_list, log)
            return {
                "status": 200,
                "data": result
            }
        except Exception as e:
            log.error(f"Error processing data: {str(e)}")
            return {
                "status": 500,
                "error": str(e)
            } 