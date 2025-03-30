#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import sqlite3
import jieba
import math
from datetime import datetime
from collections import Counter

# 設定基本參數
DB_DIR = "/home/ubuntu/legal-ai-system/data/db"
DB_FILE = os.path.join(DB_DIR, "legal_db.sqlite")
AI_DIR = "/home/ubuntu/legal-ai-system/backend/ai"
LOG_FILE = os.path.join(AI_DIR, "legal_search_log.txt")

# 確保目錄存在
os.makedirs(AI_DIR, exist_ok=True)

# 記錄函數
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

# 載入關鍵詞提取系統
def load_keyword_extractor():
    try:
        import keyword_extractor
        log_message("成功載入關鍵詞提取系統")
        return keyword_extractor
    except Exception as e:
        log_message(f"載入關鍵詞提取系統失敗: {str(e)}")
        return None

# 從數據庫搜索法規
def search_laws(keywords, category=None, limit=10):
    try:
        # 連接到SQLite數據庫
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 構建搜索查詢
        query = """
        SELECT id, title, content, category, date
        FROM laws
        """
        
        # 如果有關鍵詞，使用FTS5全文搜索
        if keywords:
            keyword_str = " OR ".join([f'"{keyword}"' for keyword in keywords])
            query = f"""
            SELECT laws.id, laws.title, laws.content, laws.category, laws.date
            FROM laws_fts
            JOIN laws ON laws_fts.rowid = laws.id
            WHERE laws_fts MATCH '{keyword_str}'
            """
        
        # 如果有類別，添加類別過濾
        if category:
            if "WHERE" in query:
                query += f" AND laws.category = '{category}'"
            else:
                query += f" WHERE laws.category = '{category}'"
        
        # 添加排序和限制
        query += f" ORDER BY laws.id DESC LIMIT {limit}"
        
        # 執行查詢
        cursor.execute(query)
        results = cursor.fetchall()
        
        # 格式化結果
        laws = []
        for row in results:
            law = {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "category": row[3],
                "date": row[4]
            }
            laws.append(law)
        
        conn.close()
        
        log_message(f"從數據庫搜索到 {len(laws)} 條法規")
        return laws
    except Exception as e:
        log_message(f"從數據庫搜索法規失敗: {str(e)}")
        return []

# 從數據庫搜索判例
def search_cases(keywords, case_type=None, limit=10):
    try:
        # 連接到SQLite數據庫
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 構建搜索查詢
        query = """
        SELECT id, title, content, case_type, date, case_number
        FROM court_cases
        """
        
        # 如果有關鍵詞，使用FTS5全文搜索
        if keywords:
            keyword_str = " OR ".join([f'"{keyword}"' for keyword in keywords])
            query = f"""
            SELECT court_cases.id, court_cases.title, court_cases.content, court_cases.case_type, court_cases.date, court_cases.case_number
            FROM court_cases_fts
            JOIN court_cases ON court_cases_fts.rowid = court_cases.id
            WHERE court_cases_fts MATCH '{keyword_str}'
            """
        
        # 如果有案件類型，添加類型過濾
        if case_type:
            if "WHERE" in query:
                query += f" AND court_cases.case_type = '{case_type}'"
            else:
                query += f" WHERE court_cases.case_type = '{case_type}'"
        
        # 添加排序和限制
        query += f" ORDER BY court_cases.id DESC LIMIT {limit}"
        
        # 執行查詢
        cursor.execute(query)
        results = cursor.fetchall()
        
        # 格式化結果
        cases = []
        for row in results:
            case = {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "case_type": row[3],
                "date": row[4],
                "case_number": row[5]
            }
            cases.append(case)
        
        conn.close()
        
        log_message(f"從數據庫搜索到 {len(cases)} 條判例")
        return cases
    except Exception as e:
        log_message(f"從數據庫搜索判例失敗: {str(e)}")
        return []

# 計算文本相似度（基於詞頻）
def calculate_text_similarity(text1, text2):
    try:
        # 分詞
        words1 = jieba.lcut(text1)
        words2 = jieba.lcut(text2)
        
        # 計算詞頻
        counter1 = Counter(words1)
        counter2 = Counter(words2)
        
        # 獲取所有不重複的詞
        all_words = set(counter1.keys()) | set(counter2.keys())
        
        # 計算餘弦相似度
        numerator = sum(counter1.get(word, 0) * counter2.get(word, 0) for word in all_words)
        denominator1 = math.sqrt(sum(counter1.get(word, 0) ** 2 for word in all_words))
        denominator2 = math.sqrt(sum(counter2.get(word, 0) ** 2 for word in all_words))
        
        if denominator1 == 0 or denominator2 == 0:
            return 0
        
        similarity = numerator / (denominator1 * denominator2)
        return similarity
    except Exception as e:
        log_message(f"計算文本相似度失敗: {str(e)}")
        return 0

