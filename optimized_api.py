from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sqlite3
import time
import json
import os
import logging
from datetime import datetime
import jieba
import re

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("legal-ai-api")

# 創建FastAPI應用
app = FastAPI(
    title="台灣法律AI系統API",
    description="提供法律問答、法規查詢與判例查詢功能的API",
    version="1.0.0"
)

# 添加CORS中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生產環境中應該限制為特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 數據庫連接
DB_PATH = "/home/ubuntu/legal-ai-system/data/legal_db.sqlite"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# 請求模型
class QuestionRequest(BaseModel):
    question: str

class FeedbackRequest(BaseModel):
    rating: int
    comment: str
    timestamp: str

class HistoryItem(BaseModel):
    type: str
    content: str
    timestamp: str

# 緩存
cache = {}
CACHE_EXPIRY = 3600  # 1小時，單位秒

def get_cache(key):
    if key in cache:
        data, timestamp = cache[key]
        if time.time() - timestamp < CACHE_EXPIRY:
            return data
    return None

def set_cache(key, data):
    cache[key] = (data, time.time())

# 後台任務
def log_request(question: str, ip: str):
    logger.info(f"收到問題: '{question}' 來自 {ip}")

# 關鍵詞提取
def extract_keywords(text):
    # 使用jieba進行分詞
    words = jieba.cut(text)
    # 過濾停用詞和標點符號
    stopwords = {'的', '了', '和', '是', '在', '我', '有', '這', '那', '你', '他', '她', '它', '們', '什麼', '怎麼', '如何', '為什麼'}
    keywords = [word for word in words if word not in stopwords and len(word) > 1 and not re.match(r'[^\w\s]', word)]
    return keywords

# 法律搜索
def search_laws(keywords, db):
    if not keywords:
        return []
    
    # 構建查詢條件
    query_conditions = " OR ".join(["title LIKE ? OR content LIKE ?" for _ in keywords])
    params = []
    for keyword in keywords:
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    
    query = f"SELECT * FROM laws WHERE {query_conditions} LIMIT 5"
    
    cursor = db.cursor()
    cursor.execute(query, params)
    laws = [dict(row) for row in cursor.fetchall()]
    return laws

# 判例搜索
def search_cases(keywords, db):
    if not keywords:
        return []
    
    # 構建查詢條件
    query_conditions = " OR ".join(["title LIKE ? OR content LIKE ?" for _ in keywords])
    params = []
    for keyword in keywords:
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    
    query = f"SELECT * FROM cases WHERE {query_conditions} LIMIT 5"
    
    cursor = db.cursor()
    cursor.execute(query, params)
    cases = [dict(row) for row in cursor.fetchall()]
    return cases

# 生成回答
def generate_response(question, laws, cases):
    # 簡單的模板化回答
    if not laws and not cases:
        return "很抱歉，我無法找到與您問題相關的法律信息。請嘗試使用不同的關鍵詞或更具體的問題。"
    
    response = f"根據您的問題「{question}」，我找到了以下相關法律信息：\n\n"
    
    if laws:
        response += "相關法規：\n"
        for law in laws:
            response += f"- {law['title']}: {law['content'][:100]}...\n"
        response += "\n"
    
    if cases:
        response += "相關判例：\n"
        for case in cases:
            response += f"- {case['title']}: {case['content'][:100]}...\n"
        response += "\n"
    
    response += "法律建議：\n"
    
    # 根據問題類型生成不同的建議
    if "撞到" in question or "車禍" in question:
        response += "1. 保持冷靜，確保安全，並檢查是否有人受傷。\n"
        response += "2. 如有人受傷，立即撥打119尋求醫療協助。\n"
        response += "3. 報警並等待警察到場處理。\n"
        response += "4. 收集證據，包括照片、目擊者聯繫方式等。\n"
        response += "5. 聯繫您的保險公司。\n"
        response += "6. 如果對方提出私下和解，建議謹慎考慮，最好諮詢專業律師。\n"
    elif "離婚" in question:
        response += "1. 台灣法律規定離婚方式包括協議離婚和裁判離婚。\n"
        response += "2. 協議離婚需雙方合意，並至戶政事務所辦理登記。\n"
        response += "3. 裁判離婚需有法定原因，如重大過失、虐待、惡意遺棄等。\n"
        response += "4. 建議先尋求專業律師諮詢，了解您的權益和財產分配問題。\n"
    elif "噪音" in question or "鄰居" in question:
        response += "1. 首先嘗試與鄰居友好溝通，說明噪音對您的影響。\n"
        response += "2. 如溝通無效，可向當地環保局投訴，他們會進行噪音測量。\n"
        response += "3. 如噪音超過法定標準，環保局可對製造噪音者開罰。\n"
        response += "4. 持續性噪音問題可考慮提起民事訴訟，要求停止侵害和損害賠償。\n"
    else:
        response += "1. 根據您的問題，建議您先了解相關法規的具體內容。\n"
        response += "2. 收集並保存所有相關證據，包括文件、照片、錄音等。\n"
        response += "3. 考慮尋求專業律師的建議，以獲得針對您具體情況的法律意見。\n"
        response += "4. 在法庭上，清晰表達事實，並引用相關法條支持您的主張。\n"
    
    response += "\n請注意，以上建議僅供參考，不構成法律意見。具體情況可能有所不同，建議您諮詢專業律師獲取針對您具體情況的法律建議。"
    
    return response

