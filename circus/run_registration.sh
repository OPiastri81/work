#!/bin/bash

# ログファイルの設定
LOG_DIR="/home/ec2-user/logs"
LOG_FILE="$LOG_DIR/registration_$(date +%Y%m%d_%H%M%S).log"

# ログディレクトリの作成
mkdir -p $LOG_DIR

# 環境変数の設定（実際の値に変更してください）
export email="your-email@example.com"
export password="your-password"

# 作業ディレクトリの移動
cd /home/ec2-user

# 実行開始ログ
echo "$(date): register_with_status_create_button.py の実行を開始します" >> $LOG_FILE

# Pythonスクリプトの実行
python3 register_with_status_create_button.py >> $LOG_FILE 2>&1

# 実行終了ログ
echo "$(date): register_with_status_create_button.py の実行が完了しました" >> $LOG_FILE
echo "----------------------------------------" >> $LOG_FILE 