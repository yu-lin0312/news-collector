import os
from dotenv import load_dotenv

# Load .env as the app/crawler would
load_dotenv()

print(f"USE_FIRESTORE: {os.environ.get('USE_FIRESTORE')}")
print(f"GOOGLE_API_KEY: {'Set' if os.environ.get('GOOGLE_API_KEY') else 'Not Set'}")
