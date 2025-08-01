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
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
    driver = webdriver.Chrome(options=options)
    return driver

def extract_prefecture(address):
    # 住所から都道府県を抽出
    prefecture_pattern = r'(.+?[都道府県])'
    match = re.search(prefecture_pattern, address)
    if match:
        return match.group(1).strip()
    return None

# 都道府県名とvalueのマッピング
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

def save_to_s3(registration_data):
    """登録データをS3にCSV形式で保存"""
    try:
        # S3クライアントの初期化
        s3_client = boto3.client('s3')
        
        # 現在の日時を取得してファイル名に使用
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'registration_result.csv'
        
        # CSVデータを作成
        csv_buffer = io.StringIO()
        fieldnames = ['name', 'furigana', 'birthYear', 'birthMonth', 'birthDay', 'postal', 'address', 'phone', 'email', 'license', 'education', '転記日時', '登録状況']
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        
        # ヘッダーを書き込み
        writer.writeheader()
        
        # データを書き込み
        writer.writerow(registration_data)
        
        # S3にアップロード
        bucket_name = 'dev1-randd'
        s3_key = f'register-circus/result/{filename}'
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=csv_buffer.getvalue().encode('utf-8'),
            ContentType='text/csv'
        )
        
        print(f"登録データをS3に保存しました: s3://{bucket_name}/{s3_key}")
        return True
        
    except Exception as e:
        print(f"S3への保存中にエラーが発生しました: {str(e)}")
        return False

def update_csv_status(csv_file_path, row_index, registration_status="1"):
    """CSVファイルの特定の行の登録状況と転記日時を更新"""
    try:
        # CSVファイルを読み込み
        df = pd.read_csv(csv_file_path)
        
        # 登録状況と転記日時を更新
        df.at[row_index, '登録状況'] = registration_status
        df.at[row_index, '転記日時'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # CSVファイルを保存
        df.to_csv(csv_file_path, index=False, encoding='utf-8')
        print(f"CSVファイルの行 {row_index + 1} の登録状況を更新しました")
        return True
        
    except Exception as e:
        print(f"CSVファイルの更新中にエラーが発生しました: {str(e)}")
        return False

def register_job_seeker(driver, data, csv_file_path, row_index):
    try:
        print("サイトにアクセスします...")
        driver.get("https://circus-job.com/")  # ログインページに直接アクセス
        
        # ページの読み込みを待機
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(5)  # 追加の待機時間

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
        # モーダルダイアログを待機して閉じる
        try:
            modal = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "MuiDialog-container")))
            close_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='close']")))
            close_button.click()
            time.sleep(2)
        except Exception as e:
            print(f"モーダルダイアログの処理中にエラーが発生しました: {str(e)}")
            print("モーダルが見つからない場合は続行します。")

        # フォーム送信ボタンをクリック
        submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        driver.execute_script("arguments[0].click();", submit_button)
        time.sleep(5)

        # ログイン確認ポップアップの処理
        print("ログイン確認ポップアップを処理します...")
        try:
            # 確認ポップアップの「ログインする」ボタンを探してクリック
            confirm_button = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, 
                "button.MuiButtonBase-root.MuiButton-root.MuiButton-contained.MuiButton-containedConversion[type='submit'][form='loginForm']"
            )))
            confirm_button.click()
            time.sleep(3)
        except Exception as e:
            print(f"ログイン確認ポップアップの処理中にエラーが発生しました: {str(e)}")
            print("確認ポップアップが見つからない場合は続行します。")

        # ログイン後のページ遷移を待機
        print("ログイン後のページ遷移を待機します...")
        try:
            # ログイン成功の確認
            wait.until(EC.url_changes("https://circus-job.com/login"))
            time.sleep(3)
            
            # ダッシュボードページの読み込みを待機
            wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'MuiDrawer-root')]")))
            print("ログイン成功を確認しました")
        except Exception as e:
            print(f"ログイン後のページ遷移でエラーが発生しました: {str(e)}")
            print("現在のURL:", driver.current_url)
            raise

        print("求職者登録ページに移動します...")
        # メニューを開く前にダイアログを処理
        try:
            # ダイアログが表示されているか確認
            dialogs = driver.find_elements(By.CLASS_NAME, "MuiDialog-container")
            if dialogs:
                print("ダイアログを処理します...")
                # ダイアログを閉じる
                close_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='close']")))
                close_button.click()
                time.sleep(2)
        except Exception as e:
            print(f"ダイアログの処理中にエラーが発生しました: {str(e)}")
            print("ダイアログが見つからない場合は続行します。")

        # メニューを開く
        try:
            print("メニューボタンを探しています...")
            # メニューボタンを探す（複数のセレクターを試す）
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
            
            # JavaScriptでクリック
            driver.execute_script("arguments[0].click();", menu_button)
            time.sleep(3)
            
            # メニューが開いたことを確認（複数の方法を試す）
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

        # 求職者メニューを探す
        try:
            print("求職者メニューを探しています...")
            # 複数のセレクターを試す
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
            
            # JavaScriptでクリック
            driver.execute_script("arguments[0].click();", job_seeker_button)
            time.sleep(3)
            
        except Exception as e:
            print(f"求職者メニューの処理中にエラーが発生しました: {str(e)}")
            print("現在のURL:", driver.current_url)
            print("ページのソース:", driver.page_source[:1000])
            raise

        # 求職者登録リンクを探す
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

        print(f"求職者 {data['name']} の登録が完了しました。")
        
        # 登録完了後、CSVファイルの登録状況を更新
        print("CSVファイルの登録状況を更新します...")
        if update_csv_status(csv_file_path, row_index, "1"):
            print(f"求職者 {data['name']} の登録状況を正常に更新しました。")
        else:
            print(f"求職者 {data['name']} の登録状況の更新に失敗しました。")
        
        # 登録完了後、S3にデータを保存
        print("登録データをS3に保存します...")
        registration_data = {
            'name': data['name'],
            'furigana': data['furigana'],
            'birthYear': data['birthYear'],
            'birthMonth': data['birthMonth'],
            'birthDay': data['birthDay'],
            'postal': data.get('postal', ''),  # postalが存在しない場合は空文字
            'address': data['address'],
            'phone': data['phone'],
            'email': data['email'],
            'license': data.get('license', ''),  # licenseが存在しない場合は空文字
            'education': data.get('education', ''),  # educationが存在しない場合は空文字
            '転記日時': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '登録状況': '1'
        }
        
        if save_to_s3(registration_data):
            print(f"求職者 {data['name']} の登録データをS3に正常に保存しました。")
        else:
            print(f"求職者 {data['name']} の登録データのS3保存に失敗しました。")

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        print("現在のページのURL:", driver.current_url)
        print("ページのソース:", driver.page_source[:500])  # 最初の500文字だけ表示
        raise  # エラーを再度発生させて、スタックトレースを表示

