import boto3
import pandas as pd
import io

# AWS認証情報は環境変数から読み込み
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION を環境変数に設定してください
import os

def check_s3_csv():
    try:
        s3_client = boto3.client('s3')
        bucket_name = 'dev1-randd'
        key = 'register-circus/output_data/output_new.csv'
        
        # S3からCSVファイルを取得
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        csv_content = response['Body'].read().decode('utf-8')
        
        # DataFrameとして読み込み
        df = pd.read_csv(io.StringIO(csv_content))
        
        print("=== S3のCSVファイルの内容 ===")
        print(f"行数: {len(df)}")
        print(f"列名: {list(df.columns)}")
        print("\n=== データの詳細 ===")
        print(df.to_string(index=False))
        
        print("\n=== 比較結果列の詳細 ===")
        for i, value in enumerate(df['比較結果']):
            print(f"行 {i+1}: '{value}' (型: {type(value)})")
            
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    check_s3_csv() 