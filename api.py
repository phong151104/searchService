from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
from wiki_search import WikiSearchService

# Cấu hình logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

app = FastAPI(
    title="Wikipedia Search API",
    description="API tìm kiếm thông tin từ Wikipedia tiếng Việt",
    version="1.0.0"
)

# Khởi tạo service
wiki_service = WikiSearchService()

class SearchRequest(BaseModel):
    query: str

@app.post("/search")
async def search_wikipedia(request: SearchRequest):
    """
    Tìm kiếm thông tin từ Wikipedia
    
    - **query**: Từ khóa tìm kiếm
    """
    result = wiki_service.process({"query": request.query}, log)
    
    if result["status"] != 200:
        raise HTTPException(
            status_code=result["status"],
            detail=result["message"]
        )
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 