def main():
    csv_file_path = '/home/ec2-user/Output Data.csv'
    
    # CSVファイルを読み込み
    try:
        df = pd.read_csv(csv_file_path)
        print(f"CSVファイルを読み込みました: {len(df)} 行のデータ")
    except Exception as e:
        print(f"CSVファイルの読み込みに失敗しました: {str(e)}")
        return
    
    # 必要なカラムが存在するかチェック
    required_columns = ['name', 'furigana', 'birthYear', 'birthMonth', 'birthDay', 'postal', 'address', 'phone', 'email', 'license', 'education', '転記日時', '登録状況']
    
    # 不足しているカラムを追加
    for column in required_columns:
        if column not in df.columns:
            df[column] = ''
            print(f"カラム '{column}' を追加しました")
    
    # CSVファイルを保存（カラム追加後）
    df.to_csv(csv_file_path, index=False, encoding='utf-8')
    print("CSVファイルを更新しました")
    
    # 登録状況が空の行のみを処理
    unregistered_rows = df[df['登録状況'].isna() | (df['登録状況'] == '')]
    print(f"未登録の行数: {len(unregistered_rows)}")
    
    if len(unregistered_rows) == 0:
        print("登録対象のデータがありません。")
        return
    
    driver = create_driver()
    try:
        for index, row in unregistered_rows.iterrows():
            print(f"\n=== 行 {index + 1} の処理を開始 ===")
            print(f"名前: {row['name']}")
            
            # データを辞書形式に変換
            data = row.to_dict()
            
            # 登録処理を実行
            register_job_seeker(driver, data, csv_file_path, index)
            time.sleep(2)  # 次の登録までの待機時間
            
    finally:
        print("処理が完了しました")
        driver.quit()

if __name__ == "__main__":
    main() 