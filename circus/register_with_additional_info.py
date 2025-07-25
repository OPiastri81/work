from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import csv
import re
import os
import boto3
import io
from datetime import datetime
import pandas as pd
from selenium.common.exceptions import TimeoutException

def create_driver():
    """Chrome WebDriverのセットアップ"""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')  # ヘッドレスモード
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
    options.add_argument('--user-data-dir=/tmp/chrome-debug')
    options.add_argument('--remote-debugging-port=9222')
    driver = webdriver.Chrome(options=options)
    return driver

def extract_prefecture(address):
    """住所から都道府県を抽出"""
    prefecture_pattern = r'(.+?[都道府県])'
    match = re.search(prefecture_pattern, address)
    if match:
        return match.group(1).strip()
    return None

# 都道府県マッピング
prefecture_map = {
    "北海道": "1", "青森県": "2", "岩手県": "3", "宮城県": "4", "秋田県": "5", "山形県": "6", "福島県": "7",
    "茨城県": "8", "栃木県": "9", "群馬県": "10", "埼玉県": "11", "千葉県": "12", "東京都": "13", "神奈川県": "14",
    "新潟県": "15", "富山県": "16", "石川県": "17", "福井県": "18", "山梨県": "19", "長野県": "20",
    "岐阜県": "21", "静岡県": "22", "愛知県": "23", "三重県": "24",
    "滋賀県": "25", "京都府": "26", "大阪府": "27", "兵庫県": "28", "奈良県": "29", "和歌山県": "30",
    "鳥取県": "31", "島根県": "32", "岡山県": "33", "広島県": "34", "山口県": "35",
    "徳島県": "36", "香川県": "37", "愛媛県": "38", "高知県": "39",
    "福岡県": "40", "佐賀県": "41", "長崎県": "42", "熊本県": "43", "大分県": "44", "宮崎県": "45", "鹿児島県": "46", "沖縄県": "47",
    "海外": "48"
}

# 担当者マッピング
assignee_map = {
    "96_五十嵐": {"name": "五十嵐 翔", "id": "3665"},
    "01_吉澤": {"name": "吉澤　亜沙美", "id": "3682"},
    "98_家治川": {"name": "家治川 輝", "id": "5657"},
    "97_中東": {"name": "中東貴洋", "id": "5788"},
    "95_飯田": {"name": "飯田常仁", "id": "19552"},
    "LIF 採用サポート": {"name": "株式会社LIF 採用サポート", "id": "21049"},
    "94_久保": {"name": "久保翔一", "id": "21351"},
    #"LIF 採用サポート02": {"name": "株式会社LIF 採用サポート02", "id": "21554"},
    "サンプル": {"name": "株式会社LIF 採用サポート02", "id": "21554"},
    "93_松本": {"name": "松本秀香", "id": "22689"},
}

def get_csv_from_s3(s3_key):
    """S3からCSVファイルを取得"""
    try:
        s3_client = boto3.client('s3')
        bucket_name = 'dev1-randd'
        
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        csv_content = response['Body'].read().decode('utf-8')
        df = pd.read_csv(io.StringIO(csv_content))
        print(f"S3からCSVファイルを正常に取得しました: s3://{bucket_name}/{s3_key}")
        
        # 必要なカラムの確認
        required_columns = ['name', 'furigana', 'birthyear', 'birthmonth', 'birthday', 
                          'gender', 'postal', 'address', 'phone', 'email', 'license', 
                          'education', 'final_grade', 'school_name', 'person_in_charge', 
                          'folder_id', 'number_of_companies_worked#2']
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"警告: 以下のカラムが見つかりません: {missing_columns}")
            
        return df
        
    except Exception as e:
        print(f"S3からCSVファイルの取得中にエラーが発生しました: {str(e)}")
        return None

def get_s3_csv_files():
    """処理対象のCSVファイルリストを取得"""
    try:
        # 元の指定されたCSVファイルを使用
        csv_files = ['register-circus/output_data/DataBase_for_EC2/output_data.csv']
        print(f"指定されたCSVファイル: {csv_files[0]}")
        return csv_files
    except Exception as e:
        print(f"CSVファイル一覧の取得中にエラーが発生しました: {str(e)}")
        return []

def get_assignee_id_from_person_in_charge(person_in_charge):
    """person_in_chargeの値から担当者IDを返す"""
    print(f"person_in_chargeの値: {person_in_charge}")
    if person_in_charge in assignee_map:
        assignee_id = assignee_map[person_in_charge]['id']
        print(f"assignee_mapで選択された担当者名: {person_in_charge} (ID: {assignee_id})")
        return person_in_charge, assignee_id
    else:
        print(f"担当者 '{person_in_charge}' に対応するIDが見つかりません")
        return person_in_charge, None

def save_to_s3(registration_data_list):
    """登録結果をS3に保存"""
    try:
        s3_client = boto3.client('s3')
        bucket_name = 'dev1-randd'
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'output_data.csv'
        
        csv_buffer = io.StringIO()
        fieldnames = ['name', 'furigana', 'birthYear', 'birthMonth', 'birthDay', 'postal', 
                     'address', 'phone', 'email', 'license', 'education', 'folder_id', 
                     '転記日時', '登録結果', '追加情報編集結果', '担当者']
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        
        writer.writeheader()
        for data in registration_data_list:
            writer.writerow(data)
        
        s3_key = f'register-circus/result/output_data/{filename}'
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=csv_buffer.getvalue().encode('utf-8'),
            ContentType='text/csv'
        )
        
        print(f"登録データ {len(registration_data_list)}件をS3に保存しました: s3://{bucket_name}/{s3_key}")
        
        # 名前とfolder_idのみの簡潔なCSVも保存
        simple_csv_buffer = io.StringIO()
        simple_fieldnames = ['name', 'folder_id']
        simple_writer = csv.DictWriter(simple_csv_buffer, fieldnames=simple_fieldnames)
        
        simple_writer.writeheader()
        for data in registration_data_list:
            simple_writer.writerow({
                'name': data['name'],
                'folder_id': data['folder_id']
            })
        
        simple_filename = f'output_data.csv'
        simple_s3_key = f'register-circus/result/output_data/{simple_filename}'
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=simple_s3_key,
            Body=simple_csv_buffer.getvalue().encode('utf-8'),
            ContentType='text/csv'
        )
        
        print(f"名前とfolder_idのみのCSVも保存しました: s3://{bucket_name}/{simple_s3_key}")
        
        return True
        
    except Exception as e:
        print(f"S3への保存中にエラーが発生しました: {str(e)}")
        return False

