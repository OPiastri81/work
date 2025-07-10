#!/bin/bash

# ログディレクトリの作成
mkdir -p /home/ec2-user/logs

# 既存のcronジョブを削除（同じスクリプトが存在する場合）
crontab -l | grep -v "register_with_status_create_button_assignee_debug.py" | crontab -

# 新しいcronジョブを追加（30分に1回実行）
(crontab -l 2>/dev/null; echo "0,30 * * * * cd /home/ec2-user && export email=\"lif_support_hr@lifinc.co.jp\" && export password=\"LifSupport01\" && python3 register_with_status_create_button_assignee_debug.py >> /home/ec2-user/logs/registration.log 2>&1") | crontab -

echo "cronジョブが設定されました。30分に1回実行されます。"
echo "現在のcronジョブ一覧:"
crontab -l 