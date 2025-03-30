#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import sqlite3
import jieba
import re
import math
from collections import Counter
from datetime import datetime

# 設定基本參數
DB_DIR = "/home/ubuntu/legal-ai-system/data/db"
DB_FILE = os.path.join(DB_DIR, "legal_db.sqlite")
AI_DIR = "/home/ubuntu/legal-ai-system/backend/ai"
LOG_FILE = os.path.join(AI_DIR, "ai_setup_log.txt")

# 確保目錄存在
os.makedirs(AI_DIR, exist_ok=True)

# 記錄函數
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

# 從數據庫加載法規和判例數據
def load_data_from_db():
    try:
        # 連接到SQLite數據庫
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 加載法規數據
        cursor.execute('''
        SELECT id, title, content, category FROM laws
        ''')
        laws = cursor.fetchall()
        
        # 加載判例數據
        cursor.execute('''
        SELECT id, title, content, case_type FROM court_cases
        ''')
        cases = cursor.fetchall()
        
        conn.close()
        
        log_message(f"從數據庫加載了 {len(laws)} 條法規和 {len(cases)} 條判例")
        return laws, cases
    except Exception as e:
        log_message(f"從數據庫加載數據失敗: {str(e)}")
        return [], []

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

# 建立TF-IDF索引
def build_tfidf_index(documents):
    # 文檔分詞
    tokenized_docs = [tokenize_text(doc[2]) for doc in documents]  # doc[2]是content
    
    # 計算詞頻 (TF)
    tf = []
    for doc_tokens in tokenized_docs:
        counter = Counter(doc_tokens)
        total_words = len(doc_tokens)
        tf.append({word: count/total_words for word, count in counter.items()})
    
    # 計算逆文檔頻率 (IDF)
    num_docs = len(documents)
    idf = {}
    for doc_tokens in tokenized_docs:
        for word in set(doc_tokens):
            idf[word] = idf.get(word, 0) + 1
    
    idf = {word: math.log(num_docs / (freq + 1)) + 1 for word, freq in idf.items()}
    
    # 計算TF-IDF
    tfidf_docs = []
    for i, doc_tf in enumerate(tf):
        tfidf = {word: tf_val * idf.get(word, 0) for word, tf_val in doc_tf.items()}
        tfidf_docs.append({
            'id': documents[i][0],
            'title': documents[i][1],
            'content': documents[i][2],
            'category': documents[i][3],
            'tokens': tokenized_docs[i],
            'tfidf': tfidf
        })
    
    return tfidf_docs, idf

# 保存TF-IDF索引到文件
def save_tfidf_index(tfidf_docs, idf, filename):
    try:
        output_path = os.path.join(AI_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                'documents': tfidf_docs,
                'idf': idf
            }, f, ensure_ascii=False)
        log_message(f"成功保存TF-IDF索引: {output_path}")
        return True
    except Exception as e:
        log_message(f"保存TF-IDF索引失敗: {str(e)}")
        return False

# 建立法律關鍵詞字典
def build_legal_keywords_dict(laws, cases):
    keywords = {}
    
    # 從法規中提取關鍵詞
    for law in laws:
        law_id, title, content, category = law
        # 提取標題中的關鍵詞
        title_tokens = tokenize_text(title)
        for token in title_tokens:
            if len(token) > 1:  # 只考慮長度大於1的詞
                if token not in keywords:
                    keywords[token] = {'type': 'law', 'categories': set(), 'ids': set()}
                keywords[token]['categories'].add(category)
                keywords[token]['ids'].add(law_id)
    
    # 從判例中提取關鍵詞
    for case in cases:
        case_id, title, content, case_type = case
        # 提取標題中的關鍵詞
        title_tokens = tokenize_text(title)
        for token in title_tokens:
            if len(token) > 1:  # 只考慮長度大於1的詞
                if token not in keywords:
                    keywords[token] = {'type': 'case', 'categories': set(), 'ids': set()}
                elif keywords[token]['type'] == 'law':
                    keywords[token]['type'] = 'both'
                keywords[token]['categories'].add(case_type)
                keywords[token]['ids'].add(case_id)
    
    # 將set轉換為list以便JSON序列化
    for token in keywords:
        keywords[token]['categories'] = list(keywords[token]['categories'])
        keywords[token]['ids'] = list(keywords[token]['ids'])
    
    return keywords