# API端點
@app.get("/")
def read_root():
    return {"message": "歡迎使用台灣法律AI系統API"}

@app.post("/api/question")
async def answer_question(
    request: QuestionRequest, 
    background_tasks: BackgroundTasks, 
    db: sqlite3.Connection = Depends(get_db)
):
    question = request.question
    
    # 記錄請求
    background_tasks.add_task(log_request, question, "127.0.0.1")
    
    # 檢查緩存
    cache_key = f"question_{question}"
    cached_result = get_cache(cache_key)
    if cached_result:
        return cached_result
    
    # 提取關鍵詞
    keywords = extract_keywords(question)
    
    # 搜索相關法規和判例
    laws = search_laws(keywords, db)
    cases = search_cases(keywords, db)
    
    # 生成回答
    response = generate_response(question, laws, cases)
    
    # 構建結果
    result = {
        "question": question,
        "response": response,
        "search_result": {
            "laws": laws,
            "cases": cases
        }
    }
    
    # 設置緩存
    set_cache(cache_key, result)
    
    return result

@app.get("/api/laws")
async def get_laws(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
    db: sqlite3.Connection = Depends(get_db)
):
    # 檢查緩存
    cache_key = f"laws_{keyword}_{category}_{limit}"
    cached_result = get_cache(cache_key)
    if cached_result:
        return cached_result
    
    cursor = db.cursor()
    query = "SELECT * FROM laws WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND (title LIKE ? OR content LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    query += f" LIMIT {limit}"
    
    cursor.execute(query, params)
    laws = [dict(row) for row in cursor.fetchall()]
    
    # 設置緩存
    set_cache(cache_key, laws)
    
    return laws

@app.get("/api/cases")
async def get_cases(
    keyword: Optional[str] = None,
    case_type: Optional[str] = None,
    limit: int = 20,
    db: sqlite3.Connection = Depends(get_db)
):
    # 檢查緩存
    cache_key = f"cases_{keyword}_{case_type}_{limit}"
    cached_result = get_cache(cache_key)
    if cached_result:
        return cached_result
    
    cursor = db.cursor()
    query = "SELECT * FROM cases WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND (title LIKE ? OR content LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    
    if case_type:
        query += " AND case_type = ?"
        params.append(case_type)
    
    query += f" LIMIT {limit}"
    
    cursor.execute(query, params)
    cases = [dict(row) for row in cursor.fetchall()]
    
    # 設置緩存
    set_cache(cache_key, cases)
    
    return cases

@app.get("/api/laws/{law_id}")
async def get_law_detail(
    law_id: int,
    db: sqlite3.Connection = Depends(get_db)
):
    # 檢查緩存
    cache_key = f"law_detail_{law_id}"
    cached_result = get_cache(cache_key)
    if cached_result:
        return cached_result
    
    cursor = db.cursor()
    cursor.execute("SELECT * FROM laws WHERE id = ?", (law_id,))
    law = cursor.fetchone()
    
    if not law:
        raise HTTPException(status_code=404, detail="法規未找到")
    
    result = dict(law)
    
    # 設置緩存
    set_cache(cache_key, result)
    
    return result

@app.get("/api/cases/{case_id}")
async def get_case_detail(
    case_id: int,
    db: sqlite3.Connection = Depends(get_db)
):
    # 檢查緩存
    cache_key = f"case_detail_{case_id}"
    cached_result = get_cache(cache_key)
    if cached_result:
        return cached_result
    
    cursor = db.cursor()
    cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    case = cursor.fetchone()
    
    if not case:
        raise HTTPException(status_code=404, detail="判例未找到")
    
    result = dict(case)
    
    # 設置緩存
    set_cache(cache_key, result)
    
    return result

@app.post("/api/feedback")
async def save_feedback(
    feedback: FeedbackRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO feedback (rating, comment, timestamp) VALUES (?, ?, ?)",
        (feedback.rating, feedback.comment, feedback.timestamp)
    )
    db.commit()
    
    return {"message": "反饋已保存"}

@app.get("/api/history")
async def get_history(
    db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM history ORDER BY timestamp DESC LIMIT 20")
    history = [dict(row) for row in cursor.fetchall()]
    
    return history

@app.post("/api/history")
async def save_history(
    history_item: HistoryItem,
    db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO history (type, content, timestamp) VALUES (?, ?, ?)",
        (history_item.type, history_item.content, history_item.timestamp)
    )
    db.commit()
    
    return {"message": "歷史記錄已保存"}

# 啟動服務器
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
