#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import codecs
from datetime import datetime

# 設定基本參數
DATA_DIR = "/home/ubuntu/legal-ai-system/data/raw/laws"
PROCESSED_DIR = "/home/ubuntu/legal-ai-system/data/processed/laws"
LOG_FILE = "/home/ubuntu/legal-ai-system/data/processed/process_log.txt"

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

# 清理和結構化法規數據
def process_law_data(raw_data):
    processed_laws = []
    
    # 處理不同格式的法規數據
    if isinstance(raw_data, list):
        for item in raw_data:
            processed_law = {}
            
            # 跨國移交受刑人法施行細則格式
            if "資料名稱" in item and "資料連結" in item:
                processed_law = {
                    "title": item.get("資料名稱", ""),
                    "url": item.get("資料連結", ""),
                    "date": item.get("資料日期", ""),
                    "content": "",  # 暫無內容
                    "source": "政府資料開放平臺",
                    "category": "跨國法規",
                    "processed_date": datetime.now().isoformat()
                }
            
            # 其他可能的格式...
            
            if processed_law:
                processed_laws.append(processed_law)
    
    return processed_laws

# 保存處理後的數據到JSON文件
def save_processed_data(data, filename):
    try:
        output_path = os.path.join(PROCESSED_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log_message(f"保存處理後數據失敗 {filename}: {str(e)}")
        return False

# 主函數
def main():
    log_message("開始處理法規數據")
    
    # 檢查是否有原始數據
    if not os.path.exists(DATA_DIR):
        log_message(f"原始數據目錄不存在: {DATA_DIR}")
        return
    
    # 獲取所有JSON文件
    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    if not json_files:
        log_message("沒有找到JSON格式的法規數據")
        return
    
    log_message(f"找到 {len(json_files)} 個JSON文件")
    
    # 處理每個JSON文件
    all_processed_laws = []
    for json_file in json_files:
        file_path = os.path.join(DATA_DIR, json_file)
        log_message(f"處理文件: {json_file}")
        
        # 讀取JSON數據（處理BOM）
        raw_data = read_json_with_bom(file_path)
        if not raw_data:
            continue
        
        # 處理數據
        processed_laws = process_law_data(raw_data)
        if processed_laws:
            log_message(f"從 {json_file} 中處理了 {len(processed_laws)} 條法規數據")
            all_processed_laws.extend(processed_laws)
            
            # 保存處理後的數據
            output_filename = f"processed_{json_file}"
            save_processed_data(processed_laws, output_filename)
    
    # 保存所有處理後的數據到一個合併文件
    if all_processed_laws:
        log_message(f"總共處理了 {len(all_processed_laws)} 條法規數據")
        save_processed_data(all_processed_laws, "all_processed_laws.json")
    
    log_message("法規數據處理完成")

if __name__ == "__main__":
    main()
