#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import jieba
import jieba.analyse
import re
from collections import Counter
from datetime import datetime

# 設定基本參數
AI_DIR = "/home/ubuntu/legal-ai-system/backend/ai"
LOG_FILE = os.path.join(AI_DIR, "keyword_extractor_log.txt")

# 確保目錄存在
os.makedirs(AI_DIR, exist_ok=True)

# 記錄函數
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

# 載入法律關鍵詞字典
def load_legal_keywords_dict():
    try:
        dict_path = os.path.join(AI_DIR, "legal_keywords_dict.json")
        with open(dict_path, "r", encoding="utf-8") as f:
            keywords_dict = json.load(f)
        log_message(f"成功載入法律關鍵詞字典，共 {len(keywords_dict)} 個關鍵詞")
        return keywords_dict
    except Exception as e:
        log_message(f"載入法律關鍵詞字典失敗: {str(e)}")
        return {}

# 載入法律問題分類器
def load_legal_question_classifier():
    try:
        classifier_path = os.path.join(AI_DIR, "legal_question_classifier.json")
        with open(classifier_path, "r", encoding="utf-8") as f:
            classifier = json.load(f)
        log_message(f"成功載入法律問題分類器，共 {len(classifier)} 個類別")
        return classifier
    except Exception as e:
        log_message(f"載入法律問題分類器失敗: {str(e)}")
        return {}

# 將法律關鍵詞添加到jieba詞典
def add_legal_keywords_to_jieba(keywords_dict):
    try:
        # 將法律關鍵詞添加到jieba詞典
        for keyword in keywords_dict.keys():
            if len(keyword) > 1:  # 只添加長度大於1的詞
                jieba.add_word(keyword, freq=10000)  # 設置高頻率，確保能被識別
        
        log_message(f"成功將 {len(keywords_dict)} 個法律關鍵詞添加到jieba詞典")
        return True
    except Exception as e:
        log_message(f"將法律關鍵詞添加到jieba詞典失敗: {str(e)}")
        return False

# 使用jieba進行中文分詞
def tokenize_text(text):
    if not text:
        return []
    # 移除標點符號和特殊字符
    text = re.sub(r'[^\w\s]', '', text)
    # 使用jieba進行分詞
    words = jieba.cut(text)
    # 過濾停用詞和空字符
    stopwords = {'的', '了', '和', '是', '在', '有', '與', '之', '或', '及', '對', '由', '上', '中', '下', '為', '以', '等'}
    return [word for word in words if word and word not in stopwords]

# 使用TF-IDF提取關鍵詞
def extract_keywords_tfidf(text, topK=10):
    try:
        # 使用jieba的TF-IDF算法提取關鍵詞
        keywords = jieba.analyse.extract_tags(text, topK=topK, withWeight=True)
        log_message(f"使用TF-IDF成功提取 {len(keywords)} 個關鍵詞")
        return keywords
    except Exception as e:
        log_message(f"使用TF-IDF提取關鍵詞失敗: {str(e)}")
        return []

# 使用TextRank提取關鍵詞
def extract_keywords_textrank(text, topK=10):
    try:
        # 使用jieba的TextRank算法提取關鍵詞
        keywords = jieba.analyse.textrank(text, topK=topK, withWeight=True)
        log_message(f"使用TextRank成功提取 {len(keywords)} 個關鍵詞")
        return keywords
    except Exception as e:
        log_message(f"使用TextRank提取關鍵詞失敗: {str(e)}")
        return []

# 提取法律相關關鍵詞
def extract_legal_keywords(text, keywords_dict, topK=10):
    try:
        # 分詞
        tokens = tokenize_text(text)
        
        # 找出文本中包含的法律關鍵詞
        legal_keywords = []
        for token in tokens:
            if token in keywords_dict:
                legal_keywords.append((token, keywords_dict[token]))
        
        # 按出現頻率排序
        counter = Counter(tokens)
        legal_keywords_with_freq = [(keyword, info, counter[keyword]) for keyword, info in legal_keywords]
        legal_keywords_with_freq.sort(key=lambda x: x[2], reverse=True)
        
        # 取前topK個
        top_legal_keywords = legal_keywords_with_freq[:topK]
        
        log_message(f"成功提取 {len(top_legal_keywords)} 個法律相關關鍵詞")
        return top_legal_keywords
    except Exception as e:
        log_message(f"提取法律相關關鍵詞失敗: {str(e)}")
        return []

