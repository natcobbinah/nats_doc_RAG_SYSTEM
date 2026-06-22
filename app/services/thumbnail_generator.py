from app.config import GENERIC_THUMBNAIL_COLORS, THUMBNAIL_CONFIG
from typing import Optional
import fitz
import os
import io
import sys
from PIL import Image, ImageDraw, ImageFont, ImageOps

if __package__:
    from ..logging_utils import LogLevel, configure_json_logging, log
    from .google_drive_processor import upload_bytes_to_drive
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log
    from app.services.google_drive_processor import upload_bytes_to_drive


class ThumbnailGenerator:
    def __init__(self):
        configure_json_logging()

        self.THUMBNAIL_WIDTH = THUMBNAIL_CONFIG["dimensions"]["width"]
        self.THUMBNAIL_HEIGHT = THUMBNAIL_CONFIG["dimensions"]["height"]
        self.JPEG_QUALITY = THUMBNAIL_CONFIG["format"]["quality"]
        self.PYMUPDF_MATRIX_SCALE = THUMBNAIL_CONFIG["tools"]["pymupdf"]["matrix_scale"]
        self.THUMBNAIL_FOLDER_NAME = THUMBNAIL_CONFIG.get("upload", {}).get("folder_name", "thumbnail_images")
        self.SUPPORTED_FORMATS = self._flatten_supported_formats(THUMBNAIL_CONFIG.get("supported_formats", {}))

    @staticmethod
    def _flatten_supported_formats(supported_formats) -> set:
        values = set()
        if isinstance(supported_formats, dict):
            for _, extensions in supported_formats.items():
                if isinstance(extensions, list):
                    values.update(ext.lower() for ext in extensions)
        return values

    @staticmethod
    def _extract_extension(filename: str) -> str:
        _, ext = os.path.splitext(filename.lower())
        return ext

    def generate_thumbnail(self, file_content: bytes, document_id: str, filename: str) -> Optional[str]:
        """Generate and upload a thumbnail URL for any extractor-supported format."""
        try:
            ext = self._extract_extension(filename)

            if self.SUPPORTED_FORMATS and ext not in self.SUPPORTED_FORMATS:
                log(
                    type=LogLevel.WARNING,
                    message={
                        "message": f"Unsupported format for thumbnail generation, {filename}",
                        "fileline": sys._getframe().f_lineno,
                        "message_data": {"extension": ext},
                        "reason": "Using generic thumbnail fallback",
                    },
                )

            image_formats = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}

            if ext == ".pdf":
                return self.generate_thumbnail_with_pymupdf(file_content, document_id, filename)

            if ext in image_formats:
                return self.generate_thumbnail_from_image(file_content, document_id, filename)

            return self.generate_generic_thumbnail(document_id, filename)
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Failed to generate thumbnail for file, {filename}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e),
                },
            )
            return None

    def generate_thumbnail_from_image(self, image_content: bytes, document_id: str, filename: str) -> Optional[str]:
        """Generate thumbnail from image formats supported by image extractor."""
        try:
            image = Image.open(io.BytesIO(image_content))
            return self._create_and_upload_thumbnail(image, document_id, filename, "Pillow")
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Failed to generate thumbnail from image, {filename}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e),
                },
            )
            return None

    def generate_generic_thumbnail(self, document_id: str, filename: str) -> Optional[str]:
        """Generate generic thumbnail for text/archive/office shortcut formats."""
        try:
            ext = self._extract_extension(filename)
            ext_label = ext.lstrip(".").upper() if ext else "FILE"
            color = GENERIC_THUMBNAIL_COLORS.get(ext_label, GENERIC_THUMBNAIL_COLORS.get("default", "#95A5A6"))

            image = Image.new("RGB", (self.THUMBNAIL_WIDTH * 2, self.THUMBNAIL_HEIGHT * 2), color)
            draw = ImageDraw.Draw(image)
            font = ImageFont.load_default()

            text_main = ext_label
            text_sub = os.path.basename(filename)[:24]

            main_bbox = draw.textbbox((0, 0), text_main, font=font)
            sub_bbox = draw.textbbox((0, 0), text_sub, font=font)

            main_w = main_bbox[2] - main_bbox[0]
            main_h = main_bbox[3] - main_bbox[1]
            sub_w = sub_bbox[2] - sub_bbox[0]
            sub_h = sub_bbox[3] - sub_bbox[1]

            width, height = image.size
            draw.text(((width - main_w) / 2, (height - main_h) / 2 - 10), text_main, fill="white", font=font)
            draw.text(((width - sub_w) / 2, (height - sub_h) / 2 + 10), text_sub, fill="white", font=font)

            return self._create_and_upload_thumbnail(image, document_id, filename, "Generic")
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Failed to generate generic thumbnail, {filename}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e),
                },
            )
            return None

    def generate_thumbnail_with_pymupdf(self, pdf_content: bytes, document_id: str, filename: str) -> Optional[str]:
        """
        Generate thumbnail using pymupdf (fitz)
        """
        try:
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")

            if pdf_document.page_count == 0:
                log(type=LogLevel.WARNING, message=f"No pages found in PDF, {filename}")
                pdf_document.close() 
                return None 
            
            # get first page 
            first_page = pdf_document[0]

            mat = fitz.Matrix(self.PYMUPDF_MATRIX_SCALE, self.PYMUPDF_MATRIX_SCALE)

            pix = first_page.get_pixmap(matrix=mat, alpha=False, colorspace=fitz.csRGB)

            image_data = pix.tobytes("ppm")
            image = Image.open(io.BytesIO(image_data))

            pix = None 
            pdf_document.close()

            return self._create_and_upload_thumbnail(
                image, document_id, filename, "PyMuPDF"
            )

        except (fitz.FileDataError, fitz.EmptyFileError, Exception) as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Failed to generate thumbnail for file, {filename}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e),
                },
            )
            return None

    def _create_and_upload_thumbnail(self, source_image: Image.Image, document_id: str, filename: str,method: str) -> Optional[str]:
        """
        create high-quality thumbnail from source iamge and upload to google drive-folder named thumbnail images
        """
        try: 
            enhanced_image = source_image.copy() 

            if enhanced_image.mode != "RGB":
                enhanced_image = enhanced_image.convert('RGB')

            enhanced_image = ImageOps.exif_transpose(enhanced_image)

            thumbnail = enhanced_image.copy() 
            thumbnail.thumbnail(
                (self.THUMBNAIL_WIDTH, self.THUMBNAIL_HEIGHT),
                Image.Resampling.LANCZOS
            )

            output_buffer = io.BytesIO()
            thumbnail.save(
                output_buffer,
                format="JPEG",
                quality=self.JPEG_QUALITY,
                optimize=True,
            )
            output_buffer.seek(0)

            base_name = os.path.splitext(os.path.basename(filename))[0]
            thumbnail_name = f"{base_name}_{document_id}_thumbnail.jpg"

            upload_result = upload_bytes_to_drive(
                file_bytes=output_buffer.getvalue(),
                filename=thumbnail_name,
                mime_type="image/jpeg",
                folder_name=self.THUMBNAIL_FOLDER_NAME,
            )

            thumbnail_url = upload_result.get("url")

            log(
                type=LogLevel.INFO,
                message={
                    "message": f"Thumbnail generated and uploaded successfully for {filename}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {
                        "document_id": document_id,
                        "thumbnail_name": thumbnail_name,
                        "upload_method": method,
                        "thumbnail_url": thumbnail_url,
                    },
                    "reason": "Thumbnail generation completed",
                },
            )

            return thumbnail_url
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Failed to create/upload thumbnail for {filename}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {
                        "error": str(e),
                        "document_id": document_id,
                        "upload_method": method,
                    },
                    "reason": str(e),
                },
            )
            return None

