#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import random
import re
from datetime import datetime

# 設定基本參數
AI_DIR = "/home/ubuntu/legal-ai-system/backend/ai"
LOG_FILE = os.path.join(AI_DIR, "response_generator_log.txt")

# 確保目錄存在
os.makedirs(AI_DIR, exist_ok=True)

# 記錄函數
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

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

# 載入關鍵詞提取系統
def load_keyword_extractor():
    try:
        import keyword_extractor
        log_message("成功載入關鍵詞提取系統")
        return keyword_extractor
    except Exception as e:
        log_message(f"載入關鍵詞提取系統失敗: {str(e)}")
        return None

# 載入法律搜索功能
def load_legal_search():
    try:
        import legal_search
        log_message("成功載入法律搜索功能")
        return legal_search
    except Exception as e:
        log_message(f"載入法律搜索功能失敗: {str(e)}")
        return None

# 提取法規內容的關鍵部分
def extract_key_content_from_law(law_content, max_length=200):
    try:
        # 如果內容較短，直接返回
        if len(law_content) <= max_length:
            return law_content
        
        # 嘗試找到最相關的段落
        paragraphs = re.split(r'\n+', law_content)
        
        # 如果只有一個段落，截取前max_length個字符
        if len(paragraphs) <= 1:
            return law_content[:max_length] + "..."
        
        # 選擇最長的段落（通常包含更多信息）
        longest_paragraph = max(paragraphs, key=len)
        if len(longest_paragraph) <= max_length:
            return longest_paragraph
        
        # 如果最長段落仍然太長，截取前max_length個字符
        return longest_paragraph[:max_length] + "..."
    except Exception as e:
        log_message(f"提取法規內容的關鍵部分失敗: {str(e)}")
        return law_content[:min(len(law_content), max_length)] + "..."

# 提取判例內容的關鍵部分
def extract_key_content_from_case(case_content, max_length=300):
    try:
        # 如果內容較短，直接返回
        if len(case_content) <= max_length:
            return case_content
        
        # 嘗試找到判決理由部分
        reason_match = re.search(r'理由[\s\n]*([\s\S]*?)(?=[\n\r]*[一二三四五六七八九十]、|\Z)', case_content)
        if reason_match:
            reason = reason_match.group(1).strip()
            if len(reason) <= max_length:
                return reason
            return reason[:max_length] + "..."
        
        # 如果找不到判決理由，嘗試找到主文部分
        main_match = re.search(r'主文[\s\n]*([\s\S]*?)(?=[\n\r]*[一二三四五六七八九十]、|\Z)', case_content)
        if main_match:
            main = main_match.group(1).strip()
            if len(main) <= max_length:
                return main
            return main[:max_length] + "..."
        
        # 如果都找不到，截取前max_length個字符
        return case_content[:max_length] + "..."
    except Exception as e:
        log_message(f"提取判例內容的關鍵部分失敗: {str(e)}")
        return case_content[:min(len(case_content), max_length)] + "..."

