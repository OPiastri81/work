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

def create_driver():
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')  # デバッグ用にヘッドレスを無効化
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
    options.add_argument('--user-data-dir=/tmp/chrome-debug')
    options.add_argument('--remote-debugging-port=9222')
    driver = webdriver.Chrome(options=options)
    return driver

def extract_prefecture(address):
    prefecture_pattern = r'(.+?[都道府県])'
    match = re.search(prefecture_pattern, address)
    if match:
        return match.group(1).strip()
    return None

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

assignee_map = {
    "五十嵐": {"name": "五十嵐 翔", "id": "3665"},
    "吉澤": {"name": "吉澤　亜沙美", "id": "3682"},
    "家治川": {"name": "家治川 輝", "id": "5657"},
    "中東": {"name": "中東貴洋", "id": "5788"},
    "飯田": {"name": "飯田常仁", "id": "19552"},
    "LIF 採用サポート": {"name": "株式会社LIF 採用サポート", "id": "21049"},
    "久保": {"name": "久保翔一", "id": "21351"},
    "LIF 採用サポート02": {"name": "株式会社LIF 採用サポート02", "id": "21554"},
    "松本": {"name": "松本秀香", "id": "22689"}
}

def get_csv_from_s3(s3_key):
    try:
        s3_client = boto3.client('s3')
        bucket_name = 'dev1-randd'
        
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        csv_content = response['Body'].read().decode('utf-8')
        df = pd.read_csv(io.StringIO(csv_content))
        print(f"S3からCSVファイルを正常に取得しました: s3://{bucket_name}/{s3_key}")
        
        if 'person_in_charge' in df.columns:
            print("person_in_charge列を確認しました")
        else:
            print("警告: person_in_charge列が見つかりません")
            
        return df
        
    except Exception as e:
        print(f"S3からCSVファイルの取得中にエラーが発生しました: {str(e)}")
        return None

def get_s3_csv_files():
    try:
        csv_files = ['register-circus/output_data/output_multi_new.csv']
        print(f"指定されたCSVファイル: {csv_files[0]}")
        return csv_files
        
    except Exception as e:
        print(f"CSVファイル一覧の取得中にエラーが発生しました: {str(e)}")
        return []

def get_assignee_from_dataframe(df):
    try:
        if 'person_in_charge' not in df.columns:
            print("person_in_charge列が見つかりません")
            return None, None
        
        person_in_charge_values = df['person_in_charge'].dropna().unique()
        if len(person_in_charge_values) == 0:
            print("person_in_charge列に値がありません")
            return None, None
        
        assignee_name = person_in_charge_values[0]
        print(f"担当者名: {assignee_name}")
        
        if assignee_name in assignee_map:
            assignee_id = assignee_map[assignee_name]['id']
            return assignee_name, assignee_id
        else:
            print(f"担当者 '{assignee_name}' に対応するIDが見つかりません")
            return assignee_name, None
            
    except Exception as e:
        print(f"担当者情報の取得中にエラーが発生しました: {str(e)}")
        return None, None

def save_to_s3_by_assignee(registration_data_list):
    try:
        s3_client = boto3.client('s3')
        bucket_name = 'dev1-randd'
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'registration_multi_result.csv'
        
        csv_buffer = io.StringIO()
        fieldnames = ['name', 'furigana', 'birthYear', 'birthMonth', 'birthDay', 'postal', 'address', 'phone', 'email', 'license', 'education', '転記日時', '比較結果', '担当者']
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for data in registration_data_list:
            writer.writerow(data)
        
        s3_key = f'register-circus/result/{filename}'
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=csv_buffer.getvalue().encode('utf-8'),
            ContentType='text/csv'
        )
        
        print(f"登録データ {len(registration_data_list)}件をS3に保存しました: s3://{bucket_name}/{s3_key}")
        return True
        
    except Exception as e:
        print(f"S3への保存中にエラーが発生しました: {str(e)}")
        return False

def update_csv_status_in_s3(s3_key, row_index, registration_status="1"):
    try:
        s3_client = boto3.client('s3')
        bucket_name = 'dev1-randd'
        result_key = 'register-circus/result/registration_multi_result.csv'
        
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=result_key)
            csv_content = response['Body'].read().decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_content))
        except:
            print("結果ファイルが存在しないため、新規作成します")
            df = pd.DataFrame(columns=['name', 'furigana', 'birthYear', 'birthMonth', 'birthDay', 'postal', 'address', 'phone', 'email', 'license', 'education', '転記日時', '比較結果', '担当者'])
        
        df.at[row_index, '比較結果'] = registration_status
        df.at[row_index, '転記日時'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=result_key,
            Body=csv_buffer.getvalue().encode('utf-8'),
            ContentType='text/csv'
        )
        
        print(f"S3の結果ファイル {result_key} の行 {row_index + 1} の比較結果を更新しました")
        return True
        
    except Exception as e:
        print(f"S3の結果ファイルの更新中にエラーが発生しました: {str(e)}")
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

