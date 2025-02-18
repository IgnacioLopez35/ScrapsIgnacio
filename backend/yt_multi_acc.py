import os
import pandas as pd
import unicodedata
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuración de la API
API_KEY = "AIzaSyADGFi_IiZWqERHs8nB-W6uzgpt4Jkyg-g"
CHANNEL_IDS = [
    "UCwTKziMccZoy631_wbxk8wg",  # Disney Studios LA
    "UC1bOh2t2cLNzGvlRrD5fY-Q",  # Videocine
    "UC_2POp0ILf48h6T5JqsiMBw",  # Sony Pictures México
    "UCaFEAxeTC-Y_0AFthe0Xmwg",  # Diamond Films México
    "UCvC4D8onUfXzvjTOM-dBfEA",  # Universal Pictures México
    "UCu-cVVMn41qUA-pwdEhNqhg",  # Warner Bros. Pictures Latinoamérica
    "UC1bOh2t2cLNzGvlRrD5fY-Q"   # Corazón Films
]
START_DATE = "2024-01-01"
END_DATE = "2024-12-31"

youtube = build("youtube", "v3", developerKey=API_KEY)

def clean_text(text):
    if isinstance(text, str):
        text = text.encode("utf-8", "ignore").decode("utf-8", "ignore")  # Ignorar bytes no válidos
        text = unicodedata.normalize("NFKC", text)  # Normalizar caracteres Unicode
        text = re.sub(r'[^\x20-\x7E]', '', text)  # Eliminar caracteres no imprimibles
        return text.strip()
    return text

def get_all_videos(channel_id, start_date, end_date):
    videos = []
    next_page_token = None
    
    while True:
        request = youtube.search().list(
            part="id,snippet",
            channelId=channel_id,
            publishedAfter=start_date + "T00:00:00Z",
            publishedBefore=end_date + "T23:59:59Z",
            maxResults=50,
            type="video",
            pageToken=next_page_token
        )
        response = request.execute()
        
        for item in response.get("items", []):
            video_id = item["id"]["videoId"]
            title = clean_text(item["snippet"]["title"])  # Limpiar título
            published_at = item["snippet"]["publishedAt"]
            videos.append({"video_id": video_id, "title": title, "published_at": published_at})
        
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
    
    return videos

def get_video_metrics(video_id):
    request = youtube.videos().list(
        part="statistics",
        id=video_id
    )
    response = request.execute()
    
    stats = response["items"][0]["statistics"]
    return {
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0))
    }

def get_video_comments(video_id):
    comments = []
    next_page_token = None
    
    try:
        while True:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                pageToken=next_page_token
            )
            response = request.execute()
            
            for item in response.get("items", []):
                text = clean_text(item["snippet"]["topLevelComment"]["snippet"]["textDisplay"])  # Limpiar comentario
                comments.append(text)
            
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
    except HttpError as e:
        if e.resp.status == 403:
            print(f"Comentarios deshabilitados para el video {video_id}. Continuando...")
            return []
        else:
            raise e
    
    return comments

def main():
    data = []
    
    for channel_id in CHANNEL_IDS:
        print(f"Extrayendo datos de {channel_id}...")
        videos = get_all_videos(channel_id, START_DATE, END_DATE)
        
        for video in videos:
            metrics = get_video_metrics(video["video_id"])
            comments = get_video_comments(video["video_id"])
            
            if not comments:
                data.append([channel_id, video["video_id"], video["title"], video["published_at"], metrics["likes"], metrics["comments"], "No comments"])
            else:
                for comment in comments:
                    data.append([channel_id, video["video_id"], video["title"], video["published_at"], metrics["likes"], metrics["comments"], comment])
    
    df = pd.DataFrame(data, columns=['Channel ID', 'Video ID', 'Title', 'Published At', 'Likes', 'Num_Comments', 'Comment'])
    df.to_csv('youtube_2024_data_cleaned.csv', index=False, encoding='utf-8')
    print("CSV generado correctamente con comentarios limpios.")

if __name__ == "__main__":
    main()
