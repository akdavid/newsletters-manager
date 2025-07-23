import asyncio
from typing import List, Optional, Dict, Any
import openai
from datetime import datetime

from ..models.email import Email
from ..models.newsletter import Newsletter, NewsletterType
from ..models.summary import Summary, SummaryFormat, SummaryStatus, NewsletterSummaryItem
from ..utils.exceptions import OpenAIServiceException
from ..utils.helpers import extract_key_metrics, truncate_text
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AIService:
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", max_tokens: int = 1000):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        openai.api_key = api_key

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

            summary_text = response.strip()
            key_points = self._extract_key_points(summary_text)
            
            return NewsletterSummaryItem(
                email_id=email.id,
                subject=email.subject,
                sender=email.get_display_name(),
                newsletter_type=newsletter.newsletter_type.value,
                summary_text=summary_text,
                key_points=key_points,
                confidence_score=newsletter.confidence_score,
                original_length=len(content),
                summary_length=len(summary_text)
            )
            
        except Exception as e:
            logger.error(f"Error summarizing newsletter {email.id}: {e}")
            raise OpenAIServiceException(f"Newsletter summarization failed: {e}")

    async def generate_daily_summary(self, newsletters: List[NewsletterSummaryItem]) -> Summary:
        try:
            if not newsletters:
                raise OpenAIServiceException("No newsletters to summarize")

            summary_id = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            summary = Summary(
                id=summary_id,
                title=f"Résumé quotidien des newsletters - {datetime.now().strftime('%d/%m/%Y')}",
                content="",
                format=SummaryFormat.HTML,
                status=SummaryStatus.GENERATING,
                newsletters_count=len(newsletters),
                total_emails_processed=len(newsletters),
                generation_date=datetime.now(),
                newsletters_summaries=newsletters,
                ai_model_used=self.model
            )

            grouped_newsletters = self._group_newsletters_by_type(newsletters)
            html_content = await self._generate_html_summary(grouped_newsletters)
            
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

        return f"""Résume cette newsletter {newsletter_type_fr} en français de manière concise et professionnelle :

Sujet: {email.subject}
Expéditeur: {email.get_display_name()}

Instructions:
- Résumé en 2-3 phrases maximum
- Mets en avant les points clés les plus importants
- Garde un ton informatif et professionnel
- Utilise des puces (•) pour les points principaux si nécessaire
- Indique le type de contenu (newsletter {newsletter_type_fr})

Contenu à résumer :
{content}

Résumé:"""

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

    def _group_newsletters_by_type(self, newsletters: List[NewsletterSummaryItem]) -> Dict[str, List[NewsletterSummaryItem]]:
        grouped = {}
        for newsletter in newsletters:
            newsletter_type = newsletter.newsletter_type
            if newsletter_type not in grouped:
                grouped[newsletter_type] = []
            grouped[newsletter_type].append(newsletter)
        return grouped

    async def _generate_html_summary(self, grouped_newsletters: Dict[str, List[NewsletterSummaryItem]]) -> str:
        try:
            prompt = self._create_html_summary_prompt(grouped_newsletters)
            html_content = await self._make_openai_request(prompt, max_tokens=2000)
            
            if not html_content:
                return self._generate_fallback_html_summary(grouped_newsletters)
            
            return html_content
            
        except Exception as e:
            logger.warning(f"Failed to generate AI HTML summary, using fallback: {e}")
            return self._generate_fallback_html_summary(grouped_newsletters)

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

    def _generate_fallback_html_summary(self, grouped_newsletters: Dict[str, List[NewsletterSummaryItem]]) -> str:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Résumé quotidien des newsletters</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .section {{ margin-bottom: 30px; }}
                .newsletter-type {{ color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 5px; }}
                .newsletter-item {{ margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
                .newsletter-subject {{ font-weight: bold; color: #333; }}
                .newsletter-sender {{ color: #666; font-size: 0.9em; }}
                .newsletter-summary {{ margin-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📧 Résumé quotidien des newsletters</h1>
                <p><strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
                <p><strong>Newsletters traitées:</strong> {sum(len(newsletters) for newsletters in grouped_newsletters.values())}</p>
            </div>
        """

        for newsletter_type, newsletters in grouped_newsletters.items():
            type_display = newsletter_type.replace('_', ' ').title()
            html += f"""
            <div class="section">
                <h2 class="newsletter-type">{type_display} ({len(newsletters)})</h2>
            """
            
            for newsletter in newsletters:
                html += f"""
                <div class="newsletter-item">
                    <div class="newsletter-subject">{newsletter.subject}</div>
                    <div class="newsletter-sender">Par: {newsletter.sender}</div>
                    <div class="newsletter-summary">{newsletter.summary_text}</div>
                </div>
                """
            
            html += "</div>"

        html += """
        </body>
        </html>
        """
        
        return html

    async def _make_openai_request(self, prompt: str, max_tokens: int = None) -> Optional[str]:
        try:
            max_tokens = max_tokens or self.max_tokens
            
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
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
                    result = json.loads(response)
                    return result
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse AI classification response for email {email.id}")
            
            return {"is_newsletter": False, "confidence": 0.0, "type": "other", "reasons": []}
            
        except Exception as e:
            logger.error(f"Error classifying email content: {e}")
            return {"is_newsletter": False, "confidence": 0.0, "type": "other", "reasons": []}