def verify_registration(driver, data):
    """登録が実際に成功したかどうかを確認"""
    try:
        print("=== 登録確認処理を開始 ===")
        time.sleep(5)  # ページ遷移を待機
        
        current_url = driver.current_url
        print(f"現在のURL: {current_url}")
        
        # URLから求職者IDを抽出
        if '/job-seekers/' in current_url:
            job_seeker_id = current_url.split('/job-seekers/')[-1]
            print(f"求職者ID: {job_seeker_id}")
            
            # ページの内容を確認
            page_source = driver.page_source
            if data['name'] in page_source:
                print(f"✅ 登録成功確認: {data['name']} の名前がページに表示されています")
                return True, job_seeker_id
            else:
                print(f"❌ 登録失敗: {data['name']} の名前がページに表示されていません")
                return False, None
        else:
            print("❌ 求職者詳細ページに遷移していません")
            return False, None
            
    except Exception as e:
        print(f"登録確認処理中にエラーが発生しました: {str(e)}")
        return False, None

def login_to_circus(driver, wait):
    """circusにログインする"""
    try:
        print("サイトにアクセスします...")
        driver.get("https://circus-job.com/login")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(5)

        print(f"現在のURL: {driver.current_url}")
        print(f"ページタイトル: {driver.title}")

        # すでにログイン済みか判定
        login_form = None
        try:
            login_form = wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
            print("ログインフォームを確認しました")
        except Exception as e:
            print(f"ログインフォームが見つかりません: {str(e)}")
            print("ログイン済みと判断し、ログイン処理をスキップします")
            return True

        if login_form:
            print("ログイン処理を開始します...")
            
            # メールアドレス入力
            print("メールアドレスを入力します...")
            email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            email_input.clear()
            # 環境変数の取得（大文字・小文字両方に対応）
            email_value = os.environ.get("email") or os.environ.get("EMAIL")
            if not email_value:
                raise Exception("環境変数 'email' または 'EMAIL' が設定されていません")
            email_input.send_keys(email_value)
            
            # パスワード入力
            print("パスワードを入力します...")
            password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_value = os.environ.get("password") or os.environ.get("PASSWORD")
            if not password_value:
                raise Exception("環境変数 'password' または 'PASSWORD' が設定されていません")
            password_input.send_keys(password_value)
            
            # ログインボタンクリック
            print("ログインボタンをクリックします...")
            login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'ログイン')]")))
            login_button.click()
            time.sleep(2)
            
            # モーダル処理
            try:
                modal = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "MuiDialog-container")))
                close_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='close']")))
                close_button.click()
                time.sleep(2)
            except Exception as e:
                print(f"モーダルダイアログの処理中にエラーが発生しました: {str(e)}")
            
            # フォーム送信
            print("フォーム送信ボタンをクリックします...")
            submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            driver.execute_script("arguments[0].click();", submit_button)
            time.sleep(5)
            
            # 確認ポップアップ処理
            try:
                confirm_button = wait.until(EC.element_to_be_clickable((
                    By.CSS_SELECTOR, 
                    "button.MuiButtonBase-root.MuiButton-root.MuiButton-contained.MuiButton-containedConversion[type='submit'][form='loginForm']"
                )))
                confirm_button.click()
                time.sleep(3)
            except Exception as e:
                print(f"ログイン確認ポップアップの処理中にエラーが発生しました: {str(e)}")
            
            # ログイン後のページ遷移を待機
            print("ログイン後のページ遷移を待機します...")
            try:
                wait.until(EC.url_changes("https://circus-job.com/login"))
                time.sleep(3)
                wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'MuiDrawer-root')]")))
                print("ログイン成功を確認しました")
                return True
            except Exception as e:
                print(f"ログイン後のページ遷移でエラーが発生しました: {str(e)}")
                return False
        
        return True
        
    except Exception as e:
        print(f"ログイン処理中にエラーが発生しました: {str(e)}")
        return False