# 生成法律建議
def generate_legal_advice(question, search_result, templates):
    try:
        # 如果沒有找到相關法規和判例
        if not search_result["laws"] and not search_result["cases"]:
            # 使用無相關信息的模板
            if "no_relevant_info" in templates:
                return random.choice(templates["no_relevant_info"])
            return "抱歉，系統中沒有與您問題直接相關的法規或判例。建議您諮詢專業律師獲取更準確的法律建議。"
        
        # 準備回答內容
        response_parts = []
        
        # 添加法規引用
        if search_result["laws"]:
            law = search_result["laws"][0]  # 使用最相關的法規
            law_template = random.choice(templates.get("general_law_query", ["根據{law_name}，{law_content}"]))
            law_content = extract_key_content_from_law(law["content"])
            law_part = law_template.format(law_name=law["title"], law_content=law_content)
            response_parts.append(law_part)
        
        # 添加判例引用
        if search_result["cases"]:
            case = search_result["cases"][0]  # 使用最相關的判例
            case_template = random.choice(templates.get("case_reference", ["在類似案例中（{case_title}），法院判決指出：{case_content}"]))
            case_content = extract_key_content_from_case(case["content"])
            case_part = case_template.format(case_title=case["title"], case_content=case_content)
            response_parts.append(case_part)
        
        # 根據問題類型生成法律建議
        category = search_result.get("category")
        
        # 刑事案件的建議
        if category == "刑事":
            advice_template = random.choice(templates.get("legal_advice", ["針對您的情況，建議您：\n1. {advice_1}\n2. {advice_2}\n3. {advice_3}"]))
            advice_part = advice_template.format(
                advice_1="保持冷靜，不要自行與對方協商或承認責任",
                advice_2="尋求專業刑事律師的協助，詳細說明事件經過",
                advice_3="收集並保存所有相關證據，如監控錄像、證人證詞等"
            )
            response_parts.append(advice_part)
            
            strategy_template = random.choice(templates.get("court_strategy", ["在法庭上，您可以採取以下策略：\n1. {strategy_1}\n2. {strategy_2}\n3. {strategy_3}"]))
            strategy_part = strategy_template.format(
                strategy_1="強調行為的非故意性質，說明當時情況下的合理反應",
                strategy_2="提出對方可能存在的過失或誇大傷害的情況",
                strategy_3="如有前科，請律師強調您的改過自新和社會貢獻"
            )
            response_parts.append(strategy_part)
        
        # 民事案件的建議
        elif category == "民事" or category == "商業" or category == "勞工" or category == "家事":
            advice_template = random.choice(templates.get("legal_advice", ["針對您的情況，建議您：\n1. {advice_1}\n2. {advice_2}\n3. {advice_3}"]))
            advice_part = advice_template.format(
                advice_1="收集所有相關證據，如合約、通訊記錄、付款證明等",
                advice_2="嘗試與對方進行協商，尋求和解可能",
                advice_3="如協商不成，可向法院提起民事訴訟，或考慮調解程序"
            )
            response_parts.append(advice_part)
            
            strategy_template = random.choice(templates.get("court_strategy", ["在法庭上，您可以採取以下策略：\n1. {strategy_1}\n2. {strategy_2}\n3. {strategy_3}"]))
            strategy_part = strategy_template.format(
                strategy_1="清晰陳述事實，並提供充分證據支持您的主張",
                strategy_2="強調對方違反法律或合約的具體條款",
                strategy_3="準備好回應對方可能提出的抗辯，並有備用論點"
            )
            response_parts.append(strategy_part)
        
        # 行政案件的建議
        elif category == "行政":
            advice_template = random.choice(templates.get("legal_advice", ["針對您的情況，建議您：\n1. {advice_1}\n2. {advice_2}\n3. {advice_3}"]))
            advice_part = advice_template.format(
                advice_1="確認行政處分的法律依據，檢查是否有程序或實體上的瑕疵",
                advice_2="在法定期限內提出訴願，向上級機關表達您的異議",
                advice_3="如訴願結果不滿意，可向行政法院提起行政訴訟"
            )
            response_parts.append(advice_part)
            
            strategy_template = random.choice(templates.get("court_strategy", ["在法庭上，您可以採取以下策略：\n1. {strategy_1}\n2. {strategy_2}\n3. {strategy_3}"]))
            strategy_part = strategy_template.format(
                strategy_1="質疑行政機關的裁量是否逾越法律授權範圍",
                strategy_2="指出行政程序中可能存在的瑕疵或違法情形",
                strategy_3="引用類似案例的判決結果，支持您的主張"
            )
            response_parts.append(strategy_part)
        
        # 無法分類的情況
        else:
            advice_template = random.choice(templates.get("legal_advice", ["針對您的情況，建議您：\n1. {advice_1}\n2. {advice_2}\n3. {advice_3}"]))
            advice_part = advice_template.format(
                advice_1="收集並保存所有相關證據和文件",
                advice_2="尋求專業律師的法律諮詢，了解您的權利和可能的法律行動",
                advice_3="考慮透過協商、調解等非訴訟方式解決爭議，節省時間和費用"
            )
            response_parts.append(advice_part)
        
        # 組合回答
        response = "\n\n".join(response_parts)
        
        # 添加免責聲明
        disclaimer = "\n\n請注意：以上建議僅供參考，不構成法律意見。具體情況可能有所不同，建議您諮詢專業律師獲取針對您具體情況的法律建議。"
        response += disclaimer
        
        return response
    except Exception as e:
        log_message(f"生成法律建議失敗: {str(e)}")
        return "抱歉，系統在生成回答時遇到了問題。建議您諮詢專業律師獲取法律建議。"

# 根據問題和搜索結果生成回答
def generate_response(question, analysis_result, search_result, templates):
    try:
        # 生成法律建議
        response = generate_legal_advice(question, search_result, templates)
        
        # 構建完整回答
        full_response = {
            "question": question,
            "response": response,
            "analysis_result": analysis_result,
            "search_result": search_result,
            "generated_at": datetime.now().isoformat()
        }
        
        log_message("成功生成回答")
        return full_response
    except Exception as e:
        log_message(f"生成回答失敗: {str(e)}")
        return {
            "question": question,
            "response": "抱歉，系統在生成回答時遇到了問題。建議您諮詢專業律師獲取法律建議。",
            "error": str(e),
            "generated_at": datetime.now().isoformat()
        }

# 保存生成的回答
def save_response(response, filename):
    try:
        output_path = os.path.join(AI_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(response, f, ensure_ascii=False, indent=2)
        log_message(f"成功保存回答: {output_path}")
        return True
    except Exception as e:
        log_message(f"保存回答失敗: {str(e)}")
        return False

# 主函數
def main():
    log_message("開始開發模板回答系統")
    
    # 載入回答模板
    templates = load_response_templates()
    if not templates:
        log_message("無法載入回答模板，無法繼續")
        return
    
    # 載入關鍵詞提取系統
    keyword_extractor = load_keyword_extractor()
    if not keyword_extractor:
        log_message("無法載入關鍵詞提取系統，無法繼續")
        return
    
    # 載入法律搜索功能
    legal_search = load_legal_search()
    if not legal_search:
        log_message("無法載入法律搜索功能，無法繼續")
        return
    
    # 測試問題
    test_questions = [
        "我不小心撞到路人，要怎麼樣無罪?",
        "如果我的鄰居深夜製造噪音，我可以採取什麼法律行動?",
        "我的房東未經我同意就進入我的租屋處，這違法嗎?",
        "我的公司拖欠薪資三個月了，我該怎麼辦?",
        "如果我收到交通罰單但認為不合理，有什麼申訴管道?"
    ]
    
    # 對每個測試問題生成回答
    for i, question in enumerate(test_questions):
        log_message(f"處理測試問題 {i+1}: {question}")
        
        # 分析問題
        analysis_result = keyword_extractor.analyze_question(question)
        
        # 搜索相關法規和判例
        search_result = legal_search.search_by_question_analysis(analysis_result)
        
        # 生成回答
        response = generate_response(question, analysis_result, search_result, templates)
        
        # 保存回答
        save_response(response, f"response_{i+1}.json")
    
    log_message("模板回答系統開發完成")

if __name__ == "__main__":
    main()
