"""
Configuration settings for thumbnail generation service
"""

THUMBNAIL_CONFIG = {
    "dimensions": {
        "width": 100,
        "height": 150
    },
    "format":{
        "type": "JPEG",
        "quality": 95
    },
    "supported_formats":{
        "pdf": [".pdf"],
        "office": [".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"],
        "text": [".txt", ".md", ".csv", ".xml", ".html", ".htm", ".gdoc"],
        "ebook": [".epub", ".kpub", ".mobi"],
        "archive": [".zip", ".rar", ".7z"],
        "image": [".png", ".jpg", ".jpeg", ".bmp", ".tiff"],
        "fixed_layout": [".xps"]
    },
    "upload": {
        "folder_name": "thumbnail_images"
    },
    "tools": {
        "pymupdf":{
            "dpi": 300,
            "format": "RGB",
            "matrix_scale": 2.0, # scaing factor for higher quality (300 DPI equivalent)
        }
    }
}

GENERIC_THUMBNAIL_COLORS = {
    "PDF": "#FF6B6B",
    "DOCX": "#4ECDC4",
    "DOC": "#4ECDC4",
    "PPTX": "#45B7D1",
    "PPT": "#45B7D1",
    "XLSX": "#96CEB4",
    "XLS": "#96CEB4",
    "TXT": "#6C7A89",
    "MD": "#7F8C8D",
    "CSV": "#2ECC71",
    "XML": "#16A085",
    "HTML": "#E67E22",
    "HTM": "#E67E22",
    "GDOC": "#3498DB",
    "EPUB": "#8E44AD",
    "KPUB": "#9B59B6",
    "MOBI": "#34495E",
    "ZIP": "#F39C12",
    "RAR": "#D35400",
    "7Z": "#A04000",
    "XPS": "#1ABC9C",
    "PNG": "#27AE60",
    "JPG": "#2980B9",
    "JPEG": "#2980B9",
    "BMP": "#95A5A6",
    "TIFF": "#7D3C98",
    "default": "#95A5A6",
}