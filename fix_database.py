#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sqlite3
from datetime import datetime

# 設定基本參數
DB_DIR = "/home/ubuntu/legal-ai-system/data/db"
DB_FILE = os.path.join(DB_DIR, "legal_db.sqlite")
LOG_FILE = os.path.join(DB_DIR, "db_fix_log.txt")

# 確保目錄存在
os.makedirs(DB_DIR, exist_ok=True)

# 記錄函數
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

# 檢查數據庫表結構
def check_database_tables():
    try:
        # 連接到SQLite數據庫
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 檢查laws表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='laws'")
        laws_table_exists = cursor.fetchone() is not None
        
        # 檢查court_cases表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='court_cases'")
        court_cases_table_exists = cursor.fetchone() is not None
        
        log_message(f"數據庫檢查結果: laws表存在: {laws_table_exists}, court_cases表存在: {court_cases_table_exists}")
        
        return laws_table_exists, court_cases_table_exists
    except Exception as e:
        log_message(f"檢查數據庫表結構失敗: {str(e)}")
        return False, False

# 創建缺失的表
def create_missing_tables(laws_exists, court_cases_exists):
    try:
        # 連接到SQLite數據庫
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 如果laws表不存在，創建它
        if not laws_exists:
            log_message("創建laws表...")
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
            
            log_message("laws表創建成功")
        
        # 如果court_cases表不存在，創建它
        if not court_cases_exists:
            log_message("創建court_cases表...")
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
            
            log_message("court_cases表創建成功")
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        log_message(f"創建缺失的表失敗: {str(e)}")
        return False

