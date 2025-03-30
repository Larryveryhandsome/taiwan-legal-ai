#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
from datetime import datetime

# 設定基本參數
DATA_DIR = "/home/ubuntu/legal-ai-system/data/raw/laws"
LOG_FILE = "/home/ubuntu/legal-ai-system/data/raw/laws/download_log.txt"

# 確保目錄存在
os.makedirs(DATA_DIR, exist_ok=True)

# 記錄函數
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

# 從政府資料開放平臺搜索法規資料集
def search_law_datasets(keyword="法規", page=1, per_page=100):
    url = "https://data.gov.tw/api/v2/rest/dataset"
    params = {
        "q": keyword,
        "page": page,
        "per_page": per_page,
        "sort": "downloadcount",
        "order": "desc"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_message(f"搜索法規資料集失敗: {str(e)}")
        return {"success": False, "result": []}

# 下載資料集的資源
def download_dataset_resource(resource_url, output_path):
    try:
        response = requests.get(resource_url)
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        log_message(f"下載資源失敗 {resource_url}: {str(e)}")
        return False

# 從法規URL獲取法規內容
def get_law_content(law_url):
    try:
        response = requests.get(law_url)
        response.raise_for_status()
        return response.text
    except Exception as e:
        log_message(f"獲取法規內容失敗 {law_url}: {str(e)}")
        return None

# 保存法規內容到文件
def save_law_content(content, filename):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        log_message(f"保存法規內容失敗 {filename}: {str(e)}")
        return False

# 處理JSON格式的法規資料
def process_json_law_data(json_file_path):
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 處理不同格式的JSON數據
        if isinstance(data, list):
            for item in data:
                if "資料連結" in item and "資料名稱" in item:
                    law_name = item["資料名稱"]
                    law_url = item["資料連結"]
                    
                    # 創建安全的文件名
                    safe_name = "".join([c if c.isalnum() or c in "._- " else "_" for c in law_name])
                    output_path = os.path.join(DATA_DIR, f"{safe_name}.html")
                    
                    log_message(f"正在下載法規: {law_name}")
                    content = get_law_content(law_url)
                    if content:
                        save_law_content(content, output_path)
                        log_message(f"成功保存法規: {law_name}")
                    
                    # 避免請求過於頻繁
                    time.sleep(1)
        
        return True
    except Exception as e:
        log_message(f"處理JSON法規數據失敗 {json_file_path}: {str(e)}")
        return False

# 主函數
def main():
    log_message("開始實施替代法律數據收集策略")
    
    # 搜索法規相關資料集
    log_message("搜索法規相關資料集")
    datasets = search_law_datasets()
    
    if not datasets.get("success", False):
        log_message("搜索法規資料集失敗，嘗試直接下載已知資料集")
        # 已知的法規資料集URL列表
        known_datasets = [
            {
                "name": "跨國移交受刑人法施行細則",
                "url": "https://www.moj.gov.tw/media/23067/%e4%be%8b%e7%a8%bf.json?mediaDL=true",
                "format": "json"
            },
            {
                "name": "全國法規資料庫歷年收錄法規統計",
                "url": "https://data.moj.gov.tw/MojData/api/v1/LawStatistics",
                "format": "json"
            }
        ]
        
        for dataset in known_datasets:
            name = dataset["name"]
            url = dataset["url"]
            format = dataset["format"]
            
            log_message(f"下載資料集: {name}")
            output_path = os.path.join(DATA_DIR, f"{name}.{format}")
            
            if download_dataset_resource(url, output_path):
                log_message(f"成功下載資料集: {name}")
                
                if format.lower() == "json":
                    log_message(f"處理JSON資料集: {name}")
                    process_json_law_data(output_path)
            
            # 避免請求過於頻繁
            time.sleep(2)
    else:
        # 處理搜索結果
        results = datasets.get("result", [])
        log_message(f"找到 {len(results)} 個法規相關資料集")
        
        for idx, dataset in enumerate(results[:10]):  # 只處理前10個資料集
            dataset_id = dataset.get("id")
            dataset_name = dataset.get("title")
            
            log_message(f"處理資料集 ({idx+1}/10): {dataset_name}")
            
            # 獲取資料集資源
            resources = dataset.get("resources", [])
            for resource in resources:
                resource_format = resource.get("format", "").lower()
                resource_url = resource.get("resourceDownloadUrl")
                resource_name = resource.get("resourceName")
                
                if resource_format in ["json", "xml", "csv"] and resource_url:
                    log_message(f"下載資源: {resource_name} ({resource_format})")
                    
                    # 創建安全的文件名
                    safe_name = "".join([c if c.isalnum() or c in "._- " else "_" for c in resource_name])
                    output_path = os.path.join(DATA_DIR, f"{safe_name}.{resource_format}")
                    
                    if download_dataset_resource(resource_url, output_path):
                        log_message(f"成功下載資源: {resource_name}")
                        
                        if resource_format == "json":
                            log_message(f"處理JSON資源: {resource_name}")
                            process_json_law_data(output_path)
                    
                    # 避免請求過於頻繁
                    time.sleep(2)
    
    log_message("法規數據收集完成")

if __name__ == "__main__":
    main()
