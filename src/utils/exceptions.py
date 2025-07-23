class NewsletterManagerException(Exception):
    pass


class EmailServiceException(NewsletterManagerException):
    pass


class GmailServiceException(EmailServiceException):
    pass


class OutlookServiceException(EmailServiceException):
    pass


class AIServiceException(NewsletterManagerException):
    pass


class OpenAIServiceException(AIServiceException):
    pass


class DatabaseException(NewsletterManagerException):
    pass


class ConfigurationException(NewsletterManagerException):
    pass


class AuthenticationException(NewsletterManagerException):
    pass


class AgentException(NewsletterManagerException):
    pass


class MessageBrokerException(NewsletterManagerException):
    pass


class SchedulerException(NewsletterManagerException):
    pass


class NewsletterDetectionException(NewsletterManagerException):
    pass


class SummaryGenerationException(NewsletterManagerException):
    pass