import requests
from bs4 import BeautifulSoup
import json
import pymsteams
from discordwebhook import Discord
import os
import toml
import time

def my_filter(t):
    return t.name == "div" and t.has_attr("data-questions")

# peingへのセッション
session = requests.session()

# ログインページを表示してトークンを取得
login_url1 = "https://peing.net/ja/acc/login?"
r1 = session.get(login_url1)
soup = BeautifulSoup(r1.text, "html.parser")
elem_authenticity_token = soup.find_all("input", attrs={"type": "hidden", "name": "authenticity_token"})

# Webhook URLやID情報を読み込む
tomlPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "settings.toml")

with open(tomlPath, encoding="utf-8") as f:
    obj = toml.load(f)
    ID = obj["id"]
    PASS = obj["pass"]
    TEAMS_WEBHOOK = obj["teams_webhook"]
    DISCORD_WEBHOOK = obj["discord_webhook"]

discord = Discord(url=DISCORD_WEBHOOK)

# ログイン情報
login_info = {
    "account": ID,
    "password": PASS,
    "authenticity_token": elem_authenticity_token[0].get("value")
}

# ログインしてセッションを作成
login_url = "https://peing.net/ja/acc/login_confirm"
res = session.post(login_url, data=login_info)
res.raise_for_status()  # エラーならここで例外を発生させる

# 回答済みの質問IDリストを読み込む
questionsPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "questions.csv")

with open(questionsPath, mode="r") as f:
    hashSet = set(f.read().strip().split(","))

# ページ毎に質問を取得
for i in range(103):
    page = i + 1
    # 未回答のページに移動
    page_url = f"https://peing.net/ja/box?page={page}"
    res = session.get(page_url)
    time.sleep(0.5)
    soup = BeautifulSoup(res.text, "html.parser")

    # 質問が存在すれば実行
    if res.status_code // 100 == 2:

        # 質問を取得
        data_questions = soup.find_all(my_filter)[0]
        data_questions_json = json.loads(data_questions.attrs["data-questions"])

        # 取得した質問毎に処理
        for data_questions in data_questions_json:
            body = data_questions.get("body")
            uuid_hash = data_questions.get("uuid_hash")
            question_url = "https://peing.net/ja/q/" + uuid_hash

            # 未通知の場合通知を行う
            if uuid_hash not in hashSet:
                hashSet.add(uuid_hash)

                # teamsへの通知処理部
                teams_obj = pymsteams.connectorcard(TEAMS_WEBHOOK)
                message = f"新しい質問が来ています。([リンク]({question_url}))\n\n" \
                          "\--------------------\n\n" \
                          f"{body}\n\n"
                teams_obj.text(message)
                teams_obj.send()

            # discordへの通知処理部
                discord.post(
                    username="Peing-質問箱-通知bot",
                    avatar_url="https://user-images.githubusercontent.com/82703534/216120021-e3315452-a9b6-4a88-9d03-d026764c80ef.png",
                    embeds=[{"title": "新しい質問が来ています。", "description": f"{body}\n\n URL → {question_url}"}]
                )

    # 質問がなければ回答済みリストにIDを追加して終了
    else:
        # 送信した質問のuuid_hashを保持
        with open(questionsPath, mode="w") as f:
          f.write(",".join(list(hashSet)))
        break