# 保存法律關鍵詞字典到文件
def save_legal_keywords_dict(keywords, filename):
    try:
        output_path = os.path.join(AI_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(keywords, f, ensure_ascii=False)
        log_message(f"成功保存法律關鍵詞字典: {output_path}")
        return True
    except Exception as e:
        log_message(f"保存法律關鍵詞字典失敗: {str(e)}")
        return False

# 建立回答模板
def build_response_templates():
    templates = {
        "general_law_query": [
            "根據{law_name}，{law_content}",
            "依照{law_name}的規定，{law_content}",
            "參考{law_name}，相關法律規定為：{law_content}"
        ],
        "case_reference": [
            "在類似案例中（{case_title}），法院判決指出：{case_content}",
            "參考{case_title}的判例，{case_content}",
            "根據{case_title}的先例，法院認為：{case_content}"
        ],
        "legal_advice": [
            "針對您的情況，建議您：\n1. {advice_1}\n2. {advice_2}\n3. {advice_3}",
            "從法律角度考慮，您可以：\n- {advice_1}\n- {advice_2}\n- {advice_3}",
            "基於相關法規和判例，您應該：\n1) {advice_1}\n2) {advice_2}\n3) {advice_3}"
        ],
        "court_strategy": [
            "在法庭上，您可以採取以下策略：\n1. {strategy_1}\n2. {strategy_2}\n3. {strategy_3}",
            "為了在法庭上取得有利結果，您可以：\n- {strategy_1}\n- {strategy_2}\n- {strategy_3}",
            "法庭攻防建議：\n1) {strategy_1}\n2) {strategy_2}\n3) {strategy_3}"
        ],
        "no_relevant_info": [
            "抱歉，目前系統中沒有與您問題直接相關的法規或判例。建議您諮詢專業律師獲取更準確的法律建議。",
            "您的問題涉及的法律領域可能較為特殊，系統未找到相關法規或判例。建議尋求專業律師協助。",
            "系統未能找到與您問題完全匹配的法律資訊。如需進一步協助，請考慮諮詢法律專業人士。"
        ]
    }
    
    return templates

# 保存回答模板到文件
def save_response_templates(templates, filename):
    try:
        output_path = os.path.join(AI_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)
        log_message(f"成功保存回答模板: {output_path}")
        return True
    except Exception as e:
        log_message(f"保存回答模板失敗: {str(e)}")
        return False

# 建立法律問題分類器
def build_legal_question_classifier():
    # 定義法律問題類別及其關鍵詞
    categories = {
        "刑事": ["殺人", "傷害", "竊盜", "搶奪", "詐欺", "背信", "侵占", "賄賂", "貪污", "偽造文書", "妨害性自主", "妨害自由", "妨害名譽", "毒品", "槍砲", "公共危險"],
        "民事": ["買賣", "租賃", "借貸", "保證", "抵押", "質押", "贈與", "遺囑", "繼承", "侵權", "損害賠償", "債務", "契約", "婚姻", "離婚", "監護", "扶養", "贍養費"],
        "行政": ["訴願", "行政訴訟", "國家賠償", "政府機關", "行政處分", "行政罰", "稅務", "關稅", "地政", "都市計畫", "建築管理", "環境保護", "公務員", "選舉", "罷免"],
        "商業": ["公司", "商標", "專利", "著作權", "智慧財產", "股東", "董事", "監察人", "經理人", "合夥", "破產", "重整", "證券", "期貨", "保險", "票據", "海商", "仲裁"],
        "勞工": ["勞動契約", "工資", "工時", "休假", "退休", "資遣", "職業災害", "勞工保險", "工會", "團體協約", "勞資爭議", "性別歧視", "就業歧視", "職業安全衛生"],
        "家事": ["結婚", "離婚", "子女", "親權", "監護", "收養", "扶養", "贍養費", "遺產", "繼承", "遺囑", "家庭暴力", "親屬", "家庭", "婚姻"]
    }
    
    return categories

# 保存法律問題分類器到文件
def save_legal_question_classifier(classifier, filename):
    try:
        output_path = os.path.join(AI_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(classifier, f, ensure_ascii=False, indent=2)
        log_message(f"成功保存法律問題分類器: {output_path}")
        return True
    except Exception as e:
        log_message(f"保存法律問題分類器失敗: {str(e)}")
        return False

# 主函數
def main():
    log_message("開始實施基於規則的AI解決方案")
    
    # 從數據庫加載法規和判例數據
    laws, cases = load_data_from_db()
    
    if not laws and not cases:
        log_message("無法從數據庫加載數據，無法繼續")
        return
    
    # 建立TF-IDF索引
    log_message("正在建立法規的TF-IDF索引...")
    laws_tfidf, laws_idf = build_tfidf_index(laws)
    save_tfidf_index(laws_tfidf, laws_idf, "laws_tfidf_index.json")
    
    log_message("正在建立判例的TF-IDF索引...")
    cases_tfidf, cases_idf = build_tfidf_index(cases)
    save_tfidf_index(cases_tfidf, cases_idf, "cases_tfidf_index.json")
    
    # 建立法律關鍵詞字典
    log_message("正在建立法律關鍵詞字典...")
    keywords = build_legal_keywords_dict(laws, cases)
    save_legal_keywords_dict(keywords, "legal_keywords_dict.json")
    
    # 建立回答模板
    log_message("正在建立回答模板...")
    templates = build_response_templates()
    save_response_templates(templates, "response_templates.json")
    
    # 建立法律問題分類器
    log_message("正在建立法律問題分類器...")
    classifier = build_legal_question_classifier()
    save_legal_question_classifier(classifier, "legal_question_classifier.json")
    
    log_message("基於規則的AI解決方案設置完成")

if __name__ == "__main__":
    main()
