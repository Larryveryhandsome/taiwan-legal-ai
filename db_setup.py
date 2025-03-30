#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import sqlite3
from datetime import datetime

# 設定基本參數
PROCESSED_DIR = "/home/ubuntu/legal-ai-system/data/processed/laws"
DB_DIR = "/home/ubuntu/legal-ai-system/data/db"
DB_FILE = os.path.join(DB_DIR, "legal_db.sqlite")
LOG_FILE = "/home/ubuntu/legal-ai-system/data/db/db_setup_log.txt"

# 確保目錄存在
os.makedirs(DB_DIR, exist_ok=True)

# 記錄函數
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

# 創建數據庫和表
def setup_database():
    try:
        # 連接到SQLite數據庫（如果不存在則創建）
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 創建法規表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS laws (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT,
            date TEXT,
            content TEXT,
            source TEXT,
            category TEXT,
            processed_date TEXT,
            UNIQUE(url)
        )
        ''')
        
        # 創建全文搜索索引
        cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS laws_fts USING fts5(
            title, content, source, category,
            content='laws',
            content_rowid='id'
        )
        ''')
        
        # 創建觸發器以保持FTS索引同步
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS laws_ai AFTER INSERT ON laws BEGIN
            INSERT INTO laws_fts(rowid, title, content, source, category)
            VALUES (new.id, new.title, new.content, new.source, new.category);
        END
        ''')
        
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS laws_ad AFTER DELETE ON laws BEGIN
            INSERT INTO laws_fts(laws_fts, rowid, title, content, source, category)
            VALUES ('delete', old.id, old.title, old.content, old.source, old.category);
        END
        ''')
        
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS laws_au AFTER UPDATE ON laws BEGIN
            INSERT INTO laws_fts(laws_fts, rowid, title, content, source, category)
            VALUES ('delete', old.id, old.title, old.content, old.source, old.category);
            INSERT INTO laws_fts(rowid, title, content, source, category)
            VALUES (new.id, new.title, new.content, new.source, new.category);
        END
        ''')
        
        conn.commit()
        log_message("成功創建數據庫和表")
        return conn
    except Exception as e:
        log_message(f"設置數據庫失敗: {str(e)}")
        return None

# 從JSON文件加載處理後的數據
def load_processed_data():
    all_laws = []
    
    try:
        # 檢查是否有合併的數據文件
        all_laws_file = os.path.join(PROCESSED_DIR, "all_processed_laws.json")
        if os.path.exists(all_laws_file):
            with open(all_laws_file, "r", encoding="utf-8") as f:
                all_laws = json.load(f)
                log_message(f"從合併文件加載了 {len(all_laws)} 條法規數據")
                return all_laws
        
        # 如果沒有合併文件，則從各個處理文件中加載
        processed_files = [f for f in os.listdir(PROCESSED_DIR) if f.startswith("processed_") and f.endswith(".json")]
        for file in processed_files:
            file_path = os.path.join(PROCESSED_DIR, file)
            with open(file_path, "r", encoding="utf-8") as f:
                laws = json.load(f)
                if isinstance(laws, list):
                    all_laws.extend(laws)
                    log_message(f"從 {file} 加載了 {len(laws)} 條法規數據")
        
        return all_laws
    except Exception as e:
        log_message(f"加載處理後的數據失敗: {str(e)}")
        return []

# 將數據導入SQLite數據庫
def import_to_sqlite(conn, laws):
    if not conn or not laws:
        return False
    
    try:
        cursor = conn.cursor()
        success_count = 0
        
        for law in laws:
            # 準備數據
            title = law.get("title", "")
            url = law.get("url", "")
            date = law.get("date", "")
            content = law.get("content", "")
            source = law.get("source", "")
            category = law.get("category", "")
            processed_date = law.get("processed_date", datetime.now().isoformat())
            
            # 插入數據（如果URL已存在則忽略）
            cursor.execute('''
            INSERT OR IGNORE INTO laws (title, url, date, content, source, category, processed_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, url, date, content, source, category, processed_date))
            
            if cursor.rowcount > 0:
                success_count += 1
        
        conn.commit()
        log_message(f"成功導入 {success_count}/{len(laws)} 條法規數據到SQLite數據庫")
        return True
    except Exception as e:
        log_message(f"導入數據到SQLite數據庫失敗: {str(e)}")
        return False

# 測試數據庫查詢
def test_database(conn):
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # 測試基本查詢
        cursor.execute("SELECT COUNT(*) FROM laws")
        count = cursor.fetchone()[0]
        log_message(f"數據庫中共有 {count} 條法規記錄")
        
        # 測試全文搜索
        if count > 0:
            cursor.execute("SELECT id, title FROM laws LIMIT 5")
            sample_laws = cursor.fetchall()
            log_message("數據庫中的部分法規:")
            for law_id, title in sample_laws:
                log_message(f"  ID: {law_id}, 標題: {title}")
            
            # 測試FTS搜索
            search_term = "法規"
            cursor.execute('''
            SELECT laws.id, laws.title, snippet(laws_fts, 0, '<b>', '</b>', '...', 10) as snippet
            FROM laws_fts
            JOIN laws ON laws.id = laws_fts.rowid
            WHERE laws_fts MATCH ?
            LIMIT 3
            ''', (search_term,))
            
            search_results = cursor.fetchall()
            if search_results:
                log_message(f"搜索 '{search_term}' 的結果:")
                for law_id, title, snippet in search_results:
                    log_message(f"  ID: {law_id}, 標題: {title}, 摘要: {snippet}")
            else:
                log_message(f"搜索 '{search_term}' 沒有找到結果")
    except Exception as e:
        log_message(f"測試數據庫查詢失敗: {str(e)}")

# 主函數
def main():
    log_message("開始設置本地數據庫存儲法規數據")
    
    # 設置數據庫
    conn = setup_database()
    if not conn:
        log_message("無法設置數據庫，程序終止")
        return
    
    # 加載處理後的數據
    laws = load_processed_data()
    if not laws:
        log_message("沒有找到處理後的法規數據，程序終止")
        conn.close()
        return
    
    # 導入數據到SQLite
    import_to_sqlite(conn, laws)
    
    # 測試數據庫
    test_database(conn)
    
    # 關閉連接
    conn.close()
    log_message("本地數據庫設置完成")

if __name__ == "__main__":
    main()
