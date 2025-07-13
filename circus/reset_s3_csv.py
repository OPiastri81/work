import boto3
import pandas as pd
import io
from datetime import datetime

# AWS認証情報は環境変数から読み込み
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION を環境変数に設定してください
import os

def reset_s3_csv():
    try:
        s3_client = boto3.client('s3')
        bucket_name = 'dev1-randd'
        key = 'register-circus/output_data/output_multi_new.csv'
        
        # S3からCSVファイルを取得
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        csv_content = response['Body'].read().decode('utf-8')
        df = pd.read_csv(io.StringIO(csv_content))
        
        print('=== 更新前のデータ ===')
        print(f'比較結果: {df["比較結果"].iloc[0]}')
        
        # 比較結果列をリセット
        df['比較結果'] = ''
        df['転記日時'] = ''
        
        # CSVデータをS3にアップロード
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=csv_buffer.getvalue().encode('utf-8'),
            ContentType='text/csv'
        )
        
        print('=== 更新後のデータ ===')
        print(f'比較結果: "{df["比較結果"].iloc[0]}"')
        print('S3のCSVファイルをリセットしました。再度登録処理を実行できます。')
        
    except Exception as e:
        print(f'エラーが発生しました: {str(e)}')

if __name__ == "__main__":
    reset_s3_csv() 