def register_job_seeker(driver, wait, data, assignee_id):
    """ステップ1: 求職者の基本情報を登録"""
    try:
        print("=== ステップ1: 求職者の基本情報登録を開始 ===")
        
        # ダイアログ処理
        try:
            dialogs = driver.find_elements(By.CLASS_NAME, "MuiDialog-container")
            if dialogs:
                print("ダイアログを処理します...")
                close_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='close']")))
                close_button.click()
                time.sleep(2)
        except Exception as e:
            print(f"ダイアログの処理中にエラーが発生しました: {str(e)}")

        # メニューボタンをクリック
        print("メニューボタンを探しています...")
        menu_selectors = [
            "//button[contains(@class, 'MuiIconButton-root')]",
            "//button[contains(@class, 'MuiButtonBase-root')]",
            "//button[@aria-label='menu']",
            "//button[@aria-label='open drawer']"
        ]
        
        menu_button = None
        for selector in menu_selectors:
            try:
                menu_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                if menu_button:
                    print(f"メニューボタンを見つけました: {selector}")
                    break
            except:
                continue
        
        if not menu_button:
            raise Exception("メニューボタンが見つかりませんでした")
        
        driver.execute_script("arguments[0].click();", menu_button)
        time.sleep(3)

        # 求職者メニューをクリック
        print("求職者メニューを探しています...")
        job_seeker_selectors = [
            "//div[contains(@class, 'MuiListItem-root')]//span[contains(text(), '求職者')]",
            "//div[contains(@class, 'MuiListItem-root')]//div[contains(text(), '求職者')]",
            "//a[contains(@href, '/job-seeker')]",
            "//div[contains(@class, 'MuiListItem-root')]//a[contains(@href, '/job-seeker')]"
        ]
        
        job_seeker_button = None
        for selector in job_seeker_selectors:
            try:
                job_seeker_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                if job_seeker_button:
                    print(f"求職者メニューを見つけました: {selector}")
                    break
            except:
                continue
                
        if not job_seeker_button:
            raise Exception("求職者メニューが見つかりませんでした")
            
        driver.execute_script("arguments[0].click();", job_seeker_button)
        time.sleep(3)

        # 求職者登録リンクをクリック
        print("求職者登録リンクを探しています...")
        register_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/register/job-seeker')]")))
        driver.execute_script("arguments[0].click();", register_link)
        time.sleep(3)

        # 基本情報を入力
        print("基本情報を入力します...")
        wait.until(EC.presence_of_element_located((By.NAME, "name")))
        
        driver.find_element(By.NAME, "name").send_keys(data['name'])
        driver.find_element(By.NAME, "nameRuby").send_keys(data['furigana'])
        driver.find_element(By.NAME, "email").send_keys(data['email'])
        driver.find_element(By.NAME, "phone").send_keys(data['phone'])
        driver.find_element(By.NAME, "birthday.year").send_keys(str(data['birthyear']))
        driver.find_element(By.NAME, "birthday.month").send_keys(str(data['birthmonth']))
        driver.find_element(By.NAME, "birthday.day").send_keys(str(data['birthday']))

        # 性別ラジオボタンを選択
        print("性別を選択します...")
        gender_value = str(data.get('gender', '')).strip()
        print(f"性別の値: '{gender_value}' (型: {type(gender_value)})")
        
        if gender_value:
            try:
                # 性別の値を正規化
                gender_normalized = gender_value.lower()
                selected_gender = None
                
                if gender_normalized in ["男性", "male", "m", "1", "男", "おとこ"]:
                    selected_gender = "1"
                    gender_text = "男性"
                elif gender_normalized in ["女性", "female", "f", "2", "女", "おんな"]:
                    selected_gender = "2"
                    gender_text = "女性"
                else:
                    print(f"不明な性別値: {gender_value}。性別ラジオボタンは選択しません")
                    selected_gender = None
                
                if selected_gender:
                    print(f"性別 '{gender_text}' (値: {selected_gender}) を選択を試行します...")
                    
                    # 複数の方法でラジオボタンを探す
                    radio_selectors = [
                        f"input[name='gender'][value='{selected_gender}']",
                        f"input[type='radio'][name='gender'][value='{selected_gender}']",
                        f"//input[@name='gender' and @value='{selected_gender}']",
                        f"//input[@type='radio' and @name='gender' and @value='{selected_gender}']"
                    ]
                    
                    radio_found = False
                    for selector in radio_selectors:
                        try:
                            if selector.startswith("//"):
                                radio_button = driver.find_element(By.XPATH, selector)
                            else:
                                radio_button = driver.find_element(By.CSS_SELECTOR, selector)
                            
                            if radio_button:
                                print(f"性別ラジオボタンを発見: {selector}")
                                
                                # ラジオボタンが見える位置にスクロール
                                driver.execute_script("arguments[0].scrollIntoView(true);", radio_button)
                                time.sleep(0.5)
                                
                                # クリックを実行
                                driver.execute_script("arguments[0].click();", radio_button)
                                print(f"{gender_text}ラジオボタンを選択しました")
                                radio_found = True
                                
                                # 選択されたかどうかを確認
                                if radio_button.is_selected():
                                    print(f"✅ {gender_text}ラジオボタンが正常に選択されました")
                                else:
                                    print(f"⚠️ {gender_text}ラジオボタンの選択状態を確認できませんでした")
                                
                                break
                        except Exception as e:
                            print(f"セレクタ {selector} での性別選択中にエラー: {str(e)}")
                            continue
                    
                    if not radio_found:
                        print(f"❌ 性別 '{gender_text}' のラジオボタンが見つかりませんでした")
                        
            except Exception as e:
                print(f"性別ラジオボタンの選択中にエラー: {str(e)}")
        else:
            print("性別の値が空のため、性別選択をスキップします")

        # 都道府県を選択
        print("都道府県を選択します...")
        prefecture = extract_prefecture(data.get('address', ''))
        if prefecture:
            try:
                prefecture_element = driver.find_element(By.NAME, "prefecture")
                prefecture_select = Select(prefecture_element)
                if prefecture in prefecture_map:
                    prefecture_value = prefecture_map[prefecture]
                    prefecture_select.select_by_value(prefecture_value)
                    print(f"都道府県: '{prefecture}' を選択しました。")
                else:
                    print(f"'{prefecture}' は有効な都道府県ではありません。")
            except Exception as e:
                print(f"都道府県選択中にエラー: {str(e)}")

        # 担当者を選択
        print(f"担当者を選択します... (担当者ID: {assignee_id})")
        try:
            assignee_select = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[name='assignees[0]']")))
            assignee_dropdown = Select(assignee_select)
            assignee_dropdown.select_by_value(str(assignee_id))
            print(f"担当者ID {assignee_id} を選択しました")
        except Exception as e:
            print(f"担当者選択中にエラーが発生しました: {str(e)}")
            raise

        time.sleep(1)
        
        # 『作成する』ボタンをクリック
        print("『作成する』ボタンをクリックします...")
        create_button_selectors = [
            "//button[@type='submit' and contains(text(), '作成する')]",
            "//button[contains(@class, 'MuiButton-containedSecondary') and contains(text(), '作成する')]",
            "//button[contains(@class, 'FormSubmitButton-buttonWidth') and contains(text(), '作成する')]",
            "button[type='submit']"
        ]
        
        create_button = None
        for selector in create_button_selectors:
            try:
                if selector.startswith("//"):
                    create_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                else:
                    create_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    
                if create_button:
                    button_text = create_button.text
                    print(f"ボタンのテキスト: {button_text}")
                    if '作成する' in button_text:
                        print("正しいボタンを確認しました")
                        break
                    else:
                        create_button = None
                        continue
            except Exception as e:
                continue
        
        if not create_button:
            raise Exception("『作成する』ボタンが見つかりませんでした")
        
        driver.execute_script("arguments[0].scrollIntoView(true);", create_button)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", create_button)
        print("『作成する』ボタンをクリックしました。")
        time.sleep(5)

        # 登録確認
        registration_success, job_seeker_id = verify_registration(driver, data)
        
        if registration_success:
            print(f"✅ 求職者 {data['name']} の登録が完了しました。")
            return True, job_seeker_id
        else:
            print(f"❌ 求職者 {data['name']} の登録に失敗しました。")
            return False, None

    except Exception as e:
        print(f"求職者登録処理でエラーが発生しました: {str(e)}")
        return False, None

