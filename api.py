#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import sys
import os
import json
from datetime import datetime

# 添加backend目錄到Python路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入自定義模塊
try:
    import keyword_extractor
    import legal_search
    import response_generator
except ImportError as e:
    print(f"導入模塊失敗: {str(e)}")
    sys.exit(1)

# 設定基本參數
AI_DIR = "/home/ubuntu/legal-ai-system/backend/ai"
LOG_FILE = os.path.join(AI_DIR, "api_log.txt")

# 確保目錄存在
os.makedirs(AI_DIR, exist_ok=True)

# 記錄函數
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

# 創建FastAPI應用
app = FastAPI(
    title="台灣法律AI系統API",
    description="提供法律問答、法規搜索和判例查詢功能的API",
    version="1.0.0"
)

# 添加CORS中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有來源
    allow_credentials=True,
    allow_methods=["*"],  # 允許所有方法
    allow_headers=["*"],  # 允許所有頭部
)

# 定義請求和響應模型
class QuestionRequest(BaseModel):
    question: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    keywords: List[str]
    category: Optional[str] = None
    case_type: Optional[str] = None
    limit: Optional[int] = 10

class AnalysisResponse(BaseModel):
    keywords: List[str]
    category: Optional[str] = None
    entities: List[Dict[str, Any]]
    actions: List[str]

class SearchResponse(BaseModel):
    laws: List[Dict[str, Any]]
    cases: List[Dict[str, Any]]
    keywords: List[str]
    category: Optional[str] = None
    case_type: Optional[str] = None

class QuestionResponse(BaseModel):
    question: str
    response: str
    analysis: AnalysisResponse
    search_result: SearchResponse
    generated_at: str

# 載入回答模板
def load_response_templates():
    try:
        template_path = os.path.join(AI_DIR, "response_templates.json")
        with open(template_path, "r", encoding="utf-8") as f:
            templates = json.load(f)
        log_message(f"成功載入回答模板，共 {len(templates)} 種類型")
        return templates
    except Exception as e:
        log_message(f"載入回答模板失敗: {str(e)}")
        return {}

# API路由
@app.get("/")
async def root():
    return {"message": "歡迎使用台灣法律AI系統API"}

@app.post("/api/question", response_model=QuestionResponse)
async def answer_question(request: QuestionRequest):
    try:
        log_message(f"收到問題: {request.question}")
        
        # 分析問題
        analysis_result = keyword_extractor.analyze_question(request.question)
        
        # 搜索相關法規和判例
        search_result = legal_search.search_by_question_analysis(analysis_result)
        
        # 載入回答模板
        templates = load_response_templates()
        
        # 生成回答
        full_response = response_generator.generate_response(
            request.question, 
            analysis_result, 
            search_result, 
            templates
        )
        
        # 格式化響應
        response = {
            "question": request.question,
            "response": full_response["response"],
            "analysis": {
                "keywords": analysis_result.get("tfidf_keywords", []),
                "category": analysis_result.get("category"),
                "entities": analysis_result.get("entities", []),
                "actions": analysis_result.get("actions", [])
            },
            "search_result": search_result,
            "generated_at": datetime.now().isoformat()
        }
        
        log_message("成功生成回答")
        return response
    except Exception as e:
        log_message(f"處理問題失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"處理問題失敗: {str(e)}")

@app.post("/api/search", response_model=SearchResponse)
async def search_legal_documents(request: SearchRequest):
    try:
        log_message(f"收到搜索請求: 關鍵詞={request.keywords}, 類別={request.category}, 案件類型={request.case_type}")
        
        # 搜索法規
        laws = legal_search.search_laws(request.keywords, request.category, request.limit)
        
        # 搜索判例
        cases = legal_search.search_cases(request.keywords, request.case_type, request.limit)
        
        # 格式化響應
        response = {
            "laws": laws,
            "cases": cases,
            "keywords": request.keywords,
            "category": request.category,
            "case_type": request.case_type
        }
        
        log_message(f"搜索完成，找到 {len(laws)} 條相關法規和 {len(cases)} 條相關判例")
        return response
    except Exception as e:
        log_message(f"搜索失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失敗: {str(e)}")

@app.get("/api/laws", response_model=List[Dict[str, Any]])
async def get_laws(
    keyword: Optional[str] = Query(None, description="搜索關鍵詞"),
    category: Optional[str] = Query(None, description="法規類別"),
    limit: int = Query(10, description="返回結果數量限制")
):
    try:
        log_message(f"收到法規查詢請求: 關鍵詞={keyword}, 類別={category}")
        
        # 搜索法規
        keywords = [keyword] if keyword else []
        laws = legal_search.search_laws(keywords, category, limit)
        
        log_message(f"法規查詢完成，找到 {len(laws)} 條相關法規")
        return laws
    except Exception as e:
        log_message(f"法規查詢失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"法規查詢失敗: {str(e)}")

@app.get("/api/cases", response_model=List[Dict[str, Any]])
async def get_cases(
    keyword: Optional[str] = Query(None, description="搜索關鍵詞"),
    case_type: Optional[str] = Query(None, description="案件類型"),
    limit: int = Query(10, description="返回結果數量限制")
):
    try:
        log_message(f"收到判例查詢請求: 關鍵詞={keyword}, 案件類型={case_type}")
        
        # 搜索判例
        keywords = [keyword] if keyword else []
        cases = legal_search.search_cases(keywords, case_type, limit)
        
        log_message(f"判例查詢完成，找到 {len(cases)} 條相關判例")
        return cases
    except Exception as e:
        log_message(f"判例查詢失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"判例查詢失敗: {str(e)}")

@app.get("/api/categories")
async def get_categories():
    try:
        # 返回預定義的法律問題類別
        categories = {
            "刑事": "刑事相關法律問題",
            "民事": "民事相關法律問題",
            "行政": "行政相關法律問題",
            "商業": "商業相關法律問題",
            "勞工": "勞工相關法律問題",
            "家事": "家事相關法律問題"
        }
        
        return categories
    except Exception as e:
        log_message(f"獲取類別失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取類別失敗: {str(e)}")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# 主函數
def main():
    log_message("啟動台灣法律AI系統API服務")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
