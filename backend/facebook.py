import requests
import csv
from datetime import datetime

# Token de acceso de la página (¡reemplázalo si se renueva!)
ACCESS_TOKEN = "EAAN2i2OmWkgBOzcsLVNURQgYtvo7TcqCExh86qcnqm2H9h5ZCvQ77t0ZCZAezulN90FqLWb1jn7etqhKscnDVTTFqega0GTdG3zEqjF3XB2Cqc35oZBfn1IpMLhhfzPCDj4CxgN38gQHmDxxe287ZB9IZADZCUK9fODZBzmhqY0rJagrfjDGwb7OGfxuW1Jatq2ZBNZCJDHqBO9xsXornPXLbmjgZDZD"

# ID de la página de Paramount Pictures
PAGE_ID = "120233066038"

# URL base para obtener publicaciones con likes y número de comentarios
base_url = f"https://graph.facebook.com/v21.0/{PAGE_ID}/posts?fields=id,created_time,message,reactions.summary(true).limit(0),comments.summary(true).limit(0)&access_token={ACCESS_TOKEN}"

# Crear archivo CSV
with open("paramount_posts_2024.csv", mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Post ID", "Fecha", "Mensaje", "Likes", "Comentarios", "Comentarios Detallados"])

    next_page = base_url  # Primera página de publicaciones

    while next_page:
        response = requests.get(next_page)
        data = response.json()

        if "data" in data:
            for post in data["data"]:
                post_id = post["id"]
                fecha = post.get("created_time", "Desconocida")

                # Convertir fecha a formato datetime
                fecha_dt = datetime.strptime(fecha, "%Y-%m-%dT%H:%M:%S%z")
                year = fecha_dt.year

                # Si la publicación es de 2023 o anterior, detenemos la búsqueda
                if year < 2024:
                    print("📌 Ya llegamos a publicaciones del 2023. Deteniendo búsqueda.")
                    next_page = None
                    break

                # Continuar con las publicaciones de 2024
                mensaje = post.get("message", "Sin mensaje")
                likes = post.get("reactions", {}).get("summary", {}).get("total_count", 0)
                num_comentarios = post.get("comments", {}).get("summary", {}).get("total_count", 0)

                # Segunda solicitud: Obtener los comentarios de este post
                comments_url = f"https://graph.facebook.com/v21.0/{post_id}/comments?fields=message,from&access_token={ACCESS_TOKEN}"
                comments_response = requests.get(comments_url)
                comments_data = comments_response.json()

                # Obtener comentarios detallados
                comentarios_lista = []
                if "data" in comments_data:
                    for comment in comments_data["data"]:
                        comentario_texto = comment.get("message", "Sin mensaje")
                        usuario = comment["from"]["name"] if "from" in comment else "Anónimo"
                        comentarios_lista.append(f"{usuario}: {comentario_texto}")

                comentarios_str = "\n".join(comentarios_lista)  # Convertir lista a string

                # Escribir en CSV
                writer.writerow([post_id, fecha, mensaje, likes, num_comentarios, comentarios_str])

            # Paginación: Verificar si hay más publicaciones
            next_page = data.get("paging", {}).get("next")

        else:
            print("❌ Error al obtener publicaciones:", data)
            break

print("✅ Datos del 2024 guardados en 'paramount_posts_2024.csv'.")