def edit_additional_info(driver, wait, data):
    """ステップ2: 追加情報の編集と保存"""
    try:
        print("=== ステップ2: 追加情報の編集を開始 ===")
        
        # 複数の求職者一覧ページURLを試行
        print("求職者一覧ページに移動します...")
        list_urls = [
            "https://circus-job.com/job-seekers",  # 複数形のURL
            "https://circus-job.com/job-seeker",   # 単数形のURL
            "https://circus-job.com/jobseekers",   # ハイフンなし
            "https://circus-job.com/jobseeker"     # ハイフンなし・単数形
        ]
        
        list_page_found = False
        for url in list_urls:
            try:
                print(f"URLを試行中: {url}")
                driver.get(url)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(3)
                
                # ページタイトルをチェック
                page_title = driver.title
                print(f"ページタイトル: {page_title}")
                
                if "ページが見つかりませんでした" not in page_title and "404" not in page_title:
                    print(f"正しい一覧ページを発見: {url}")
                    list_page_found = True
                    break
                else:
                    print(f"このURLは無効でした: {url}")
                    
            except Exception as e:
                print(f"URL {url} でエラー: {str(e)}")
                continue
        
        if not list_page_found:
            print("求職者一覧ページが見つかりませんでした。メニューから移動を試行します...")
            
            # メニューから求職者一覧に移動を試行
            try:
                # メニューボタンをクリック
                menu_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'MuiIconButton-root')]")))
                driver.execute_script("arguments[0].click();", menu_button)
                time.sleep(2)
                
                # 求職者メニューをクリック
                job_seeker_menu = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/job-seeker')]")))
                driver.execute_script("arguments[0].click();", job_seeker_menu)
                time.sleep(3)
                
                print("メニューから求職者ページに移動しました")
                
            except Exception as e:
                print(f"メニューからの移動でもエラー: {str(e)}")
                return False

        # 複数の方法で担当者絞り込みを試行
        print("担当者絞り込みを設定します...")
        assignee_selectors = [
            "select[name='assignee']",
            "select[name='assignees']", 
            "//select[contains(@name, 'assignee')]",
            "//select[contains(@id, 'assignee')]",
            ".MuiSelect-root",
            "[data-testid*='assignee']"
        ]
        
        assignee_select_found = False
        for selector in assignee_selectors:
            try:
                if selector.startswith("//"):
                    assignee_select = driver.find_element(By.XPATH, selector)
                else:
                    assignee_select = driver.find_element(By.CSS_SELECTOR, selector)
                    
                if assignee_select:
                    print(f"担当者絞り込み要素を発見: {selector}")
                    select = Select(assignee_select)
                    select.select_by_value("")  # 空値ですべての担当者を選択
                    print("担当者絞り込みで『すべての担当者』を選択しました")
                    assignee_select_found = True
                    time.sleep(2)
                    break
            except Exception as e:
                continue
        
        if not assignee_select_found:
            print("担当者絞り込み要素が見つかりませんでした。そのまま続行します。")

        # 複数の方法で検索・一覧更新ボタンを試行
        print("検索・一覧更新ボタンを探します...")
        search_selectors = [
            "button[type='submit']",
            "//button[contains(text(), '検索')]",
            "//button[contains(text(), '更新')]",
            "//button[contains(text(), 'search')]",
            ".MuiButton-root[type='submit']",
            "form button",
            "[data-testid*='search']",
            "[data-testid*='submit']"
        ]
        
        search_btn_found = False
        for selector in search_selectors:
            try:
                if selector.startswith("//"):
                    search_btn = driver.find_element(By.XPATH, selector)
                else:
                    search_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    
                if search_btn and search_btn.is_displayed():
                    print(f"検索ボタンを発見: {selector}")
                    driver.execute_script("arguments[0].click();", search_btn)
                    print("一覧を更新しました")
                    search_btn_found = True
                    time.sleep(3)
                    break
            except Exception as e:
                continue
        
        if not search_btn_found:
            print("検索ボタンが見つかりませんでした。そのまま続行します。")

        # より柔軟な方法で求職者を検索
        print(f"求職者 {data['name']} を検索しています...")
        try:
            # 複数のテーブル構造を試行
            table_selectors = [
                "table tbody tr",
                ".MuiTable-root tbody tr",
                ".MuiTableBody-root tr",
                "[role='table'] [role='row']",
                ".table tbody tr",
                "tbody tr",
                "[data-testid*='table'] tr"
            ]
            
            rows = []
            for selector in table_selectors:
                try:
                    rows = driver.find_elements(By.CSS_SELECTOR, selector)
                    if rows:
                        print(f"テーブル行を発見: {selector} (行数: {len(rows)})")
                        break
                except Exception as e:
                    continue
            
            if not rows:
                # テーブルが見つからない場合、ページ全体で名前を検索
                print("テーブル構造が見つかりません。ページ全体で求職者名を検索します...")
                page_source = driver.page_source
                if data['name'] in page_source:
                    print(f"ページ内で求職者名 {data['name']} を確認しました")
                    # 直接編集リンクを探す
                    edit_selectors = [
                        f"//a[contains(@href, '/job-seekers/') and contains(@href, '/edit')]",
                        f"//a[contains(text(), '編集')]",
                        f"//button[contains(text(), '編集')]",
                        f".MuiButton-root[href*='edit']"
                    ]
                    
                    for edit_selector in edit_selectors:
                        try:
                            if edit_selector.startswith("//"):
                                edit_btns = driver.find_elements(By.XPATH, edit_selector)
                            else:
                                edit_btns = driver.find_elements(By.CSS_SELECTOR, edit_selector)
                            
                            if edit_btns:
                                print(f"編集ボタンを発見: {edit_selector} (個数: {len(edit_btns)})")
                                # 最初の編集ボタンをクリック（最新の登録と仮定）
                                driver.execute_script("arguments[0].click();", edit_btns[0])
                                print("編集ページに遷移しました")
                                time.sleep(3)
                                return True  # 編集ページへの遷移成功
                        except Exception as e:
                            continue
                
                print(f"求職者 {data['name']} の編集リンクが見つかりませんでした")
                return False
            
            # テーブルから求職者を検索
            found = False
            for i, row_elem in enumerate(rows):
                try:
                    row_text = row_elem.text
                    if data['name'] in row_text:
                        print(f"求職者 {data['name']} の行を見つけました (行番号: {i+1})")
                        
                        # 編集ボタンを探す（複数の方法を試行）
                        edit_selectors_in_row = [
                            ".//a[contains(@href, '/job-seekers/') and contains(@href, '/edit')]",
                            ".//a[contains(text(), '編集')]",
                            ".//button[contains(text(), '編集')]",
                            ".//a[contains(@href, 'edit')]"
                        ]
                        
                        for edit_selector in edit_selectors_in_row:
                            try:
                                edit_btn = row_elem.find_element(By.XPATH, edit_selector)
                                if edit_btn:
                                    print(f"編集ボタンを発見: {edit_selector}")
                                    driver.execute_script("arguments[0].click();", edit_btn)
                                    found = True
                                    time.sleep(3)
                                    break
                            except Exception as e:
                                continue
                        
                        if found:
                            break
                except Exception as e:
                    print(f"行 {i+1} の処理でエラー: {str(e)}")
                    continue
                    
            if not found:
                print(f"求職者 {data['name']} の行または編集ボタンが見つかりませんでした")
                return False
                
        except Exception as e:
            print(f"求職者行または編集ボタンの取得でエラー: {str(e)}")
            return False

        # 編集画面で追加情報を入力
        print("編集画面での追加情報入力を開始します...")
        try:
            # 編集ページに到達したことを確認
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
            print("編集フォームを確認しました")
            time.sleep(2)
            
            # CSVデータの値を確認
            print("=== CSVデータの値確認 ===")
            final_grade_value = data.get('final_grade', '')
            school_name_value = data.get('school_name', '')
            num_companies_value = data.get('number_of_companies_worked#2', '')
            
            print(f"final_grade (最終学歴): '{final_grade_value}' (型: {type(final_grade_value)})")
            print(f"school_name (卒業学校名): '{school_name_value}' (型: {type(school_name_value)})")
            print(f"number_of_companies_worked#2 (経験社数): '{num_companies_value}' (型: {type(num_companies_value)})")
            
            # 最終学歴フィールド - selectボックス
            final_grade_value_str = str(final_grade_value).strip()
            if final_grade_value_str and final_grade_value_str != 'nan' and final_grade_value_str != '':
                print(f"最終学歴の入力を開始します: '{final_grade_value_str}'")
                try:
                    # 最終学歴はselectボックス
                    last_education_select = driver.find_element(By.NAME, "lastEducation")
                    if last_education_select and last_education_select.is_displayed():
                        print("最終学歴のselectボックスを発見しました")
                        
                        # selectボックスの選択肢を確認
                        select_obj = Select(last_education_select)
                        options = select_obj.options
                        print("利用可能な最終学歴の選択肢:")
                        for i, option in enumerate(options):
                            print(f"  [{i}] value='{option.get_attribute('value')}', text='{option.text}'")
                        
                        # より正確な値のマッピング（実際の選択肢に基づく）
                        education_mapping = {
                            "高卒": ["高卒", "1"],
                            "専門卒": ["専門卒", "2"], 
                            "短大卒": ["短大卒", "3"],
                            "大卒": ["大卒", "4"],
                            "大学卒": ["大卒", "4"],
                            "大学院卒": ["大学院卒", "5"],
                            "その他": ["その他", "6"]
                        }
                        
                        selected = False
                        
                        # 1. 完全一致を最初に試行
                        for option in options:
                            option_text = option.text.strip()
                            option_value = option.get_attribute('value')
                            if option_text == final_grade_value_str:
                                select_obj.select_by_value(option_value)
                                print(f"最終学歴で完全一致 '{option_text}' (value='{option_value}') を選択しました")
                                selected = True
                                break
                        
                        # 2. マッピングを使用したマッチング
                        if not selected and final_grade_value_str in education_mapping:
                            possible_values = education_mapping[final_grade_value_str]
                            for option in options:
                                option_text = option.text.strip()
                                option_value = option.get_attribute('value')
                                # テキストまたは値での一致をチェック
                                if option_text in possible_values or option_value in possible_values:
                                    select_obj.select_by_value(option_value)
                                    print(f"最終学歴でマッピング一致 '{option_text}' (value='{option_value}') を選択しました")
                                    selected = True
                                    break
                        
                        # 3. 部分一致での試行
                        if not selected:
                            for option in options:
                                option_text = option.text.strip()
                                option_value = option.get_attribute('value')
                                if final_grade_value_str in option_text:
                                    select_obj.select_by_value(option_value)
                                    print(f"最終学歴で部分一致 '{option_text}' (value='{option_value}') を選択しました")
                                    selected = True
                                    break
                        
                        if not selected:
                            print(f"'{final_grade_value_str}' に対応する最終学歴の選択肢が見つかりませんでした")
                            print("利用可能な選択肢と入力値を再確認してください")
                        
                except Exception as e:
                    print(f"最終学歴の設定でエラー: {str(e)}")
            else:
                print("最終学歴の値が空またはnanのため、スキップします")

            # 卒業学校名フィールド - 正確なname属性を使用
            school_name_value_str = str(school_name_value).strip()
            if school_name_value_str and school_name_value_str != 'nan' and school_name_value_str != '':
                print(f"卒業学校名の入力を開始します: '{school_name_value_str}'")
                try:
                    school_name_field = driver.find_element(By.NAME, "schoolName")
                    if school_name_field and school_name_field.is_displayed():
                        print("卒業学校名フィールドを発見: schoolName")
                        school_name_field.clear()
                        school_name_field.send_keys(school_name_value_str)
                        print(f"卒業学校名に '{school_name_value_str}' を入力しました")
                    else:
                        print("卒業学校名フィールドが見つかりませんでした")
                except Exception as e:
                    print(f"卒業学校名の設定でエラー: {str(e)}")
            else:
                print("卒業学校名の値が空またはnanのため、スキップします")

            # 経験社数フィールド - 正確なname属性を使用
            num_companies_value_str = str(num_companies_value).strip()
            if num_companies_value_str and num_companies_value_str != 'nan' and num_companies_value_str != '':
                print(f"経験社数の入力を開始します: '{num_companies_value_str}'")
                try:
                    num_companies_field = driver.find_element(By.NAME, "numberOfCompaniesExperienced")
                    if num_companies_field and num_companies_field.is_displayed():
                        print("経験社数フィールドを発見: numberOfCompaniesExperienced")
                        num_companies_field.clear()
                        num_companies_field.send_keys(num_companies_value_str)
                        print(f"経験社数に '{num_companies_value_str}' を入力しました")
                    else:
                        print("経験社数フィールドが見つかりませんでした")
                except Exception as e:
                    print(f"経験社数の設定でエラー: {str(e)}")
            else:
                print("経験社数の値が空またはnanのため、スキップします")

            print("追加情報の入力処理が完了しました")
            
        except Exception as e:
            print(f"追加情報入力でエラー: {str(e)}")
            # エラーが発生してもそのまま保存を試行

        # 保存ボタンをクリック
        print("保存ボタンを探してクリックします...")
        try:
            save_btn_selectors = [
                "//button[@type='submit' and contains(text(), '保存')]",
                "//button[contains(@class, 'MuiButton') and contains(text(), '保存')]",
                "//button[contains(text(), '更新')]",
                "//button[contains(text(), '送信')]", 
                "//button[contains(text(), 'Save')]",
                "//button[contains(text(), 'Update')]",
                "button[type='submit']",
                "form button[type='submit']",
                ".MuiButton-root[type='submit']",
                "[data-testid*='save']",
                "[data-testid*='submit']"
            ]
            
            save_btn_found = False
            for selector in save_btn_selectors:
                try:
                    if selector.startswith("//"):
                        save_btns = driver.find_elements(By.XPATH, selector)
                    else:
                        save_btns = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for save_btn in save_btns:
                        if save_btn and save_btn.is_displayed() and save_btn.is_enabled():
                            button_text = save_btn.text.strip()
                            print(f"保存ボタンを発見: {selector}, テキスト: '{button_text}'")
                            
                            # ボタンをスクロールして表示
                            driver.execute_script("arguments[0].scrollIntoView(true);", save_btn)
                            time.sleep(1)
                            
                            # クリック実行
                            driver.execute_script("arguments[0].click();", save_btn)
                            print("編集内容を保存しました")
                            save_btn_found = True
                            time.sleep(3)
                            break
                    
                    if save_btn_found:
                        break
                        
                except Exception as e:
                    continue
            
            if not save_btn_found:
                print("保存ボタンが見つかりませんでした。フォーム送信を試行します。")
                # 最後の手段として、フォーム送信を試行
                try:
                    forms = driver.find_elements(By.TAG_NAME, "form")
                    if forms:
                        print("フォームを直接送信します")
                        driver.execute_script("arguments[0].submit();", forms[0])
                        time.sleep(3)
                        save_btn_found = True
                except Exception as e:
                    print(f"フォーム送信でもエラー: {str(e)}")
            
            return save_btn_found
            
        except Exception as e:
            print(f"保存ボタンのクリックでエラー: {str(e)}")
            return False

    except Exception as e:
        print(f"追加情報編集処理でエラー: {str(e)}")
        return False

