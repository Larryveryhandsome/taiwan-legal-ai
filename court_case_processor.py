#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import codecs
import sqlite3
from datetime import datetime

# 設定基本參數
DATA_DIR = "/home/ubuntu/legal-ai-system/data/raw/cases"
PROCESSED_DIR = "/home/ubuntu/legal-ai-system/data/processed/cases"
DB_DIR = "/home/ubuntu/legal-ai-system/data/db"
DB_FILE = os.path.join(DB_DIR, "legal_db.sqlite")
LOG_FILE = "/home/ubuntu/legal-ai-system/data/processed/cases_process_log.txt"

# 確保目錄存在
os.makedirs(PROCESSED_DIR, exist_ok=True)

# 記錄函數
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

# 處理帶有BOM的UTF-8文件
def read_json_with_bom(file_path):
    try:
        with codecs.open(file_path, 'r', 'utf-8-sig') as f:
            return json.load(f)
    except Exception as e:
        log_message(f"讀取JSON文件失敗 {file_path}: {str(e)}")
        return None

# 清理和結構化裁判書數據
def process_court_case_data(raw_data, source_file):
    processed_cases = []
    
    try:
        # 處理不同格式的裁判書數據
        if isinstance(raw_data, dict):
            # 處理單個裁判書
            case = {}
            
            # 提取常見字段
            case_id = raw_data.get("id") or raw_data.get("JID") or ""
            title = raw_data.get("title") or raw_data.get("JTITLE") or ""
            content = raw_data.get("content") or raw_data.get("JFULL") or ""
            date = raw_data.get("date") or raw_data.get("JDATE") or ""
            case_number = raw_data.get("JNO") or ""
            case_type = raw_data.get("JCASE") or ""
            year = raw_data.get("JYEAR") or ""
            
            if case_id or title:
                case = {
                    "case_id": case_id,
                    "title": title,
                    "content": content,
                    "date": date,
                    "case_number": case_number,
                    "case_type": case_type,
                    "year": year,
                    "source_file": source_file,
                    "processed_date": datetime.now().isoformat()
                }
                processed_cases.append(case)
        
        elif isinstance(raw_data, list):
            # 處理裁判書列表
            for item in raw_data:
                if isinstance(item, dict):
                    case = {}
                    
                    # 提取常見字段
                    case_id = item.get("id") or item.get("JID") or ""
                    title = item.get("title") or item.get("JTITLE") or ""
                    content = item.get("content") or item.get("JFULL") or ""
                    date = item.get("date") or item.get("JDATE") or ""
                    case_number = item.get("JNO") or ""
                    case_type = item.get("JCASE") or ""
                    year = item.get("JYEAR") or ""
                    
                    if case_id or title:
                        case = {
                            "case_id": case_id,
                            "title": title,
                            "content": content,
                            "date": date,
                            "case_number": case_number,
                            "case_type": case_type,
                            "year": year,
                            "source_file": source_file,
                            "processed_date": datetime.now().isoformat()
                        }
                        processed_cases.append(case)
        
        log_message(f"從 {source_file} 處理了 {len(processed_cases)} 條裁判書數據")
        return processed_cases
    
    except Exception as e:
        log_message(f"處理裁判書數據失敗 {source_file}: {str(e)}")
        return []

