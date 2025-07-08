import boto3
from botocore.config import Config
import io
import os
import uuid
from PIL import Image, ImageOps
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

class ImageHandler:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION', 'eu-central-1')
        )
        self.bucket_name = os.environ.get('AWS_S3_BUCKET')
        self.cloudfront_domain = os.environ.get('AWS_CLOUDFRONT_DOMAIN', '')
        
    def optimize_image(self, image_file, max_width=1200, max_height=800, quality=85):
        """
        Optimize image: resize, compress, and return optimized versions
        Returns: (original_optimized, thumbnail) as BytesIO objects
        """
        try:
            # Open and fix orientation
            image = Image.open(image_file)
            image = ImageOps.exif_transpose(image)  # Fix rotation from EXIF
            
            # Convert to RGB if necessary (for RGBA, P mode images)
            if image.mode in ('RGBA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Create optimized main image
            main_image = image.copy()
            main_image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Create thumbnail
            thumbnail = image.copy()
            thumbnail.thumbnail((300, 200), Image.Resampling.LANCZOS)
            
            # Save optimized main image to BytesIO
            main_buffer = io.BytesIO()
            main_image.save(main_buffer, format='JPEG', quality=quality, optimize=True)
            main_buffer.seek(0)
            
            # Save thumbnail to BytesIO
            thumb_buffer = io.BytesIO()
            thumbnail.save(thumb_buffer, format='JPEG', quality=80, optimize=True)
            thumb_buffer.seek(0)
            
            return main_buffer, thumb_buffer, main_image.size, thumbnail.size
            
        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            raise
    
    def upload_to_s3(self, file_buffer, key, content_type='image/jpeg'):
        """Upload file buffer to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_buffer.getvalue(),
                ContentType=content_type,
                CacheControl='max-age=31536000'  # Cache for 1 year
            )
            return True
        except ClientError as e:
            logger.error(f"Error uploading to S3: {e}")
            return False
    
    def get_image_url(self, key):
        """Get public URL for image"""
        if self.cloudfront_domain:
            return f"https://{self.cloudfront_domain}/{key}"
        else:
            return f"https://{self.bucket_name}.s3.{os.environ.get('AWS_REGION', 'eu-central-1')}.amazonaws.com/{key}"
    
    def delete_image(self, key):
        """Delete image from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            logger.error(f"Error deleting from S3: {e}")
            return False
    
    def process_and_upload_image(self, image_file, folder="trip_reports"):
        """
        Complete image processing pipeline:
        1. Optimize image
        2. Upload to S3
        3. Return URLs and metadata
        """
        try:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            main_key = f"mountaineering_club/{folder}/{file_id}.jpg"
            thumb_key = f"mountaineering_club/{folder}/thumbs/{file_id}.jpg"
            
            # Optimize image
            main_buffer, thumb_buffer, main_size, thumb_size = self.optimize_image(image_file)
            
            # Upload main image
            if not self.upload_to_s3(main_buffer, main_key):
                raise Exception("Failed to upload main image")
            
            # Upload thumbnail
            if not self.upload_to_s3(thumb_buffer, thumb_key):
                raise Exception("Failed to upload thumbnail")
            
            # Return metadata
            return {
                'key': main_key,
                'thumb_key': thumb_key,
                'url': self.get_image_url(main_key),
                'thumbnail_url': self.get_image_url(thumb_key),
                'width': main_size[0],
                'height': main_size[1],
                'thumb_width': thumb_size[0],
                'thumb_height': thumb_size[1]
            }
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise
    
    def delete_images(self, image_metadata):
        """Delete both main image and thumbnail"""
        try:
            self.delete_image(image_metadata['key'])
            self.delete_image(image_metadata['thumb_key'])
            return True
        except Exception as e:
            logger.error(f"Error deleting images: {e}")
            return False