def register_job_seeker_with_create(driver, data, row_index, assignee_id, s3_key, skip_login=False):
    try:
        if not skip_login:
            print("サイトにアクセスします...")
            driver.get("https://circus-job.com/login")
            
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(5)
            
            print(f"現在のURL: {driver.current_url}")
            print(f"ページタイトル: {driver.title}")
            
            try:
                login_form = wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
                print("ログインフォームを確認しました")
            except Exception as e:
                print(f"ログインフォームが見つかりません: {str(e)}")
                print("ページのソース:", driver.page_source[:2000])
                raise

            print("ログイン処理を開始します...")
            print("メールアドレスを入力します...")
            try:
                email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
                email_input.clear()
                email_input.send_keys(os.environ["email"])
            except Exception as e:
                print(f"メールアドレス入力フィールドが見つかりません: {str(e)}")
                print("現在のページのURL:", driver.current_url)
                print("ページのソース:", driver.page_source[:1000])
                raise
            
            print("パスワードを入力します...")
            password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_input.send_keys(os.environ["password"])
            
            print("ログインボタンをクリックします...")
            login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'ログイン')]")))
            login_button.click()
            time.sleep(2)

            print("フォーム送信ボタンをクリックします...")
            try:
                modal = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "MuiDialog-container")))
                close_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='close']")))
                close_button.click()
                time.sleep(2)
            except Exception as e:
                print(f"モーダルダイアログの処理中にエラーが発生しました: {str(e)}")
                print("モーダルが見つからない場合は続行します。")

            submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            driver.execute_script("arguments[0].click();", submit_button)
            time.sleep(5)

            print("ログイン確認ポップアップを処理します...")
            try:
                confirm_button = wait.until(EC.element_to_be_clickable((
                    By.CSS_SELECTOR, 
                    "button.MuiButtonBase-root.MuiButton-root.MuiButton-contained.MuiButton-containedConversion[type='submit'][form='loginForm']"
                )))
                confirm_button.click()
                time.sleep(3)
            except Exception as e:
                print(f"ログイン確認ポップアップの処理中にエラーが発生しました: {str(e)}")
                print("確認ポップアップが見つからない場合は続行します。")

            print("ログイン後のページ遷移を待機します...")
            try:
                wait.until(EC.url_changes("https://circus-job.com/login"))
                time.sleep(3)
                
                wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'MuiDrawer-root')]")))
                print("ログイン成功を確認しました")
            except Exception as e:
                print(f"ログイン後のページ遷移でエラーが発生しました: {str(e)}")
                print("現在のURL:", driver.current_url)
                raise
        else:
            print("ログイン処理をスキップします...")
            wait = WebDriverWait(driver, 20)

        print("求職者登録ページに移動します...")
        try:
            dialogs = driver.find_elements(By.CLASS_NAME, "MuiDialog-container")
            if dialogs:
                print("ダイアログを処理します...")
                close_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='close']")))
                close_button.click()
                time.sleep(2)
        except Exception as e:
            print(f"ダイアログの処理中にエラーが発生しました: {str(e)}")
            print("ダイアログが見つからない場合は続行します。")

        try:
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
            
            print("メニューが開いたことを確認します...")
            menu_open_selectors = [
                "//div[contains(@class, 'MuiDrawer-root') and contains(@class, 'MuiDrawer-open')]",
                "//div[contains(@class, 'MuiDrawer-root')]//div[contains(@class, 'MuiDrawer-paper')]",
                "//div[contains(@class, 'MuiDrawer-root')]//nav"
            ]
            
            menu_opened = False
            for selector in menu_open_selectors:
                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    menu_opened = True
                    print(f"メニューが開いたことを確認しました: {selector}")
                    break
                except:
                    continue
            
            if not menu_opened:
                print("メニューの開閉状態を確認できませんでしたが、処理を続行します")
            
        except Exception as e:
            print(f"メニューボタンの処理中にエラーが発生しました: {str(e)}")
            print("現在のURL:", driver.current_url)
            print("ページのソース:", driver.page_source[:1000])
            raise

        try:
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
        except Exception as e:
            print(f"求職者メニューの処理中にエラーが発生しました: {str(e)}")
            print("現在のURL:", driver.current_url)
            print("ページのソース:", driver.page_source[:1000])
            raise

        try:
            print("求職者登録リンクを探しています...")
            register_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/register/job-seeker')]")))
            driver.execute_script("arguments[0].click();", register_link)
            time.sleep(3)
        except Exception as e:
            print(f"求職者登録リンクの処理中にエラーが発生しました: {str(e)}")
            print("現在のURL:", driver.current_url)
            print("ページのソース:", driver.page_source[:1000])
            raise

        print("基本情報を入力します...")
        driver.find_element(By.NAME, "name").send_keys(data['name'])
        driver.find_element(By.NAME, "nameRuby").send_keys(data['furigana'])
        driver.find_element(By.NAME, "email").send_keys(data['email'])
        driver.find_element(By.NAME, "phone").send_keys(data['phone'])
        driver.find_element(By.NAME, "birthday.year").send_keys(data['birthYear'])
        driver.find_element(By.NAME, "birthday.month").send_keys(data['birthMonth'])
        driver.find_element(By.NAME, "birthday.day").send_keys(data['birthDay'])
        
        print("都道府県を選択します...")
        prefecture = extract_prefecture(data['address'])
        if prefecture:
            prefecture_element = driver.find_element(By.NAME, "prefecture")
            prefecture_select = Select(prefecture_element)
            if prefecture in prefecture_map:
                prefecture_value = prefecture_map[prefecture]
                prefecture_select.select_by_value(prefecture_value)
                print(f"都道府県: '{prefecture}' を選択しました。")
            else:
                print(f"'{prefecture}' は有効な都道府県ではありません。")
        time.sleep(1)

        print("担当者を選択します... (担当者ID: {})".format(assignee_id))
        try:
            assignee_select = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[name='assignees[0]']")))
            print("担当者選択ドロップダウンを見つけました: select[name='assignees[0]']")
            assignee_dropdown = Select(assignee_select)
            assignee_dropdown.select_by_value(str(assignee_id))
            print("担当者ID {} を選択しました".format(assignee_id))
        except Exception as e:
            print(f"担当者選択中にエラーが発生しました: {str(e)}")
            raise

        time.sleep(1)
        print("『作成する』ボタンをクリックします...")
        try:
            create_button_selectors = [
                "button.MuiButtonBase-root.MuiButton-root.MuiButton-contained.MuiButton-containedSecondary.MuiButton-sizeMedium.MuiButton-containedSizeMedium.FormSubmitButton-buttonWidth[type='submit']",
                "button.FormSubmitButton-buttonWidth[type='submit']",
                "button.MuiButton-containedSecondary[type='submit']",
                "//button[@type='submit' and contains(., '作成する')]",
                "//button[contains(@class, 'MuiButton-containedSecondary') and contains(., '作成する')]",
                "//button[contains(@class, 'FormSubmitButton-buttonWidth') and contains(., '作成する')]",
                "//button[contains(text(), '作成する')]",
                "button[type='submit']"
            ]
            create_button = None
            for selector in create_button_selectors:
                try:
                    print(f"セレクタを試行中: {selector}")
                    if selector.startswith("//"):
                        create_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    else:
                        create_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    if create_button:
                        print(f"『作成する』ボタンを見つけました: {selector}")
                        button_text = create_button.text
                        print(f"ボタンのテキスト: {button_text}")
                        if '作成する' in button_text:
                            print("正しいボタンを確認しました")
                            break
                        else:
                            print("ボタンのテキストが「作成する」ではありません")
                            create_button = None
                            continue
                except Exception as e:
                    print(f"セレクタ {selector} でボタンが見つかりませんでした: {str(e)}")
                    continue
            if not create_button:
                print("ページのソースからボタンを探します...")
                page_source = driver.page_source
                if '作成する' in page_source:
                    print("ページに「作成する」テキストが存在します")
                    all_buttons = driver.find_elements(By.TAG_NAME, "button")
                    print(f"ページ内のボタン数: {len(all_buttons)}")
                    for i, button in enumerate(all_buttons):
                        try:
                            button_text = button.text
                            button_type = button.get_attribute('type')
                            button_class = button.get_attribute('class')
                            print(f"ボタン {i}: テキスト='{button_text}', type='{button_type}', class='{button_class}'")
                            if '作成する' in button_text and button_type == 'submit':
                                print(f"ボタン {i} に「作成する」テキストを発見: {button_text}")
                                create_button = button
                                break
                        except Exception as e:
                            print(f"ボタン {i} の情報取得でエラー: {str(e)}")
                            continue
                if not create_button:
                    raise Exception("『作成する』ボタンが見つかりませんでした")
            print("『作成する』ボタンをクリックします...")
            driver.execute_script("arguments[0].scrollIntoView(true);", create_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", create_button)
            print("『作成する』ボタンをクリックしました。")
            time.sleep(5)
            print("ボタンクリック後の処理を確認します...")
            print("現在のURL:", driver.current_url)
        except Exception as e:
            print(f"『作成する』ボタンのクリックに失敗しました: {str(e)}")
            print("現在のページのURL:", driver.current_url)
            print("ページのソース（ボタン部分）:", driver.page_source[:3000])
            raise

        # 登録確認処理を追加
        registration_success, job_seeker_id = verify_registration(driver, data)
        
        if registration_success:
            print(f"✅ 求職者 {data['name']} の登録が完了しました。")
            registration_status = "1"
        else:
            print(f"❌ 求職者 {data['name']} の登録に失敗しました。")
            registration_status = "0"

        print("S3のCSVファイルの比較結果を更新します...")
        if update_csv_status_in_s3(s3_key, row_index, registration_status):
            print(f"求職者 {data['name']} の比較結果を正常に更新しました。")
        else:
            print(f"求職者 {data['name']} の比較結果の更新に失敗しました。")

        registration_data = {
            'name': data['name'],
            'furigana': data['furigana'],
            'birthYear': data['birthYear'],
            'birthMonth': data['birthMonth'],
            'birthDay': data['birthDay'],
            'postal': data.get('postal', ''),
            'address': data['address'],
            'phone': data['phone'],
            'email': data['email'],
            'license': data.get('license', ''),
            'education': data.get('education', ''),
            '転記日時': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '比較結果': registration_status,
            '担当者': assignee_id
        }
        
        global all_registration_data
        all_registration_data.append(registration_data)
        print(f"求職者 {data['name']} の登録データをリストに追加しました。")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        print("現在のページのURL:", driver.current_url)
        print("ページのソース:", driver.page_source[:500])
        raise

def main():
    global all_registration_data
    all_registration_data = []
    
    driver = create_driver()
    try:
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
            
            assignee_name, assignee_id = get_assignee_from_dataframe(df)
            if assignee_id is None:
                print(f"担当者IDの取得に失敗しました。CSVファイル {csv_file} をスキップします。")
                continue
            
            print(f"担当者: {assignee_name} (ID: {assignee_id})")
            
            print(f"CSVファイルの列名: {list(df.columns)}")
            print(f"CSVファイルの総行数: {len(df)}")
            
            # 比較結果列の値の分布を表示
            if '比較結果' in df.columns:
                print("比較結果列の値の分布:")
                print(df['比較結果'].value_counts())
                
                # 登録対象のデータを抽出
                unregistered_rows = df[df['比較結果'].isna() | (df['比較結果'] == '') | (df['比較結果'] == '""')]
                print(f"登録対象のデータ数: {len(unregistered_rows)}件")
                
                if unregistered_rows.empty:
                    print("登録対象のデータがありません。次のファイルに進みます。")
                    continue
                
                for i, (index, row) in enumerate(unregistered_rows.iterrows()):
                    print(f"\n=== 行 {index + 1} の処理を開始 ===")
                    skip_login = (i > 0)
                    register_job_seeker_with_create(driver, row, index, assignee_id, csv_file, skip_login)
                    time.sleep(2)
            else:
                print("比較結果列が存在しません。すべての行を処理します。")
                for i, (index, row) in enumerate(df.iterrows()):
                    print(f"\n=== 行 {index + 1} の処理を開始 ===")
                    skip_login = (i > 0)
                    register_job_seeker_with_create(driver, row, index, assignee_id, csv_file, skip_login)
                    time.sleep(2)
        
        if all_registration_data:
            print(f"\n=== すべての登録が完了しました。{len(all_registration_data)}件のデータをS3に保存します ===")
            if save_to_s3_by_assignee(all_registration_data):
                print("すべての登録データをS3に正常に保存しました。")
            else:
                print("登録データのS3保存に失敗しました。")
        else:
            print("保存する登録データがありません。")
            
    finally:
        print("処理が完了しました")
        driver.quit()

if __name__ == "__main__":
    main() 