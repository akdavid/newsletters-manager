import asyncio
from typing import List, Optional, Dict, Any
import openai
from datetime import datetime

from ..models.email import Email
from ..models.newsletter import Newsletter, NewsletterType
from ..models.summary import Summary, SummaryFormat, SummaryStatus, NewsletterSummaryItem
from ..utils.exceptions import OpenAIServiceException
from ..utils.helpers import truncate_text
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AIService:
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", max_tokens: int = 1000):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.client = openai.OpenAI(api_key=api_key)

    async def summarize_newsletter(self, email: Email, newsletter: Newsletter) -> Optional[NewsletterSummaryItem]:
        try:
            content = email.content_text or email.content_html
            if not content:
                logger.warning(f"No content to summarize for email {email.id}")
                return None

            content_truncated = truncate_text(content, 4000)
            
            prompt = self._create_summary_prompt(email, newsletter, content_truncated)
            
            response = await self._make_openai_request(prompt)
            
            if not response:
                return None

            # Log raw response for debugging
            logger.debug(f"Raw AI response for {email.subject}: {response.strip()}")
            
            # Parse the structured response
            summary_text, extracted_link = self._parse_structured_response(response.strip())
            key_points = self._extract_key_points(summary_text)
            
            # Use the link extracted by AI, with fallback to old method if needed
            links = [extracted_link] if extracted_link else []
            
            logger.debug(f"Parsed summary: {summary_text[:100]}...")
            logger.debug(f"AI extracted link for {email.subject}: {extracted_link}")
            
            return NewsletterSummaryItem(
                email_id=email.id,
                subject=email.subject,
                sender=email.get_display_name(),
                newsletter_type=newsletter.newsletter_type.value,
                summary_text=summary_text,
                key_points=key_points,
                confidence_score=newsletter.confidence_score,
                original_length=len(content),
                summary_length=len(summary_text),
                links=links,
                received_date=email.received_date,
                account_source=email.account_source.value if hasattr(email.account_source, 'value') else str(email.account_source)
            )
            
        except Exception as e:
            logger.error(f"Error summarizing newsletter {email.id}: {e}")
            raise OpenAIServiceException(f"Newsletter summarization failed: {e}")

    async def generate_daily_summary(self, newsletters: List[NewsletterSummaryItem]) -> Summary:
        try:
            if not newsletters:
                raise OpenAIServiceException("No newsletters to summarize")

            # Use current date for summary generation
            now = datetime.now()
            summary_id = f"summary_{now.strftime('%Y%m%d_%H%M%S')}"
            
            # French month names
            french_months = {
                1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
                7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
            }
            french_date = f"{french_months[now.month]} {now.year}"
            
            summary = Summary(
                id=summary_id,
                title=f"Résumé des newsletters - {french_date}",
                content="",
                format=SummaryFormat.HTML,
                status=SummaryStatus.GENERATING,
                newsletters_count=len(newsletters),
                total_emails_processed=len(newsletters),
                generation_date=now,
                newsletters_summaries=newsletters,
                ai_model_used=self.model
            )

            grouped_newsletters = self._group_newsletters_by_type(newsletters)
            html_content = await self._generate_html_summary(grouped_newsletters, now)
            
            summary.content = html_content
            summary.word_count = len(html_content.split())
            summary.status = SummaryStatus.COMPLETED
            
            logger.info(f"Generated daily summary with {len(newsletters)} newsletters")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            raise OpenAIServiceException(f"Daily summary generation failed: {e}")

    def _create_summary_prompt(self, email: Email, newsletter: Newsletter, content: str) -> str:
        newsletter_type_fr = {
            NewsletterType.TECH: "technologie",
            NewsletterType.BUSINESS: "business",
            NewsletterType.NEWS: "actualités",
            NewsletterType.MARKETING: "marketing",
            NewsletterType.EDUCATION: "éducation",
            NewsletterType.ENTERTAINMENT: "divertissement",
            NewsletterType.HEALTH: "santé",
            NewsletterType.PERSONAL: "personnel",
            NewsletterType.OTHER: "autre"
        }.get(newsletter.newsletter_type, "autre")

        return f"""Résume cette newsletter {newsletter_type_fr} en français et extrait le lien principal :

Sujet: {email.subject}
Expéditeur: {email.get_display_name()}

Instructions:
- Si c'est un digest avec plusieurs articles, résume l'article PRINCIPAL mentionné dans le sujet
- Pour cet article principal : 2-3 phrases de résumé concis
- CRUCIAL: Cherche dans le contenu et copie EXACTEMENT l'URL de l'article principal (ne modifie jamais l'URL)
- L'URL doit être extraite directement du contenu HTML/texte, pas inventée ou reconstruite
- Si tu trouves plusieurs liens, choisis celui qui correspond au titre de l'article principal
- Garde un ton informatif et professionnel
- Indique le type de contenu (newsletter {newsletter_type_fr})

Format de réponse requis:
RÉSUMÉ: [ton résumé ici]
LIEN: [URL exacte trouvée dans le contenu, sans modification]

Contenu à analyser :
{content}

Réponse:"""

    def _extract_key_points(self, summary_text: str) -> List[str]:
        key_points = []
        lines = summary_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                key_points.append(line.lstrip('•-* '))
        
        if not key_points and summary_text:
            sentences = summary_text.split('.')
            key_points = [sentence.strip() for sentence in sentences if sentence.strip()][:3]
        
        return key_points

    def _parse_structured_response(self, response: str) -> tuple[str, Optional[str]]:
        """Parse the structured AI response to extract summary and link."""
        logger.debug(f"Parsing response: {response}")
        
        summary_text = ""
        extracted_link = None
        
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            logger.debug(f"Processing line: '{line}'")
            
            if line.upper().startswith('RÉSUMÉ:') or line.upper().startswith('RESUME:'):
                current_section = 'summary'
                summary_text = line.replace('RÉSUMÉ:', '').replace('RESUME:', '').strip()
                logger.debug(f"Found summary start: '{summary_text}'")
            elif line.upper().startswith('LIEN:') or line.upper().startswith('LINK:'):
                current_section = 'link'
                link_text = line.replace('LIEN:', '').replace('LINK:', '').strip()
                logger.debug(f"Found link line: '{link_text}'")
                
                # Extract URL from different formats
                extracted_link = self._extract_url_from_text(link_text)
                if extracted_link:
                    logger.debug(f"Extracted link: {extracted_link}")
                    
            elif current_section == 'summary' and line:
                # Continue building summary if we're in summary section
                summary_text += ' ' + line
            elif current_section == 'link' and line:
                # Handle case where link is on next line
                potential_link = self._extract_url_from_text(line)
                if potential_link:
                    extracted_link = potential_link
                    logger.debug(f"Found link on separate line: {extracted_link}")
        
        # Fallback: if no structured format, treat whole response as summary
        if not summary_text:
            summary_text = response
            logger.debug("No structured format found, using whole response as summary")
            
            # Try to find any URL in the response
            extracted_link = self._extract_url_from_text(response)
            if extracted_link:
                logger.debug(f"Found URL in unstructured response: {extracted_link}")
        
        logger.debug(f"Final parsed - Summary: '{summary_text[:100]}...', Link: {extracted_link}")
        return summary_text.strip(), extracted_link

    def _extract_url_from_text(self, text: str) -> Optional[str]:
        """Extract URL from text that may be in different formats."""
        if not text:
            return None
            
        import re
        
        # First check if it's a direct HTTP/HTTPS URL
        if text.startswith(('http://', 'https://')):
            return text
        
        # Check for Markdown format [text](URL)
        markdown_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        markdown_match = re.search(markdown_pattern, text)
        if markdown_match:
            url = markdown_match.group(2)
            if url.startswith(('http://', 'https://')):
                return url
        
        # Fallback: find any HTTP/HTTPS URL in the text
        url_pattern = r'https?://[^\s<>"\')\]]+' 
        url_match = re.search(url_pattern, text)
        if url_match:
            return url_match.group(0)
        
        return None

    def _group_newsletters_by_type(self, newsletters: List[NewsletterSummaryItem]) -> Dict[str, List[NewsletterSummaryItem]]:
        grouped = {}
        for newsletter in newsletters:
            newsletter_type = newsletter.newsletter_type
            if newsletter_type not in grouped:
                grouped[newsletter_type] = []
            grouped[newsletter_type].append(newsletter)
        return grouped

    async def _generate_html_summary(self, grouped_newsletters: Dict[str, List[NewsletterSummaryItem]], generation_date: datetime = None) -> str:
        # Use our improved template directly for better control over links and metadata
        return self._generate_fallback_html_summary(grouped_newsletters, generation_date)

    def _create_html_summary_prompt(self, grouped_newsletters: Dict[str, List[NewsletterSummaryItem]]) -> str:
        newsletters_text = ""
        for newsletter_type, newsletters in grouped_newsletters.items():
            newsletters_text += f"\n\n## {newsletter_type.upper()}:\n"
            for newsletter in newsletters:
                newsletters_text += f"- **{newsletter.subject}** ({newsletter.sender}): {newsletter.summary_text}\n"

        return f"""Génère un résumé HTML élégant et professionnel de ces newsletters en français.

Structure souhaitée:
- Titre principal avec la date
- Introduction courte
- Sections par type de newsletter
- Style moderne et lisible
- Utilise des couleurs et une mise en forme agréable

Newsletters à résumer:{newsletters_text}

Génère uniquement le code HTML complet, sans markdown:"""

    def _generate_fallback_html_summary(self, grouped_newsletters: Dict[str, List[NewsletterSummaryItem]], generation_date: datetime = None) -> str:
        if generation_date is None:
            generation_date = datetime.now()
            
        # French month names
        french_months = {
            1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
            7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
        }
        french_date = f"{french_months[generation_date.month]} {generation_date.year}"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Résumé des newsletters - {french_date}</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 20px; 
                    line-height: 1.6;
                    background-color: #ffffff;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px; 
                    border-radius: 12px; 
                    margin-bottom: 30px; 
                    text-align: center;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }}
                .header h1 {{ 
                    margin: 0 0 15px 0; 
                    font-size: 2.2em; 
                    font-weight: 300;
                }}
                .header p {{ 
                    margin: 5px 0; 
                    opacity: 0.9;
                    font-size: 1.1em;
                }}
                .section {{ 
                    margin-bottom: 40px; 
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                }}
                .newsletter-type {{ 
                    background: #f8f9fa;
                    color: #495057; 
                    padding: 15px 20px;
                    margin: 0;
                    font-size: 1.3em;
                    font-weight: 600;
                    border-left: 4px solid #007bff;
                }}
                .newsletter-item {{ 
                    margin: 0; 
                    padding: 20px; 
                    border-bottom: 1px solid #e9ecef;
                    transition: background-color 0.2s ease;
                }}
                .newsletter-item:last-child {{
                    border-bottom: none;
                }}
                .newsletter-item:hover {{
                    background-color: #f8f9fa;
                }}
                .newsletter-subject {{ 
                    font-weight: 600; 
                    color: #212529; 
                    font-size: 1.1em;
                    margin-bottom: 5px;
                }}
                .newsletter-sender {{ 
                    color: #6c757d; 
                    font-size: 0.9em; 
                    margin-bottom: 10px;
                }}
                .newsletter-summary {{ 
                    color: #495057;
                    line-height: 1.6;
                }}
                .newsletter-metadata {{
                    margin-top: 10px;
                    font-size: 0.8em;
                    color: #6c757d;
                    border-top: 1px solid #e9ecef;
                    padding-top: 10px;
                }}
                .newsletter-links {{
                    margin-top: 10px;
                }}
                .newsletter-links a {{
                    display: inline-block;
                    margin: 2px 5px 2px 0;
                    padding: 4px 8px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    font-size: 0.8em;
                }}
                .newsletter-links a:hover {{
                    background-color: #0056b3;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 40px;
                    padding: 20px;
                    color: #6c757d;
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📧 Résumé des newsletters</h1>
                <p><strong>{french_date}</strong></p>
                <p>Généré le {generation_date.strftime('%d/%m/%Y à %H:%M')}</p>
                <p><strong>{sum(len(newsletters) for newsletters in grouped_newsletters.values())} newsletters traitées</strong></p>
            </div>
        """

        for newsletter_type, newsletters in grouped_newsletters.items():
            type_display = newsletter_type.replace('_', ' ').title()
            html += f"""
            <div class="section">
                <h2 class="newsletter-type">{type_display} ({len(newsletters)})</h2>
            """
            
            for newsletter in newsletters:
                logger.debug(f"Processing newsletter {newsletter.subject}: {len(newsletter.links)} links, received_date={newsletter.received_date}, account={newsletter.account_source}")
                
                # Format received date
                date_str = ""
                if newsletter.received_date:
                    date_str = newsletter.received_date.strftime('%d/%m/%Y à %H:%M')
                
                # Format links (only one link now)
                links_html = ""
                if newsletter.links and newsletter.links[0]:
                    links_html = f'<div class="newsletter-links"><a href="{newsletter.links[0]}" target="_blank">📖 Lire l\'article</a></div>'
                else:
                    links_html = '<div class="newsletter-links"><span style="color: #999; font-size: 0.8em;">Aucun lien disponible</span></div>'
                
                # Format metadata
                metadata_parts = []
                if date_str:
                    metadata_parts.append(f"📅 {date_str}")
                else:
                    metadata_parts.append("📅 Date inconnue")
                    
                if newsletter.account_source:
                    metadata_parts.append(f"📧 {newsletter.account_source}")
                else:
                    metadata_parts.append("📧 Compte inconnu")
                
                metadata_html = f'<div class="newsletter-metadata">{" • ".join(metadata_parts)}</div>'
                
                html += f"""
                <div class="newsletter-item">
                    <div class="newsletter-subject">{newsletter.subject}</div>
                    <div class="newsletter-sender">Par: {newsletter.sender}</div>
                    <div class="newsletter-summary">{newsletter.summary_text}</div>
                    {links_html}
                    {metadata_html}
                </div>
                """
            
            html += "</div>"

        html += """
            <div class="footer">
                <p>📧 Résumé automatique généré par Newsletter Manager</p>
                <p>Cliquez sur les liens pour accéder aux articles originaux</p>
            </div>
        </body>
        </html>
        """
        
        return html

    async def _make_openai_request(self, prompt: str, max_tokens: int = None) -> Optional[str]:
        try:
            max_tokens = max_tokens or self.max_tokens
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": "Tu es un assistant expert en résumé de newsletters qui génère des résumés concis et informatifs en français."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            if response.choices:
                return response.choices[0].message.content.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}")
            return None

    async def classify_email_content(self, email: Email) -> Dict[str, Any]:
        try:
            content = email.content_text or email.content_html
            if not content:
                return {"is_newsletter": False, "confidence": 0.0, "type": "other"}

            content_truncated = truncate_text(content, 2000)
            
            prompt = f"""Analyse ce contenu d'email et détermine s'il s'agit d'une newsletter.

Critères d'évaluation:
- Présence de liens de désabonnement
- Structure professionnelle/marketing
- Contenu informatif récurrent
- Expéditeur commercial ou organisation

Email:
Sujet: {email.subject}
Expéditeur: {email.sender}
Contenu: {content_truncated}

Réponds en JSON avec:
- "is_newsletter": true/false
- "confidence": score de 0 à 1
- "type": "tech", "business", "news", "marketing", "education", "entertainment", "health", "personal", ou "other"
- "reasons": liste des raisons de la classification

JSON:"""

            response = await self._make_openai_request(prompt, max_tokens=200)
            
            if response:
                try:
                    import json
                    # Log the raw response for debugging
                    logger.debug(f"AI raw response for {email.id}: {response}")
                    
                    # Try to extract JSON from the response if it's wrapped in markdown
                    response_clean = response.strip()
                    if response_clean.startswith('```json'):
                        response_clean = response_clean[7:]
                    if response_clean.endswith('```'):
                        response_clean = response_clean[:-3]
                    response_clean = response_clean.strip()
                    
                    result = json.loads(response_clean)
                    return result
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse AI classification response for email {email.id}: {e}")
                    logger.debug(f"Raw response was: {response}")
            
            return {"is_newsletter": False, "confidence": 0.0, "type": "other", "reasons": []}
            
        except Exception as e:
            logger.error(f"Error classifying email content: {e}")
            return {"is_newsletter": False, "confidence": 0.0, "type": "other", "reasons": []}

