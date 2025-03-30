#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
from datetime import datetime

# 設定基本參數
DATA_DIR = "/home/ubuntu/legal-ai-system/data/raw/cases"
LOG_FILE = "/home/ubuntu/legal-ai-system/data/raw/cases/download_log.txt"

# 確保目錄存在
os.makedirs(DATA_DIR, exist_ok=True)

# 記錄函數
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

# 從司法院資料開放平台獲取裁判書列表
def get_court_cases_list(page=1, per_page=10):
    url = "https://opendata.judicial.gov.tw/api/v1/datasets"
    params = {
        "categoryTheme4Sys": "051",  # 裁判書類別
        "page": page,
        "size": per_page,
        "sort": "publishedDate,desc"
    }
    
    try:
        log_message(f"正在獲取裁判書列表 (頁碼: {page}, 每頁數量: {per_page})")
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_message(f"獲取裁判書列表失敗: {str(e)}")
        return {"success": False, "result": []}

# 從司法院資料開放平台獲取裁判書詳情
def get_court_case_detail(case_id):
    url = f"https://opendata.judicial.gov.tw/api/v1/datasets/{case_id}"
    
    try:
        log_message(f"正在獲取裁判書詳情 (ID: {case_id})")
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_message(f"獲取裁判書詳情失敗 (ID: {case_id}): {str(e)}")
        return None

# 從司法院資料開放平台下載裁判書資源
def download_court_case_resource(resource_url, output_path):
    try:
        log_message(f"正在下載裁判書資源: {resource_url}")
        response = requests.get(resource_url)
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        log_message(f"成功下載裁判書資源: {output_path}")
        return True
    except Exception as e:
        log_message(f"下載裁判書資源失敗: {str(e)}")
        return False

# 使用司法院裁判書開放API獲取裁判書
def get_court_case_by_api(jid=None, date_from=None, date_to=None):
    # 獲取裁判書異動清單
    if date_from and date_to:
        url = "https://data.judicial.gov.tw/jdg/api/JDG_M0001"
        params = {
            "date_from": date_from,  # 格式: YYYYMMDD
            "date_to": date_to       # 格式: YYYYMMDD
        }
        
        try:
            log_message(f"正在獲取裁判書異動清單 (日期範圍: {date_from} - {date_to})")
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log_message(f"獲取裁判書異動清單失敗: {str(e)}")
            return []
    
    # 獲取特定裁判書內容
    elif jid:
        url = "https://data.judicial.gov.tw/jdg/api/JDG_M0002"
        params = {
            "jid": jid
        }
        
        try:
            log_message(f"正在獲取裁判書內容 (JID: {jid})")
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log_message(f"獲取裁判書內容失敗 (JID: {jid}): {str(e)}")
            return None
    
    else:
        log_message("獲取裁判書API參數錯誤: 需要提供jid或date_from和date_to")
        return None

# 保存裁判書數據到JSON文件
def save_court_case_data(data, filename):
    try:
        output_path = os.path.join(DATA_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        log_message(f"成功保存裁判書數據: {output_path}")
        return True
    except Exception as e:
        log_message(f"保存裁判書數據失敗: {str(e)}")
        return False

# 主函數
def main():
    log_message("開始實施判例數據收集策略")
    
    # 方法1: 從司法院資料開放平台獲取裁判書列表
    try:
        log_message("嘗試從司法院資料開放平台獲取裁判書列表")
        cases_list = get_court_cases_list(page=1, per_page=5)
        
        if cases_list and "data" in cases_list and len(cases_list["data"]) > 0:
            log_message(f"成功獲取 {len(cases_list['data'])} 條裁判書列表數據")
            
            # 保存裁判書列表
            save_court_case_data(cases_list, "court_cases_list.json")
            
            # 獲取並保存每個裁判書的詳情
            for idx, case in enumerate(cases_list["data"]):
                case_id = case.get("id")
                if case_id:
                    case_detail = get_court_case_detail(case_id)
                    if case_detail:
                        save_court_case_data(case_detail, f"court_case_detail_{case_id}.json")
                    
                    # 避免請求過於頻繁
                    time.sleep(2)
        else:
            log_message("從司法院資料開放平台獲取裁判書列表失敗或列表為空")
    except Exception as e:
        log_message(f"從司法院資料開放平台獲取裁判書時發生錯誤: {str(e)}")
    
    # 方法2: 使用司法院裁判書開放API
    try:
        log_message("嘗試使用司法院裁判書開放API獲取裁判書")
        
        # 獲取最近7天的裁判書異動清單
        today = datetime.now().strftime("%Y%m%d")
        seven_days_ago = (datetime.now() - datetime.timedelta(days=7)).strftime("%Y%m%d")
        
        cases_changes = get_court_case_by_api(date_from=seven_days_ago, date_to=today)
        
        if cases_changes and len(cases_changes) > 0:
            log_message(f"成功獲取 {len(cases_changes)} 條裁判書異動清單")
            
            # 保存裁判書異動清單
            save_court_case_data(cases_changes, "court_cases_changes.json")
            
            # 獲取並保存每個裁判書的內容
            for idx, case in enumerate(cases_changes[:5]):  # 只處理前5個
                jid = case.get("JID")
                if jid:
                    case_content = get_court_case_by_api(jid=jid)
                    if case_content:
                        save_court_case_data(case_content, f"court_case_content_{jid}.json")
                    
                    # 避免請求過於頻繁
                    time.sleep(2)
        else:
            log_message("使用司法院裁判書開放API獲取裁判書異動清單失敗或清單為空")
    except Exception as e:
        log_message(f"使用司法院裁判書開放API獲取裁判書時發生錯誤: {str(e)}")
    
    # 方法3: 直接下載已知的裁判書資源
    try:
        log_message("嘗試直接下載已知的裁判書資源")
        
        # 已知的裁判書資源URL列表
        known_resources = [
            {
                "name": "199601裁判書",
                "url": "https://opendata.judicial.gov.tw/api/v1/datasets/199601/resources/downloadFile",
                "format": "json"
            },
            {
                "name": "199602裁判書",
                "url": "https://opendata.judicial.gov.tw/api/v1/datasets/199602/resources/downloadFile",
                "format": "json"
            }
        ]
        
        for resource in known_resources:
            name = resource["name"]
            url = resource["url"]
            format = resource["format"]
            
            output_path = os.path.join(DATA_DIR, f"{name}.{format}")
            download_court_case_resource(url, output_path)
            
            # 避免請求過於頻繁
            time.sleep(2)
    except Exception as e:
        log_message(f"直接下載已知的裁判書資源時發生錯誤: {str(e)}")
    
    log_message("判例數據收集完成")

if __name__ == "__main__":
    main()