# 分類法律問題
def classify_legal_question(text, classifier):
    try:
        # 分詞
        tokens = tokenize_text(text)
        
        # 計算每個類別的匹配分數
        category_scores = {}
        for category, keywords in classifier.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            if score > 0:
                category_scores[category] = score
        
        # 按分數排序
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_categories:
            top_category = sorted_categories[0][0]
            log_message(f"問題分類結果: {top_category}, 分數: {sorted_categories[0][1]}")
            return top_category, sorted_categories
        else:
            log_message("無法分類問題")
            return None, []
    except Exception as e:
        log_message(f"分類法律問題失敗: {str(e)}")
        return None, []

# 提取問題中的實體和行為
def extract_entities_and_actions(text):
    try:
        # 使用正則表達式提取可能的實體和行為
        entities = []
        actions = []
        
        # 提取人物實體（假設人物後面跟著"某"或者是"我"、"他"、"她"等代詞）
        person_pattern = r'([張李王陳楊趙黃周吳劉蔡鄭許謝郭洪曾邱廖賴][\u4e00-\u9fa5]{0,1}某|我|他|她|你|妳|我們|他們|她們|你們|妳們)'
        person_matches = re.findall(person_pattern, text)
        if person_matches:
            entities.extend([("人物", match) for match in person_matches])
        
        # 提取地點實體（假設地點前面有"在"、"於"等介詞）
        location_pattern = r'(在|於)([^\，\。\！\？\；\：]{1,10})'
        location_matches = re.findall(location_pattern, text)
        if location_matches:
            entities.extend([("地點", match[1]) for match in location_matches])
        
        # 提取時間實體
        time_pattern = r'([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日|[0-9]{1,2}月[0-9]{1,2}日|[0-9]{1,2}日|[0-9]{1,2}時|[0-9]{1,2}分|昨天|今天|明天|前天|後天|早上|中午|下午|晚上)'
        time_matches = re.findall(time_pattern, text)
        if time_matches:
            entities.extend([("時間", match) for match in time_matches])
        
        # 提取行為（假設行為是動詞加上可能的賓語）
        action_pattern = r'(([^\，\。\！\？\；\：]{1,3})(了|過)([^\，\。\！\？\；\：]{1,10}))'
        action_matches = re.findall(action_pattern, text)
        if action_matches:
            actions.extend([match[0] for match in action_matches])
        
        log_message(f"成功提取 {len(entities)} 個實體和 {len(actions)} 個行為")
        return entities, actions
    except Exception as e:
        log_message(f"提取問題中的實體和行為失敗: {str(e)}")
        return [], []

# 綜合分析問題
def analyze_question(text):
    try:
        # 載入法律關鍵詞字典
        keywords_dict = load_legal_keywords_dict()
        
        # 載入法律問題分類器
        classifier = load_legal_question_classifier()
        
        # 將法律關鍵詞添加到jieba詞典
        add_legal_keywords_to_jieba(keywords_dict)
        
        # 使用TF-IDF提取關鍵詞
        tfidf_keywords = extract_keywords_tfidf(text)
        
        # 使用TextRank提取關鍵詞
        textrank_keywords = extract_keywords_textrank(text)
        
        # 提取法律相關關鍵詞
        legal_keywords = extract_legal_keywords(text, keywords_dict)
        
        # 分類法律問題
        category, category_scores = classify_legal_question(text, classifier)
        
        # 提取問題中的實體和行為
        entities, actions = extract_entities_and_actions(text)
        
        # 整合分析結果
        analysis_result = {
            "original_text": text,
            "tfidf_keywords": tfidf_keywords,
            "textrank_keywords": textrank_keywords,
            "legal_keywords": legal_keywords,
            "category": category,
            "category_scores": category_scores,
            "entities": entities,
            "actions": actions
        }
        
        log_message("問題分析完成")
        return analysis_result
    except Exception as e:
        log_message(f"綜合分析問題失敗: {str(e)}")
        return None

# 保存分析結果
def save_analysis_result(result, filename):
    try:
        output_path = os.path.join(AI_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        log_message(f"成功保存分析結果: {output_path}")
        return True
    except Exception as e:
        log_message(f"保存分析結果失敗: {str(e)}")
        return False

# 主函數
def main():
    log_message("開始開發關鍵詞提取系統")
    
    # 測試問題
    test_questions = [
        "我不小心撞到路人，要怎麼樣無罪?",
        "如果我的鄰居深夜製造噪音，我可以採取什麼法律行動?",
        "我的房東未經我同意就進入我的租屋處，這違法嗎?",
        "我的公司拖欠薪資三個月了，我該怎麼辦?",
        "如果我收到交通罰單但認為不合理，有什麼申訴管道?"
    ]
    
    # 分析每個測試問題
    for i, question in enumerate(test_questions):
        log_message(f"分析測試問題 {i+1}: {question}")
        result = analyze_question(question)
        if result:
            save_analysis_result(result, f"question_analysis_{i+1}.json")
    
    log_message("關鍵詞提取系統開發完成")

if __name__ == "__main__":
    main()