def edit_additional_info_form_only(driver, wait, data):
    """編集フォームでの追加情報入力のみ（直接編集ページにアクセスした場合）"""
    try:
        print("編集フォームでの追加情報入力を開始します...")
        
        # 編集ページに到達したことを確認（タイムアウトを延長）
        extended_wait = WebDriverWait(driver, 30)  # 30秒に延長
        try:
            extended_wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
            print("編集フォームを確認しました")
        except TimeoutException:
            print("フォーム要素が見つかりません。ページ内容を確認します...")
            print(f"現在のURL: {driver.current_url}")
            print(f"ページタイトル: {driver.title}")
            # フォームが見つからなくても処理を続行
            
        time.sleep(3)  # 追加の待機時間
        
        # CSVデータの値を確認
        print("=== CSVデータの値確認 ===")
        final_grade_value = data.get('final_grade', '')
        school_name_value = data.get('school_name', '')
        num_companies_value = data.get('number_of_companies_worked#2', '')
        
        print(f"final_grade (最終学歴): '{final_grade_value}' (型: {type(final_grade_value)})")
        print(f"school_name (卒業学校名): '{school_name_value}' (型: {type(school_name_value)})")
        print(f"number_of_companies_worked#2 (経験社数): '{num_companies_value}' (型: {type(num_companies_value)})")
        
        # 最終学歴フィールド（selectボックス）
        final_grade_str = str(final_grade_value).strip()
        if final_grade_str and final_grade_str != 'nan':
            print(f"最終学歴の入力を開始: '{final_grade_str}'")
            try:
                # 複数のセレクタで最終学歴フィールドを探す
                education_selectors = [
                    "select[name='lastEducation']",
                    "select[name='education']",
                    "select[name='finalEducation']",
                    "//select[contains(@name, 'education')]",
                    "//select[contains(@name, 'Education')]"
                ]
                
                last_education_select = None
                for selector in education_selectors:
                    try:
                        if selector.startswith("//"):
                            last_education_select = driver.find_element(By.XPATH, selector)
                        else:
                            last_education_select = driver.find_element(By.CSS_SELECTOR, selector)
                        if last_education_select:
                            print(f"最終学歴フィールドを発見: {selector}")
                            break
                    except:
                        continue
                
                if last_education_select:
                    select_obj = Select(last_education_select)
                    options = select_obj.options
                    print("最終学歴の選択肢:")
                    for opt in options:
                        print(f"  value='{opt.get_attribute('value')}', text='{opt.text}'")
                    
                    # より正確な教育レベルマッピング
                    education_mapping = {
                        "高卒": ["高卒", "1"],
                        "専門卒": ["専門卒", "2"], 
                        "短大卒": ["短大卒", "3"],
                        "大卒": ["大卒", "4"],
                        "大学卒": ["大卒", "4"],
                        "大学院卒": ["大学院卒", "5"],
                        "その他": ["その他", "6"]
                    }
                    
                    selected = False
                    
                    # 1. 完全一致を最初に試行
                    for option in options:
                        option_text = option.text.strip()
                        option_value = option.get_attribute('value')
                        if option_text == final_grade_str:
                            select_obj.select_by_value(option_value)
                            print(f"最終学歴で完全一致 '{option_text}' (value='{option_value}') を選択しました")
                            selected = True
                            break
                    
                    # 2. マッピングを使用したマッチング
                    if not selected and final_grade_str in education_mapping:
                        possible_values = education_mapping[final_grade_str]
                        for option in options:
                            option_text = option.text.strip()
                            option_value = option.get_attribute('value')
                            # テキストまたは値での一致をチェック
                            if option_text in possible_values or option_value in possible_values:
                                select_obj.select_by_value(option_value)
                                print(f"最終学歴でマッピング一致 '{option_text}' (value='{option_value}') を選択しました")
                                selected = True
                                break
                    
                    # 3. 部分一致での試行
                    if not selected:
                        for option in options:
                            option_text = option.text.strip()
                            option_value = option.get_attribute('value')
                            if final_grade_str in option_text:
                                select_obj.select_by_value(option_value)
                                print(f"最終学歴で部分一致 '{option_text}' (value='{option_value}') を選択しました")
                                selected = True
                                break
                    
                    if not selected:
                        print(f"'{final_grade_str}' に対応する選択肢が見つかりませんでした")
                        print("利用可能な選択肢と入力値を再確認してください")
                else:
                    print("最終学歴フィールドが見つかりませんでした")
                    
            except Exception as e:
                print(f"最終学歴の設定でエラー: {str(e)}")

        # 卒業学校名フィールド
        school_name_str = str(school_name_value).strip()
        if school_name_str and school_name_str != 'nan':
            print(f"卒業学校名の入力を開始: '{school_name_str}'")
            try:
                # 複数のセレクタで学校名フィールドを探す
                school_selectors = [
                    "input[name='schoolName']",
                    "input[name='school']",
                    "input[name='graduationSchool']",
                    "//input[contains(@name, 'school')]",
                    "//input[contains(@name, 'School')]"
                ]
                
                school_name_field = None
                for selector in school_selectors:
                    try:
                        if selector.startswith("//"):
                            school_name_field = driver.find_element(By.XPATH, selector)
                        else:
                            school_name_field = driver.find_element(By.CSS_SELECTOR, selector)
                        if school_name_field:
                            print(f"卒業学校名フィールドを発見: {selector}")
                            break
                    except:
                        continue
                
                if school_name_field:
                    school_name_field.clear()
                    school_name_field.send_keys(school_name_str)
                    print(f"卒業学校名に '{school_name_str}' を入力しました")
                else:
                    print("卒業学校名フィールドが見つかりませんでした")
            except Exception as e:
                print(f"卒業学校名の設定でエラー: {str(e)}")

        # 経験社数フィールド
        num_companies_str = str(num_companies_value).strip()
        if num_companies_str and num_companies_str != 'nan':
            print(f"経験社数の入力を開始: '{num_companies_str}'")
            try:
                # 複数のセレクタで経験社数フィールドを探す
                companies_selectors = [
                    "input[name='numberOfCompaniesExperienced']",
                    "input[name='companiesExperienced']",
                    "input[name='companyCount']",
                    "//input[contains(@name, 'companies')]",
                    "//input[contains(@name, 'Companies')]",
                    "//input[contains(@name, 'experience')]"
                ]
                
                num_companies_field = None
                for selector in companies_selectors:
                    try:
                        if selector.startswith("//"):
                            num_companies_field = driver.find_element(By.XPATH, selector)
                        else:
                            num_companies_field = driver.find_element(By.CSS_SELECTOR, selector)
                        if num_companies_field:
                            print(f"経験社数フィールドを発見: {selector}")
                            break
                    except:
                        continue
                
                if num_companies_field:
                    num_companies_field.clear()
                    num_companies_field.send_keys(num_companies_str)
                    print(f"経験社数に '{num_companies_str}' を入力しました")
                else:
                    print("経験社数フィールドが見つかりませんでした")
            except Exception as e:
                print(f"経験社数の設定でエラー: {str(e)}")

        print("追加情報の入力処理が完了しました")
        
        # 保存ボタンをクリック
        print("保存ボタンを探してクリックします...")
        try:
            save_btn_selectors = [
                "//button[@type='submit' and contains(text(), '保存')]",
                "//button[contains(@class, 'MuiButton') and contains(text(), '保存')]",
                "//button[contains(text(), '更新')]",
                "//button[contains(text(), '送信')]", 
                "//button[contains(text(), 'Save')]",
                "//button[contains(text(), 'Update')]",
                "button[type='submit']",
                "form button[type='submit']",
                ".MuiButton-root[type='submit']"
            ]
            
            save_btn_found = False
            for selector in save_btn_selectors:
                try:
                    if selector.startswith("//"):
                        save_btns = driver.find_elements(By.XPATH, selector)
                    else:
                        save_btns = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for save_btn in save_btns:
                        if save_btn and save_btn.is_displayed() and save_btn.is_enabled():
                            button_text = save_btn.text.strip()
                            print(f"保存ボタンを発見: {selector}, テキスト: '{button_text}'")
                            
                            # ボタンをスクロールして表示
                            driver.execute_script("arguments[0].scrollIntoView(true);", save_btn)
                            time.sleep(1)
                            
                            # クリック実行
                            driver.execute_script("arguments[0].click();", save_btn)
                            print("編集内容を保存しました")
                            save_btn_found = True
                            time.sleep(3)
                            break
                    
                    if save_btn_found:
                        break
                        
                except Exception as e:
                    continue
            
            if not save_btn_found:
                print("保存ボタンが見つかりませんでした。")
                return False
            else:
                return True
                
        except Exception as e:
            print(f"保存ボタンのクリックでエラー: {str(e)}")
            return False

    except Exception as e:
        print(f"編集フォームでの追加情報入力でエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def process_job_seeker(driver, wait, row, row_index, assignee_id):
    """求職者1件の完全な処理（登録 + 追加情報編集）"""
    try:
        print(f"\n=== 求職者 {row['name']} の処理を開始 ===")
        
        # ステップ1: 基本情報の登録
        registration_success, job_seeker_id = register_job_seeker(driver, wait, row, assignee_id)
        
        if not registration_success:
            print(f"❌ 求職者 {row['name']} の登録に失敗しました。処理を終了します。")
            return {
                'name': row['name'],
                'furigana': row['furigana'],
                'birthYear': row['birthyear'],
                'birthMonth': row['birthmonth'],
                'birthDay': row['birthday'],
                'postal': row.get('postal', ''),
                'address': row['address'],
                'phone': row['phone'],
                'email': row['email'],
                'license': row.get('license', ''),
                'education': row.get('education', ''),
                'folder_id': row.get('folder_id', ''),
                '転記日時': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '登録結果': '失敗',
                '追加情報編集結果': '未実行',
                '担当者': assignee_id
            }
        
        # ステップ2: 追加情報の編集
        print("\n--- 追加情報編集フェーズに移行 ---")
        time.sleep(2)  # 画面遷移のための待機
        
        # 登録成功時にjob_seeker_idがある場合は直接編集ページにアクセス
        additional_info_success = False
        if job_seeker_id:
            print(f"求職者ID {job_seeker_id} の編集ページに直接アクセスを試行します...")
            try:
                edit_url = f"https://circus-job.com/job-seekers/{job_seeker_id}/edit"
                driver.get(edit_url)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(3)
                
                # ページタイトルをチェック
                page_title = driver.title
                if "ページが見つかりませんでした" not in page_title and "404" not in page_title:
                    print("編集ページに直接アクセス成功")
                    additional_info_success = edit_additional_info_form_only(driver, wait, row)
                else:
                    print("直接アクセスに失敗。一覧経由で試行します。")
                    additional_info_success = edit_additional_info(driver, wait, row)
            except Exception as e:
                print(f"直接アクセスでエラー: {str(e)}。一覧経由で試行します。")
                additional_info_success = edit_additional_info(driver, wait, row)
        else:
            additional_info_success = edit_additional_info(driver, wait, row)
        
        additional_info_result = '成功' if additional_info_success else '失敗'
        
        print(f"✅ 求職者 {row['name']} の全処理が完了しました。")
        print(f"   登録結果: 成功")
        print(f"   追加情報編集結果: {additional_info_result}")
        
        return {
            'name': row['name'],
            'furigana': row['furigana'],
            'birthYear': row['birthyear'],
            'birthMonth': row['birthmonth'],
            'birthDay': row['birthday'],
            'postal': row.get('postal', ''),
            'address': row['address'],
            'phone': row['phone'],
            'email': row['email'],
            'license': row.get('license', ''),
            'education': row.get('education', ''),
            'folder_id': row.get('folder_id', ''),
            '転記日時': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '登録結果': '成功',
            '追加情報編集結果': additional_info_result,
            '担当者': assignee_id
        }
        
    except Exception as e:
        print(f"求職者 {row['name']} の処理中にエラーが発生しました: {str(e)}")
        return {
            'name': row['name'],
            'furigana': row['furigana'],
            'birthYear': row['birthyear'],
            'birthMonth': row['birthmonth'],
            'birthDay': row['birthday'],
            'postal': row.get('postal', ''),
            'address': row['address'],
            'phone': row['phone'],
            'email': row['email'],
            'license': row.get('license', ''),
            'education': row.get('education', ''),
            'folder_id': row.get('folder_id', ''),
            '転記日時': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '登録結果': 'エラー',
            '追加情報編集結果': 'エラー',
            '担当者': assignee_id
        }

def main():
    """メイン処理"""
    all_registration_data = []
    
    driver = create_driver()
    try:
        wait = WebDriverWait(driver, 20)
        
        # ログイン処理
        if not login_to_circus(driver, wait):
            print("ログインに失敗しました。処理を終了します。")
            return
        
        # CSVファイルの取得
        csv_files = get_s3_csv_files()
        if not csv_files:
            print("処理対象のCSVファイルがありません。")
            return
        
        print(f"処理対象のCSVファイル数: {len(csv_files)}")
        
        for csv_file in csv_files:
            print(f"\n=== CSVファイル処理開始: {csv_file} ===")
            
            df = get_csv_from_s3(csv_file)
            if df is None:
                print(f"CSVファイル {csv_file} の取得に失敗しました。次のファイルに進みます。")
                continue
            
            print(f"CSVファイルの行数: {len(df)}")
            
            # データの処理（全データを処理）
            for i, (index, row) in enumerate(df.iterrows()):
                print(f"\n=== 行 {index + 1} の処理を開始 ===")
                
                # 担当者IDの取得
                person_in_charge = row.get('person_in_charge', None)
                assignee_name, assignee_id = get_assignee_id_from_person_in_charge(person_in_charge)
                
                if assignee_id is None:
                    print(f"担当者IDの取得に失敗しました。行 {index + 1} をスキップします。")
                    continue
                
                # 求職者の完全処理（登録 + 追加情報編集）
                result = process_job_seeker(driver, wait, row, index, assignee_id)
                all_registration_data.append(result)
                
                # 各処理間の待機
                time.sleep(3)
        
        # 結果の保存
        if all_registration_data:
            print(f"\n=== すべての処理が完了しました。{len(all_registration_data)}件のデータをS3に保存します ===")
            if save_to_s3(all_registration_data):
                print("すべての登録データをS3に正常に保存しました。")
            else:
                print("登録データのS3保存に失敗しました。")
        else:
            print("保存する登録データがありません。")
            
    except Exception as e:
        print(f"メイン処理でエラーが発生しました: {str(e)}")
        
    finally:
        print("処理が完了しました。ブラウザを終了します。")
        driver.quit()

if __name__ == "__main__":
    main()
