#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
from datetime import datetime

# 設定基本參數
BASE_URL = "https://law.moj.gov.tw/api"
LAWS_DIR = "/home/ubuntu/legal-ai-system/data/raw/laws"
LOG_FILE = "/home/ubuntu/legal-ai-system/data/raw/laws/download_log.txt"

# 確保目錄存在
os.makedirs(LAWS_DIR, exist_ok=True)

# 記錄函數
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

# 獲取法規類別列表
def get_law_categories():
    url = f"{BASE_URL}/Law/LawClassList"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_message(f"獲取法規類別失敗: {str(e)}")
        return []

# 獲取特定類別下的法規列表
def get_laws_by_category(category_id):
    url = f"{BASE_URL}/Law/LawList"
    params = {"LawClassId": category_id}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_message(f"獲取類別 {category_id} 的法規列表失敗: {str(e)}")
        return []

# 獲取特定法規的詳細內容
def get_law_detail(pcode):
    url = f"{BASE_URL}/Law/LawAll"
    params = {"PCode": pcode}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_message(f"獲取法規 {pcode} 的詳細內容失敗: {str(e)}")
        return None

# 保存法規內容到文件
def save_law(law_data, pcode):
    if not law_data:
        return False
    
    filename = os.path.join(LAWS_DIR, f"{pcode}.json")
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(law_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log_message(f"保存法規 {pcode} 失敗: {str(e)}")
        return False

# 主函數
def main():
    log_message("開始從台灣全國法規資料庫收集法律條文")
    
    # 獲取所有法規類別
    categories = get_law_categories()
    if not categories:
        log_message("無法獲取法規類別，程序終止")
        return
    
    log_message(f"成功獲取 {len(categories)} 個法規類別")
    
    # 遍歷每個類別
    total_laws = 0
    successful_downloads = 0
    
    for category in categories:
        category_id = category.get("LawClassId")
        category_name = category.get("LawClassName", "未知類別")
        
        log_message(f"處理類別: {category_name} (ID: {category_id})")
        
        # 獲取該類別下的所有法規
        laws = get_laws_by_category(category_id)
        if not laws:
            log_message(f"類別 {category_name} 下沒有法規或獲取失敗，跳過")
            continue
        
        log_message(f"類別 {category_name} 下有 {len(laws)} 個法規")
        total_laws += len(laws)
        
        # 遍歷每個法規
        for i, law in enumerate(laws):
            pcode = law.get("PCode")
            law_name = law.get("LawName", "未知法規")
            
            # 檢查是否已下載
            if os.path.exists(os.path.join(LAWS_DIR, f"{pcode}.json")):
                log_message(f"法規 {law_name} (PCode: {pcode}) 已存在，跳過")
                successful_downloads += 1
                continue
            
            log_message(f"下載法規 ({i+1}/{len(laws)}): {law_name} (PCode: {pcode})")
            
            # 獲取法規詳細內容
            law_detail = get_law_detail(pcode)
            if not law_detail:
                log_message(f"獲取法規 {law_name} 詳細內容失敗，跳過")
                continue
            
            # 保存法規
            if save_law(law_detail, pcode):
                log_message(f"成功保存法規: {law_name}")
                successful_downloads += 1
            else:
                log_message(f"保存法規 {law_name} 失敗")
            
            # 避免請求過於頻繁
            time.sleep(1)
    
    log_message(f"法規收集完成。總共處理 {total_laws} 個法規，成功下載 {successful_downloads} 個")

if __name__ == "__main__":
    main()
