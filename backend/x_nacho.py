import requests
import pandas as pd
from datetime import datetime

class TwitterAPI:
    def __init__(self, bearer_token):
        self.bearer_token = bearer_token
        self.headers = {"Authorization": f"Bearer {bearer_token}"}

    def get_user_id(self, username):
        url = f"https://api.twitter.com/2/users/by/username/{username}"
        response = requests.get(url, headers=self.headers)
        return response.json()["data"]["id"] if response.status_code == 200 else None

    def get_tweets(self, user_id, max_results=10):
        url = f"https://api.twitter.com/2/users/{user_id}/tweets"
        params = {
            "max_results": max_results,
            "tweet.fields": "id,text,created_at,public_metrics,conversation_id",
            "exclude": "retweets,replies"
        }
        response = requests.get(url, headers=self.headers, params=params)
        return response.json() if response.status_code == 200 else None

    def get_replies_to_tweet(self, conversation_id, max_results=10):
        url = "https://api.twitter.com/2/tweets/search/recent"
        params = {
            "query": f"conversation_id:{conversation_id}",  # Corregido: "conversation_id" -> "conversation_id"
            "max_results": max_results,
            "tweet.fields": "author_id,text,created_at,public_metrics"
        }
        response = requests.get(url, headers=self.headers, params=params)
        return response.json() if response.status_code == 200 else None

    def get_all_data(self, username):
        user_id = self.get_user_id(username)
        if not user_id:
            return None

        tweets = self.get_tweets(user_id, max_results=5)
        if not tweets or "data" not in tweets:
            return None

        current_year = datetime.now().year
        all_data = []

        for tweet in tweets["data"]:
            tweet_date = datetime.strptime(tweet["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
            if tweet_date.year != current_year:
                continue

            replies = self.get_replies_to_tweet(tweet["conversation_id"])
            replies_data = replies["data"] if replies and "data" in replies else []

            all_data.append({
                "tweet_id": tweet["id"],
                "tweet_text": tweet["text"],
                "tweet_date": tweet["created_at"],
                "tweet_likes": tweet["public_metrics"]["like_count"],
                "tweet_retweets": tweet["public_metrics"]["retweet_count"],
                "reply_count": len(replies_data),
                "replies": replies_data
            })

        return all_data

def save_to_csv(data, filename="tweets_con_respuestas.csv"):
    # Preparamos los datos para el CSV
    rows = []
    for tweet in data:
        for reply in tweet["replies"]:
            rows.append({
                "tweet_id": tweet["tweet_id"],
                "tweet_text": tweet["tweet_text"],
                "tweet_date": tweet["tweet_date"],
                "tweet_likes": tweet["tweet_likes"],
                "tweet_retweets": tweet["tweet_retweets"],
                "reply_author_id": reply["author_id"],
                "reply_text": reply["text"],
                "reply_date": reply["created_at"],
                "reply_likes": reply["public_metrics"]["like_count"]
            })
    
    # Creamos un DataFrame y lo guardamos como CSV
    df = pd.DataFrame(rows)
    df.to_csv(filename, index=False, encoding="utf-8-sig")  # "utf-8-sig" para caracteres especiales
    print(f"✅ Datos guardados en {filename}")

# Ejemplo de uso
if __name__ == "__main__":
    BEARER_TOKEN = 'AAAAAAAAAAAAAAAAAAAAAOk50QEAAAAArs94z47Qrvz7IfUbuyv%2F8XGnAOI%3DhD8SihRdIPkj1vzBIGG8YUCGANNq09LVNI1ulkCDfjeiNEdbYL'  # Reemplaza con tu token
    twitter = TwitterAPI(BEARER_TOKEN)
    data = twitter.get_all_data("PlataCard")  # Cambia la cuenta si lo necesitas

    if data:
        save_to_csv(data)
    else:
        print("No se encontraron datos para exportar.")