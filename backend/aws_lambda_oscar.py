import json
import os
import logging
from datetime import datetime
import boto3
import json

# Importar módulos personalizados
from utils import get_secret, json_to_csv
from clients.twitter_api import XAPI
from clients.youtube_api import YouTubeAPI
from clients.meta_api import MetaAPI
from s3_connection import S3Connection

# Configurar logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicializar cliente de Secrets Manager



secretsmanager_client = boto3.client('secretsmanager')

def get_parameter(name, decrypt=True):
    """Obtiene un parámetro seguro de AWS SSM Parameter Store"""
    ssm = boto3.client('ssm', region_name="us-east-2")  # Cambia la región si es necesario
    response = ssm.get_parameter(Name=name, WithDecryption=decrypt)
    return json.loads(response['Parameter']['Value'])  # Convertir a JSON
# Nombre del bucket S3
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'oscares2025.wivboost')

def lambda_handler(event, context):
    """Función principal de Lambda"""
    logger.info('Iniciando proceso de recopilación de datos de redes sociales')
    
    try:
        # Inicializar conexión S3
        s3 = S3Connection(S3_BUCKET_NAME)
        
        # Obtener los secretos de las APIs
        logger.info('Obteniendo secretos de APIs desde Secrets Manager...')
        #all_secrets = get_secret(secretsmanager_client, 'oscares2025_wivboost')
        logger.info('Obteniendo secretos de APIs desde Parameter Store...')
        all_secrets = get_parameter('/api_oscar')

    # Acceder a las claves específicas

        x_secrets = {
            'api_key': all_secrets['X_API_KEY'],
            'api_key_secret': all_secrets['X_API_KEY_SECRET'],
            'bearer_token': all_secrets['X_BEARER_TOKEN']
        }
        
        youtube_secrets = {
            'api_key': all_secrets['YOUTUBE_API_KEY'],
            'channel_id': all_secrets['YOUTUBE_CHANNEL_ID']
        }
        
        meta_secrets = {
            'access_token': all_secrets['META_ACCESS_TOKEN']
        }
        

        #x_secrets = get_secret(secretsmanager_client, 'oscares2025_wivboost/x')
        #youtube_secrets = get_secret(secretsmanager_client, 'oscares2025_wivboost/youtube')
        #meta_secrets = get_secret(secretsmanager_client, 'oscares2025_wivboost/meta')
        
        # Obtener parámetros de la solicitud (si se proporcionan)
        platforms = event.get('platforms', ['x', 'youtube', 'meta'])
        date = datetime.now().strftime('%Y-%m-%d')
        
        results = {}
        
        # Procesar cada plataforma solicitada
        for platform in platforms:
            logger.info(f"Procesando datos de {platform}...")
            
            try:
                data = None
                file_name = f"{platform}_data_{date}"
                
                # Obtener datos según la plataforma
                if platform == 'x':
                    x_api = XAPI(x_secrets)
                    data = x_api.export_data_for_dashboard()
                elif platform == 'youtube':
                    youtube_api = YouTubeAPI(youtube_secrets)
                    data = youtube_api.export_data_for_dashboard()
                elif platform == 'meta':
                    meta_api = MetaAPI(meta_secrets)
                    data = meta_api.export_data_for_dashboard()
                else:
                    logger.warning(f"Plataforma no reconocida: {platform}")
                    continue
                
                # Subir datos a S3
                if data:
                    # Subir JSON completo
                    json_url = s3.upload_data(data, platform, file_name)
                    
                    # Subir distintos componentes como CSV para QuickSight
                    csv_urls = {}
                    
                    if platform == 'x':
                        # Datos del perfil
                        profile_csv = json_to_csv(data.get('profile', {}), platform, 'profile')
                        if profile_csv:
                            profile_key = f"data/{platform}/profile/{file_name}_profile.csv"
                            csv_urls['profile'] = s3.upload_csv(profile_csv, profile_key)
                        
                        # Tweets
                        tweets_csv = json_to_csv(data.get('tweets', []), platform, 'tweets')
                        if tweets_csv:
                            tweets_key = f"data/{platform}/tweets/{file_name}_tweets.csv"
                            csv_urls['tweets'] = s3.upload_csv(tweets_csv, tweets_key)
                        
                        # Menciones
                        mentions_csv = json_to_csv(data.get('mentions', []), platform, 'mentions')
                        if mentions_csv:
                            mentions_key = f"data/{platform}/mentions/{file_name}_mentions.csv"
                            csv_urls['mentions'] = s3.upload_csv(mentions_csv, mentions_key)
                    
                    elif platform == 'youtube':
                        # Datos del canal
                        channel_csv = json_to_csv(data.get('channel', {}), platform, 'channel')
                        if channel_csv:
                            channel_key = f"data/{platform}/channel/{file_name}_channel.csv"
                            csv_urls['channel'] = s3.upload_csv(channel_csv, channel_key)
                        
                        # Videos
                        videos_csv = json_to_csv(data.get('videos', []), platform, 'videos')
                        if videos_csv:
                            videos_key = f"data/{platform}/videos/{file_name}_videos.csv"
                            csv_urls['videos'] = s3.upload_csv(videos_csv, videos_key)
                        
                        # Comentarios
                        comments_csv = json_to_csv(data.get('comments', []), platform, 'comments')
                        if comments_csv:
                            comments_key = f"data/{platform}/comments/{file_name}_comments.csv"
                            csv_urls['comments'] = s3.upload_csv(comments_csv, comments_key)
                    
                    elif platform == 'meta':
                        # Facebook
                        fb_page_csv = json_to_csv(data.get('facebook', {}).get('page', {}), platform, 'fb_page')
                        if fb_page_csv:
                            fb_page_key = f"data/{platform}/facebook/page/{file_name}_fb_page.csv"
                            csv_urls['fb_page'] = s3.upload_csv(fb_page_csv, fb_page_key)
                        
                        fb_posts_csv = json_to_csv(data.get('facebook', {}).get('posts', []), platform, 'fb_posts')
                        if fb_posts_csv:
                            fb_posts_key = f"data/{platform}/facebook/posts/{file_name}_fb_posts.csv"
                            csv_urls['fb_posts'] = s3.upload_csv(fb_posts_csv, fb_posts_key)
                        
                        fb_comments_csv = json_to_csv(data.get('facebook', {}).get('comments', []), platform, 'fb_comments')
                        if fb_comments_csv:
                            fb_comments_key = f"data/{platform}/facebook/comments/{file_name}_fb_comments.csv"
                            csv_urls['fb_comments'] = s3.upload_csv(fb_comments_csv, fb_comments_key)
                        
                        # Instagram
                        ig_profile_csv = json_to_csv(data.get('instagram', {}).get('profile', {}), platform, 'ig_profile')
                        if ig_profile_csv:
                            ig_profile_key = f"data/{platform}/instagram/profile/{file_name}_ig_profile.csv"
                            csv_urls['ig_profile'] = s3.upload_csv(ig_profile_csv, ig_profile_key)
                        
                        ig_media_csv = json_to_csv(data.get('instagram', {}).get('media', []), platform, 'ig_media')
                        if ig_media_csv:
                            ig_media_key = f"data/{platform}/instagram/media/{file_name}_ig_media.csv"
                            csv_urls['ig_media'] = s3.upload_csv(ig_media_csv, ig_media_key)
                        
                        ig_comments_csv = json_to_csv(data.get('instagram', {}).get('comments', []), platform, 'ig_comments')
                        if ig_comments_csv:
                            ig_comments_key = f"data/{platform}/instagram/comments/{file_name}_ig_comments.csv"
                            csv_urls['ig_comments'] = s3.upload_csv(ig_comments_csv, ig_comments_key)
                    
                    results[platform] = {
                        'status': 'success',
                        'message': f"Datos de {platform} procesados correctamente",
                        'json_url': json_url,
                        'csv_urls': csv_urls
                    }
                    
                    # Limpiar datos antiguos (retención)
                    s3.delete_old_data(platform, 90)  # Retener datos por 90 días
            except Exception as e:
                logger.error(f"Error al procesar {platform}: {e}")
                results[platform] = {
                    'status': 'error',
                    'message': f"Error al procesar datos de {platform}: {str(e)}"
                }
        
        # Crear un reporte de ejecución
        execution_report = {
            'execution_id': context.aws_request_id,
            'timestamp': datetime.now().isoformat(),
            'results': results
        }
        
        # Guardar el reporte de ejecución
        s3.upload_data(execution_report, 'reports', f"execution_report_{date}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Proceso completado',
                'execution_id': context.aws_request_id,
                'results': results
            }, default=str)
        }
    except Exception as e:
        logger.error(f"Error general en la ejecución: {e}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error en la ejecución',
                'error': str(e)
            })
        }