# 根據問題分析結果搜索相關法規和判例
def search_by_question_analysis(analysis_result, law_limit=5, case_limit=5):
    try:
        # 提取關鍵詞
        keywords = []
        
        # 從TF-IDF關鍵詞中提取
        if "tfidf_keywords" in analysis_result and analysis_result["tfidf_keywords"]:
            keywords.extend([keyword for keyword, weight in analysis_result["tfidf_keywords"]])
        
        # 從TextRank關鍵詞中提取
        if "textrank_keywords" in analysis_result and analysis_result["textrank_keywords"]:
            keywords.extend([keyword for keyword, weight in analysis_result["textrank_keywords"]])
        
        # 從法律關鍵詞中提取
        if "legal_keywords" in analysis_result and analysis_result["legal_keywords"]:
            keywords.extend([keyword for keyword, info, freq in analysis_result["legal_keywords"]])
        
        # 從實體中提取
        if "entities" in analysis_result and analysis_result["entities"]:
            keywords.extend([entity[1] for entity in analysis_result["entities"]])
        
        # 從行為中提取
        if "actions" in analysis_result and analysis_result["actions"]:
            keywords.extend(analysis_result["actions"])
        
        # 去重
        keywords = list(set(keywords))
        
        # 獲取問題類別
        category = None
        case_type = None
        if "category" in analysis_result and analysis_result["category"]:
            category = analysis_result["category"]
            # 將問題類別映射到案件類型
            category_to_case_type = {
                "刑事": "刑事",
                "民事": "民事",
                "行政": "行政",
                "商業": "民事",  # 商業糾紛通常屬於民事案件
                "勞工": "民事",  # 勞資糾紛通常屬於民事案件
                "家事": "民事"   # 家事案件通常屬於民事案件
            }
            case_type = category_to_case_type.get(category, None)
        
        log_message(f"搜索關鍵詞: {keywords}, 類別: {category}, 案件類型: {case_type}")
        
        # 搜索相關法規
        laws = search_laws(keywords, category, law_limit)
        
        # 搜索相關判例
        cases = search_cases(keywords, case_type, case_limit)
        
        # 計算相關性分數
        original_text = analysis_result.get("original_text", "")
        
        # 為法規計算相關性分數
        for law in laws:
            law["similarity"] = calculate_text_similarity(original_text, law["content"])
        
        # 為判例計算相關性分數
        for case in cases:
            case["similarity"] = calculate_text_similarity(original_text, case["content"])
        
        # 按相關性排序
        laws.sort(key=lambda x: x["similarity"], reverse=True)
        cases.sort(key=lambda x: x["similarity"], reverse=True)
        
        # 返回搜索結果
        search_result = {
            "laws": laws,
            "cases": cases,
            "keywords": keywords,
            "category": category,
            "case_type": case_type
        }
        
        log_message(f"搜索完成，找到 {len(laws)} 條相關法規和 {len(cases)} 條相關判例")
        return search_result
    except Exception as e:
        log_message(f"根據問題分析結果搜索相關法規和判例失敗: {str(e)}")
        return {"laws": [], "cases": [], "keywords": [], "category": None, "case_type": None}

# 保存搜索結果
def save_search_result(result, filename):
    try:
        output_path = os.path.join(AI_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        log_message(f"成功保存搜索結果: {output_path}")
        return True
    except Exception as e:
        log_message(f"保存搜索結果失敗: {str(e)}")
        return False

# 主函數
def main():
    log_message("開始實現法律搜索功能")
    
    # 載入關鍵詞提取系統
    keyword_extractor = load_keyword_extractor()
    if not keyword_extractor:
        log_message("無法載入關鍵詞提取系統，無法繼續")
        return
    
    # 測試問題
    test_questions = [
        "我不小心撞到路人，要怎麼樣無罪?",
        "如果我的鄰居深夜製造噪音，我可以採取什麼法律行動?",
        "我的房東未經我同意就進入我的租屋處，這違法嗎?",
        "我的公司拖欠薪資三個月了，我該怎麼辦?",
        "如果我收到交通罰單但認為不合理，有什麼申訴管道?"
    ]
    
    # 對每個測試問題進行搜索
    for i, question in enumerate(test_questions):
        log_message(f"處理測試問題 {i+1}: {question}")
        
        # 分析問題
        analysis_result = keyword_extractor.analyze_question(question)
        
        # 根據分析結果搜索相關法規和判例
        search_result = search_by_question_analysis(analysis_result)
        
        # 保存搜索結果
        save_search_result(search_result, f"search_result_{i+1}.json")
    
    log_message("法律搜索功能實現完成")

if __name__ == "__main__":
    main()
