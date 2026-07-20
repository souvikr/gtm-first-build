"""
gtm_agent — GTM signal-to-outbound pipeline package.

Loads environment variables from a .env file at the project root
(if present) so that OPENAI_API_KEY is available to all submodules
before any OpenAI client is instantiated.
"""
from dotenv import load_dotenv

# load_dotenv() is a no-op if .env doesn't exist, so this is always safe.
# override=False means an already-set env var (e.g. from CI) takes priority.
load_dotenv(override=False)