# 保存處理後的數據到JSON文件
def save_processed_data(data, filename):
    try:
        output_path = os.path.join(PROCESSED_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log_message(f"成功保存處理後數據: {output_path}")
        return True
    except Exception as e:
        log_message(f"保存處理後數據失敗 {filename}: {str(e)}")
        return False

# 將數據導入SQLite數據庫
def import_to_sqlite(data):
    try:
        # 連接到SQLite數據庫
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 創建裁判書表（如果不存在）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS court_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT,
            title TEXT,
            content TEXT,
            date TEXT,
            case_number TEXT,
            case_type TEXT,
            year TEXT,
            source_file TEXT,
            processed_date TEXT,
            UNIQUE(case_id, case_number)
        )
        ''')
        
        # 創建全文搜索索引
        cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS court_cases_fts USING fts5(
            title, content, case_type,
            content='court_cases',
            content_rowid='id'
        )
        ''')
        
        # 創建觸發器以保持FTS索引同步
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS court_cases_ai AFTER INSERT ON court_cases BEGIN
            INSERT INTO court_cases_fts(rowid, title, content, case_type)
            VALUES (new.id, new.title, new.content, new.case_type);
        END
        ''')
        
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS court_cases_ad AFTER DELETE ON court_cases BEGIN
            INSERT INTO court_cases_fts(court_cases_fts, rowid, title, content, case_type)
            VALUES ('delete', old.id, old.title, old.content, old.case_type);
        END
        ''')
        
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS court_cases_au AFTER UPDATE ON court_cases BEGIN
            INSERT INTO court_cases_fts(court_cases_fts, rowid, title, content, case_type)
            VALUES ('delete', old.id, old.title, old.content, old.case_type);
            INSERT INTO court_cases_fts(rowid, title, content, case_type)
            VALUES (new.id, new.title, new.content, new.case_type);
        END
        ''')
        
        # 導入數據
        success_count = 0
        for case in data:
            try:
                cursor.execute('''
                INSERT OR IGNORE INTO court_cases 
                (case_id, title, content, date, case_number, case_type, year, source_file, processed_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    case.get("case_id", ""),
                    case.get("title", ""),
                    case.get("content", ""),
                    case.get("date", ""),
                    case.get("case_number", ""),
                    case.get("case_type", ""),
                    case.get("year", ""),
                    case.get("source_file", ""),
                    case.get("processed_date", "")
                ))
                
                if cursor.rowcount > 0:
                    success_count += 1
            except Exception as e:
                log_message(f"導入單條裁判書數據失敗: {str(e)}")
        
        conn.commit()
        log_message(f"成功導入 {success_count}/{len(data)} 條裁判書數據到SQLite數據庫")
        
        # 測試數據庫
        cursor.execute("SELECT COUNT(*) FROM court_cases")
        count = cursor.fetchone()[0]
        log_message(f"數據庫中共有 {count} 條裁判書記錄")
        
        conn.close()
        return True
    except Exception as e:
        log_message(f"導入數據到SQLite數據庫失敗: {str(e)}")
        return False

# 主函數
def main():
    log_message("開始處理裁判書數據並存儲到本地數據庫")
    
    # 檢查是否有原始數據
    if not os.path.exists(DATA_DIR):
        log_message(f"原始數據目錄不存在: {DATA_DIR}")
        return
    
    # 獲取所有JSON文件
    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    if not json_files:
        log_message("沒有找到JSON格式的裁判書數據")
        return
    
    log_message(f"找到 {len(json_files)} 個JSON文件")
    
    # 處理每個JSON文件
    all_processed_cases = []
    for json_file in json_files:
        file_path = os.path.join(DATA_DIR, json_file)
        log_message(f"處理文件: {json_file}")
        
        # 讀取JSON數據（處理BOM）
        raw_data = read_json_with_bom(file_path)
        if not raw_data:
            continue
        
        # 處理數據
        processed_cases = process_court_case_data(raw_data, json_file)
        if processed_cases:
            all_processed_cases.extend(processed_cases)
            
            # 保存處理後的數據
            output_filename = f"processed_{json_file}"
            save_processed_data(processed_cases, output_filename)
    
    # 保存所有處理後的數據到一個合併文件
    if all_processed_cases:
        log_message(f"總共處理了 {len(all_processed_cases)} 條裁判書數據")
        save_processed_data(all_processed_cases, "all_processed_cases.json")
        
        # 導入數據到SQLite
        import_to_sqlite(all_processed_cases)
    else:
        log_message("沒有處理到任何裁判書數據")
    
    log_message("裁判書數據處理和存儲完成")

if __name__ == "__main__":
    main()
