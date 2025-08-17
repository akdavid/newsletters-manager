import re
import html2text
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import hashlib
import uuid
from email.utils import parseaddr, parsedate_to_datetime


def extract_email_address(email_string: str) -> str:
    name, email = parseaddr(email_string)
    return email.lower().strip()


def extract_sender_name(email_string: str) -> Optional[str]:
    name, email = parseaddr(email_string)
    return name.strip() if name else None


def extract_domain(email: str) -> str:
    return email.split('@')[-1].lower() if '@' in email else ''


def html_to_text(html_content: str) -> str:
    if not html_content:
        return ""
    
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0
    
    return h.handle(html_content).strip()


def clean_text(text: str) -> str:
    if not text:
        return ""
    
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    text = text.strip()
    
    return text


def extract_text_from_html(html_content: str) -> str:
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for script in soup(['script', 'style']):
        script.decompose()
    
    text = soup.get_text()
    return clean_text(text)


def calculate_html_to_text_ratio(html_content: str, text_content: str) -> float:
    if not html_content or not text_content:
        return 0.0
    
    html_length = len(html_content)
    text_length = len(text_content)
    
    if html_length == 0:
        return 0.0
    
    return text_length / html_length


def contains_tracking_pixels(html_content: str) -> bool:
    if not html_content:
        return False
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    img_tags = soup.find_all('img')
    for img in img_tags:
        src = img.get('src', '')
        width = img.get('width', '')
        height = img.get('height', '')
        
        if (width == '1' and height == '1') or 'track' in src.lower():
            return True
    
    return False


def has_unsubscribe_link(html_content: str, text_content: str) -> bool:
    if not html_content and not text_content:
        return False
    
    unsubscribe_patterns = [
        r'unsubscribe',
        r'se désabonner',
        r'désinscription',
        r'opt.?out'
    ]
    
    content = (html_content or '') + ' ' + (text_content or '')
    content = content.lower()
    
    return any(re.search(pattern, content, re.IGNORECASE) for pattern in unsubscribe_patterns)


def contains_promotional_keywords(content: str) -> bool:
    if not content:
        return False
    
    promotional_keywords = [
        'sale', 'discount', 'offer', 'deal', 'promotion', 'limited time',
        'vente', 'remise', 'offre', 'promotion', 'temps limité',
        'special', 'exclusive', 'free', 'gratuit', 'spécial', 'exclusif'
    ]
    
    content_lower = content.lower()
    return any(keyword in content_lower for keyword in promotional_keywords)


def generate_email_id(message_id: str, account_source: str) -> str:
    unique_string = f"{message_id}_{account_source}"
    return hashlib.md5(unique_string.encode()).hexdigest()


def generate_uuid() -> str:
    return str(uuid.uuid4())


def parse_email_date(date_string: str) -> Optional[datetime]:
    try:
        parsed_date = parsedate_to_datetime(date_string)
        # Ensure datetime is timezone-aware to avoid warnings
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        return parsed_date
    except (ValueError, TypeError):
        return None


def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def normalize_subject(subject: str) -> str:
    prefixes = ['re:', 'fwd:', 'fw:', 'tr:', 'rv:']
    normalized = subject.lower().strip()
    
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
    
    return normalized


def extract_key_metrics(content: str) -> Dict[str, Any]:
    word_count = len(content.split()) if content else 0
    char_count = len(content) if content else 0
    
    links_count = len(re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content))
    
    return {
        'word_count': word_count,
        'char_count': char_count,
        'links_count': links_count
    }


def extract_all_links_from_email(html_content: str, text_content: str = None) -> List[str]:
    """Extract all HTTP/HTTPS links from email content for LLM selection."""
    links = set()
    
    # Extract from HTML if available
    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Find all <a> tags with href attributes
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith(('http://', 'https://')):
                # Only skip obvious tracking and unsubscribe links
                skip_terms = ['unsubscribe', 'optout', 'pixel', 'beacon']
                
                if not any(term in href.lower() for term in skip_terms):
                    # Clean the link by removing tracking parameters
                    clean_href = href.split('?')[0] if '?' in href else href
                    links.add(clean_href)
    
    # Extract from text content as fallback
    if text_content:
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        text_links = re.findall(url_pattern, text_content)
        for link in text_links:
            if not any(term in link.lower() for term in ['unsubscribe', 'optout']):
                clean_link = link.split('?')[0] if '?' in link else link
                links.add(clean_link)
    
    return list(links)