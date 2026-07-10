# Personal Plant Photo Prototype

Phone-friendly Streamlit prototype for testing PlantNet genus identification.

The app:

- takes or uploads a plant photo from a phone browser
- sends the temporary image to PlantNet
- shows PlantNet reference images and relevant Dear Garden genus examples
- asks the user to label the result as `correct`, `incorrect`, or `unsure`
- does not store user photos

## Run locally

```powershell
streamlit run prototype/app.py
```

For local testing, set environment variables or create a local `.streamlit/secrets.toml`
from `.streamlit/secrets.toml.example`. Do not commit real secrets.

## Deploy

Deploy `prototype/app.py` on Streamlit Community Cloud.

Add these in Streamlit's Secrets box:

```toml
PLANTNET_API_KEY = "..."
SUPABASE_URL = "..."
SUPABASE_KEY = "..."
```

Use a read-only Supabase key/policy for Dear Garden catalogue reads. Do not paste real keys into GitHub, README files, screenshots, or Streamlit page text.

## Storage

The app does not store photos. It stores only evaluation rows.

Evaluation labels are written to `prototype/evaluations.csv`. This is fine for local testing, but it is not reliable durable storage for a public Streamlit Cloud app. Do not write these labels to the Dear Garden Supabase database; use a separate evaluation database later if shared durable storage is needed.

Dear Garden Supabase is used only to read catalogue plants and image URLs.