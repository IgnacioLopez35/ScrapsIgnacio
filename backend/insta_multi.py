import requests
import csv
from datetime import datetime

# Token de acceso de la página (¡reemplázalo con el más reciente si se renueva!)
ACCESS_TOKEN = "EAAN2i2OmWkgBO2OFxBMuJepMQALkI28cgKZBjhG9LYZBRirExMts1Rw5pWTTAJkTjXuWrAQFDPy6X3XShrH4g87eAdHLwGb5S6TMZCn6IlyjS7k42Ezp5p89CtuUYvghnXjfNce7cNbZAfVZAkBK9qnoPO3pQt5tR5oj2vn4JBI53mUaoTdvMXI5bpywHl6Sr0vhSo2JHT9dUzKLImkGWvWtKZCF9G81sHR7TvIHZCuaQj6ebFGEZCyA"

# IDs de las cuentas de Instagram vinculadas
INSTAGRAM_IDS = {
    "Videocine": "264542504",
    "Sony Pictures México": "416065046",
    "Diamond Films México": "460201226",
    "Universal Pictures México": "226344817",
    "Warner Bros México": "1272200412",
    "Corazón Films": "251941099"
}

# Crear archivo CSV
with open("instagram_posts_2024_compe.csv", mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Cuenta", "Post ID", "Fecha", "Mensaje", "Likes", "Comentarios", "Comentarios Detallados"])
    
    for account_name, INSTAGRAM_ID in INSTAGRAM_IDS.items():
        print(f"📡 Extrayendo datos de {account_name}...")
        base_url = f"https://graph.facebook.com/v21.0/{INSTAGRAM_ID}/media?fields=id,caption,timestamp,like_count,comments_count&access_token={ACCESS_TOKEN}"
        next_page = base_url  # Primera página de publicaciones
        
        while next_page:
            response = requests.get(next_page)
            data = response.json()
            
            if "data" in data:
                for post in data["data"]:
                    post_id = post["id"]
                    fecha = post.get("timestamp", "Desconocida")
                    fecha_dt = datetime.strptime(fecha, "%Y-%m-%dT%H:%M:%S%z")
                    year = fecha_dt.year
                    
                    if year < 2024:
                        print(f"📌 Ya llegamos a publicaciones del 2023 en {account_name}. Deteniendo búsqueda.")
                        next_page = None
                        break
                    
                    mensaje = post.get("caption", "Sin mensaje")
                    likes = post.get("like_count", 0)
                    num_comentarios = post.get("comments_count", 0)
                    
                    # Segunda solicitud: Obtener comentarios de este post
                    comments_url = f"https://graph.facebook.com/v21.0/{post_id}/comments?fields=text,username&access_token={ACCESS_TOKEN}"
                    comments_response = requests.get(comments_url)
                    comments_data = comments_response.json()
                    
                    comentarios_lista = []
                    if "data" in comments_data:
                        for comment in comments_data["data"]:
                            comentario_texto = comment.get("text", "Sin mensaje")
                            usuario = comment.get("username", "Anónimo")
                            comentarios_lista.append(f"{usuario}: {comentario_texto}")
                    
                    comentarios_str = "\n".join(comentarios_lista)  # Convertir lista a string
                    
                    # Escribir en CSV
                    writer.writerow([account_name, post_id, fecha, mensaje, likes, num_comentarios, comentarios_str])
                
                next_page = data.get("paging", {}).get("next")
            else:
                print(f"❌ Error al obtener publicaciones de {account_name}:", data)
                break

print("✅ Datos del 2024 guardados en 'instagram_posts_2024.csv'.")
