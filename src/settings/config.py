from dotenv import load_dotenv
from os import getenv


load_dotenv()

# Outlook_vit
OUTLOOK_EMAIL = getenv('OUTLOOK_EMAIL')
OUTLOOK_PASSWORD = getenv('OUTLOOK_PASSWORD')
# Email_tac
EMAIL_TAC = getenv('EMAIL_TAC')
# Alert
CRITICAL_HOSTS = [host.strip().replace(' ', '') for host in getenv('CRITICAL_HOSTS').split(',')]
RECIPIENTS_EMAILS = getenv('RECIPIENTS_EMAILS')
EXCLUDE_GROUPS = getenv('EXCLUDE_GROUPS')
# Redis
REDIS_HOST = getenv('REDIS_HOST', 'redis_app')
REDIS_PORT = int(getenv('REDIS_PORT', 6379))
# Telegram
TELEGRAM_TOKEN = getenv('TELEGRAM_TOKEN')