# 插入示例數據
def insert_sample_data():
    try:
        # 連接到SQLite數據庫
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 檢查laws表是否為空
        cursor.execute("SELECT COUNT(*) FROM laws")
        laws_count = cursor.fetchone()[0]
        
        # 檢查court_cases表是否為空
        cursor.execute("SELECT COUNT(*) FROM court_cases")
        court_cases_count = cursor.fetchone()[0]
        
        log_message(f"當前數據庫中有 {laws_count} 條法規和 {court_cases_count} 條判例")
        
        # 如果laws表為空，插入示例法規數據
        if laws_count == 0:
            log_message("插入示例法規數據...")
            
            sample_laws = [
                (
                    "中華民國刑法",
                    "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=C0000001",
                    "2023-01-01",
                    """第 1 條
                    行為之處罰，以行為時之法律有明文規定者為限。
                    拘束人身自由之保安處分，亦同。
                    
                    第 2 條
                    行為後法律有變更者，適用行為時之法律。但行為後之法律有利於行為人者，適用最有利於行為人之法律。
                    沒收、非拘束人身自由之保安處分適用裁判時之法律。
                    處罰或保安處分之裁判確定後，未執行或執行未完畢，而法律有變更，不處罰其行為或不施以保安處分者，免其刑或保安處分之執行。
                    
                    第 3 條
                    本法於在中華民國領域內犯罪者，適用之。在中華民國領域外之中華民國船艦或航空器內犯罪者，以在中華民國領域內犯罪論。
                    
                    第 4 條
                    犯罪之行為或結果，有一在中華民國領域內者，為在中華民國領域內犯罪。
                    
                    第 5 條
                    本法於凡在中華民國領域外犯下列各罪者，適用之：
                    一、內亂罪。
                    二、外患罪。
                    三、第一百三十五條、第一百三十六條之妨害公務罪。
                    四、第一百八十五條之一之公共危險罪。
                    五、偽造貨幣罪。
                    六、第二百零一條至第二百零二條之偽造有價證券罪。
                    七、第二百一十一條、第二百一十四條、第二百一十八條之偽造文書印文罪。
                    八、第二百九十六條、第二百九十六條之一之妨害自由罪。
                    九、第三百三十三條、第三百三十四條、第三百三十四條之一、第三百四十八條、第三百四十八條之一之竊盜罪。
                    十、第三百三十九條、第三百三十九條之三、第三百四十條、第三百四十四條、第三百四十六條、第三百四十六條之一、第三百四十六條之二之詐欺罪。
                    十一、第三百三十九條之四之侵占罪。""",
                    "政府資料開放平臺",
                    "刑法",
                    datetime.now().isoformat()
                ),
                (
                    "中華民國民法",
                    "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=B0000001",
                    "2023-01-01",
                    """第 1 條
                    民事，法律所未規定者，依習慣；無習慣者，依法理。
                    
                    第 2 條
                    民事所適用之習慣，以不背於公共秩序或善良風俗者為限。
                    
                    第 3 條
                    依法律之規定，有使用文字之必要者，得不由本人自寫，但必須親自簽名。
                    如有用印章代簽名者，其蓋章與簽名生同等之效力。
                    如以指印、十字或其他符號代簽名者，在文件上，經二人簽名證明，亦與簽名生同等之效力。
                    
                    第 4 條
                    關於一定之數量，同時以文字及號碼表示者，其文字與號碼有不符合時，如法院不能決定何者為當事人之原意，應以文字為準。
                    
                    第 5 條
                    年齡自出生之日起算。
                    計算年齡，以出生之日為一歲，爾後每屆期一年，加一歲。
                    
                    第 6 條
                    稱成年者，謂年滿二十歲而未受監護或輔助宣告之人。""",
                    "政府資料開放平臺",
                    "民法",
                    datetime.now().isoformat()
                ),
                (
                    "中華民國憲法",
                    "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=A0000001",
                    "2023-01-01",
                    """第 1 條
                    中華民國基於三民主義，為民有民治民享之民主共和國。
                    
                    第 2 條
                    中華民國之主權屬於國民全體。
                    
                    第 3 條
                    具有中華民國國籍者為中華民國國民。
                    
                    第 4 條
                    中華民國領土，依其固有之疆域，非經國民大會之決議，不得變更之。
                    
                    第 5 條
                    中華民國各民族一律平等。
                    
                    第 6 條
                    中華民國國旗定為紅地，左上角青天白日。""",
                    "政府資料開放平臺",
                    "憲法",
                    datetime.now().isoformat()
                )
            ]
            
            cursor.executemany('''
            INSERT INTO laws (title, url, date, content, source, category, processed_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', sample_laws)
            
            log_message(f"成功插入 {len(sample_laws)} 條示例法規數據")
        
        # 如果court_cases表為空，插入示例判例數據
        if court_cases_count == 0:
            log_message("插入示例判例數據...")
            
            sample_cases = [
                (
                    "109-台上-2134",
                    "最高法院 109 年度台上字第 2134 號刑事判決",
                    """最高法院刑事判決
                    109年度台上字第2134號
                    
                    上訴人 公訴人
                    被上訴人 李○○
                    
                    上列上訴人因被上訴人傷害案件，不服台灣高等法院108年度上訴字第3219號中華民國108年12月18日第二審判決（起訴案號：台灣台北地方法院檢察署107年度偵字第22720號），提起上訴，本院判決如下：
                    
                    主文
                    上訴駁回。
                    
                    理由
                    一、按刑事訴訟法第三百七十七條規定，上訴於第三審法院，非以判決違背法令為理由，不得為之。是提起第三審上訴，應以原判決違背法令為理由，並具體指摘原判決不適用何種法則或如何適用不當，或對於如何違背法令有何具體理由，始為適法。
                    二、本件公訴意旨略以：被告李○○於民國107年9月23日晚間10時許，在臺北市○○區○○路0號前，因故與告訴人黃○○發生爭執，竟基於傷害之犯意，持其所有之安全帽，朝告訴人頭部毆打數下，致告訴人受有頭部挫傷、右側顏面挫傷等傷害，因認被告涉犯刑法第277條第1項之傷害罪嫌等語。
                    三、原審斟酌上開證據及調查之結果，已依論理法則及經驗法則，認定上訴意旨所指摘之事項，或屬原審採證認事職權之適法行使，或已經原審詳予調查審認，或屬與判決結果不生影響之事項，均難認有何違背法令之處。核其所為論斷與卷內資料相符，經核於法並無違誤，亦無足採之理由。
                    四、至於上訴意旨略謂：(一)原判決未詳加調查證人證述之矛盾處，有應於審判期日調查之證據未予調查之違法。(二)被告所為，係出於正當防衛，原判決未詳查，有適用法則不當之違法等語。惟查：
                    (一)、刑事訴訟法第159條第1項規定：「被告以外之人於審判外之言詞或書面陳述，除法律有規定者外，不得作為證據」，此即傳聞法則。同法第159條之1至第159條之5則係傳聞例外之規定。原判決已說明證人黃○○於警詢及偵查中之證述，符合刑事訴訟法第159條之3之規定，自得為證據。且原判決已說明其所憑之證據及認定之理由，並就上訴意旨所指摘之事項，詳為論述，因認被告所辯：其係遭告訴人先以機車安全帽攻擊，其始基於防衛之意，持安全帽予以還擊云云，並不可採，已詳述其採證認事之理由，經核於法並無違誤。上訴意旨猶執前詞，無非係就原審採證認事之職權行使，暨原判決已說明不採之理由，任意指摘，並就原審已論斷者，泛言未詳查，均無可採。
                    (二)、按正當防衛，須以防衛權之行使，確有其事實上之必要，且所採防衛手段與防衛目的，亦須相當，始能阻卻違法性。倘行為人對正在不法侵害其權利之人，施以過度之反擊行為，則屬過當防衛，仍應成立犯罪，僅得減輕其刑而已。查原判決已說明被告所辯係遭告訴人先以機車安全帽攻擊，其始基於防衛之意，持安全帽予以還擊云云，並不可採，已詳述其採證認事之理由，經核於法並無違誤。上訴意旨猶執前詞，無非係就原審採證認事之職權行使，暨原判決已說明不採之理由，任意指摘，並就原審已論斷者，泛言未詳查，均無可採。
                    五、綜上所述，原判決並無違誤，上訴論旨，指摘原判決不當，求予廢棄，非有理由，應予駁回。
                    六、據上論結，應依刑事訴訟法第三百九十五條前段，判決如主文。
                    
                    中華民國109年5月28日
                    最高法院刑事第七庭
                    審判長法官 吳○○
                    法官 林○○
                    法官 蔡○○
                    法官 黃○○
                    法官 蔡○○""",
                    "2020-05-28",
                    "109-台上-2134",
                    "刑事",
                    "109",
                    "sample_case_1.json",
                    datetime.now().isoformat()
                ),
                (
                    "108-台上-1234",
                    "最高法院 108 年度台上字第 1234 號民事判決",
                    """最高法院民事判決
                    108年度台上字第1234號
                    
                    上訴人 張○○
                    被上訴人 王○○
                    
                    上列上訴人因與被上訴人間請求給付租金事件，不服台灣高等法院107年度上字第789號中華民國107年12月20日第二審判決（起訴案號：台灣台北地方法院106年度訴字第12345號），提起上訴，本院判決如下：
                    
                    主文
                    原判決廢棄，發回台灣高等法院。
                    
                    理由
                    一、按上訴第三審法院，非以原判決違背法令為理由，不得為之。又提起第三審上訴，應以原判決違背法令為理由，並具體指摘原判決不適用法規或適用不當之處。
                    二、本件上訴人主張：伊於民國105年1月1日將坐落台北市○○區○○路0號房屋（下稱系爭房屋）出租予被上訴人，租期3年，每月租金新台幣（下同）2萬元，約定於每月5日前給付當月租金。詎被上訴人自106年7月起即未依約給付租金，迄今積欠租金共計36萬元（自106年7月起至107年6月止，計18個月）。爰依租賃契約之約定，請求被上訴人給付積欠之租金36萬元及依約定年息5%計算之遲延利息。
                    三、被上訴人則以：伊於106年6月30日即已搬離系爭房屋，並已將鑰匙交還上訴人，兩造間之租賃關係已合意終止，伊並無積欠租金等語，資為抗辯。
                    四、原審斟酌全辯論意旨及調查證據之結果，以：兩造固於105年1月1日就系爭房屋成立租賃契約，惟被上訴人抗辯伊於106年6月30日已搬離系爭房屋，並已將鑰匙交還上訴人，兩造間之租賃關係已合意終止乙節，業據證人李○○證述明確，且有Line通訊軟體之對話紀錄可稽，堪信為真實。是兩造間之租賃關係既已於106年6月30日終止，上訴人請求被上訴人給付106年7月以後之租金，為無理由，不應准許。因而維持第一審所為上訴人敗訴之判決，駁回其上訴。
                    五、惟查，兩造就系爭房屋成立租賃契約，固經原審認定屬實，惟租賃關係是否已於106年6月30日終止，攸關上訴人請求被上訴人給付106年7月以後租金之請求權是否存在，原審未詳查Line通訊軟體對話紀錄之真實性及完整性，遽採證人李○○之證述，認定兩造間之租賃關係已於106年6月30日終止，自有可議。況證人李○○與被上訴人為何關係，其證述是否可採，原審未予調查審認，即遽採為判決之基礎，亦嫌速斷。上訴論旨，指摘原判決違背法令，求予廢棄，非無理由。
                    六、據上論結，本件上訴為有理由。依民事訴訟法第四百七十七條第一項、第四百七十八條第一項，判決如主文。
                    
                    中華民國108年6月15日
                    最高法院民事第二庭
                    審判長法官 陳○○
                    法官 林○○
                    法官 張○○
                    法官 李○○
                    法官 王○○""",
                    "2019-06-15",
                    "108-台上-1234",
                    "民事",
                    "108",
                    "sample_case_2.json",
                    datetime.now().isoformat()
                ),
                (
                    "107-訴-5678",
                    "臺灣臺北地方法院 107 年度訴字第 5678 號刑事判決",
                    """臺灣臺北地方法院刑事判決
                    107年度訴字第5678號
                    
                    公訴人 臺灣臺北地方法院檢察署檢察官
                    被告 陳○○
                    
                    上列被告因過失傷害案件，經檢察官提起公訴（107年度偵字第12345號），本院判決如下：
                    
                    主文
                    陳○○犯過失傷害罪，處拘役貳拾日，如易科罰金，以新臺幣壹仟元折算壹日。
                    
                    事實及理由
                    一、本件犯罪事實及證據，除下列事項外，其餘均引用檢察官起訴書之記載：
                    (一)、被告陳○○於民國107年3月15日上午10時許，駕駛車牌號碼0000-00號自小客車，沿臺北市○○區○○路由南往北方向行駛，行經○○路與○○街口時，本應注意車前狀況，並隨時採取必要之安全措施，而依當時天候晴、日間自然光線、柏油路面乾燥無缺陷、視距良好，並無不能注意之情形，竟疏未注意車前狀況，貿然左轉進入○○街，適有告訴人林○○騎乘車牌號碼0000-00號普通重型機車沿○○路由北往南方向行駛而來，兩車因而發生碰撞，致告訴人受有右側鎖骨骨折、右側肋骨骨折等傷害。
                    (二)、證據部分：
                    1.被告陳○○於警詢及偵查中之自白。
                    2.告訴人林○○於警詢及偵查中之指訴。
                    3.交通事故現場圖、道路交通事故調查報告表、車輛勘驗照片、監視器畫面翻拍照片等在卷可稽。
                    4.告訴人之診斷證明書在卷可參。
                    二、按駕駛人轉彎時，應依標誌、標線、號誌指示或下列規定行之：一、應距離交岔路口三十公尺前顯示方向燈或手勢，換入內側車道或左側車道，駛至交岔路口中心處左轉，道路交通安全規則第102條第1項第1款定有明文。查被告駕駛自小客車，轉彎進入○○街時，未注意有告訴人騎乘機車由對向駛來，貿然左轉，致兩車發生碰撞，此有交通事故現場圖、道路交通事故調查報告表、車輛勘驗照片、監視器畫面翻拍照片等在卷可稽，並有告訴人之診斷證明書可參，是被告過失傷害犯行洵堪認定，應依刑法第284條第1項規定論處。
                    三、爰審酌被告犯罪動機、目的、手段、犯後態度，及告訴人傷勢等一切情狀，量處如主文所示之刑，並諭知易科罰金之折算標準。
                    四、據上論斷，應依刑事訴訟法第273條之1第1項、第299條第1項前段，刑法第284條第1項、第41條第1項前段、第42條第3項，判決如主文。
                    
                    中華民國107年9月20日
                    臺灣臺北地方法院刑事第五庭
                    法官 吳○○""",
                    "2018-09-20",
                    "107-訴-5678",
                    "刑事",
                    "107",
                    "sample_case_3.json",
                    datetime.now().isoformat()
                )
            ]
            
            cursor.executemany('''
            INSERT INTO court_cases (case_id, title, content, date, case_number, case_type, year, source_file, processed_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', sample_cases)
            
            log_message(f"成功插入 {len(sample_cases)} 條示例判例數據")
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        log_message(f"插入示例數據失敗: {str(e)}")
        return False

# 主函數
def main():
    log_message("開始修復數據庫問題")
    
    # 檢查數據庫表結構
    laws_exists, court_cases_exists = check_database_tables()
    
    # 創建缺失的表
    if not laws_exists or not court_cases_exists:
        create_missing_tables(laws_exists, court_cases_exists)
    
    # 插入示例數據
    insert_sample_data()
    
    log_message("數據庫問題修復完成")

if __name__ == "__main__":
    main()
