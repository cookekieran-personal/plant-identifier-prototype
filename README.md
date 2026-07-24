# Personal Plant Photo Prototype

Phone-friendly Streamlit prototype for testing PlantNet plant identification.

The app:

- takes or uploads a plant photo from a phone browser
- sends the temporary image to PlantNet
- shows the exact species suggestion when PlantNet confidence is high
- shows PlantNet reference images and relevant Dear Garden genus examples
- asks for a second, more identifiable photo when confidence is low or the user marks the match incorrect
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

# Dear Garden catalogue reads only.
SUPABASE_URL = "..."
SUPABASE_KEY = "..."

# Separate evaluation database for tester verdicts.
EVAL_SUPABASE_URL = "..."
EVAL_SUPABASE_KEY = "..."
EVAL_SUPABASE_TABLE = "prototype_evaluations"
```

Use a read-only Supabase key or policy for Dear Garden catalogue reads. Do not paste real keys into GitHub, README files, screenshots, or Streamlit page text.

## Storage

The app does not store photos. It stores only evaluation rows: the suggested genus, PlantNet score, PlantNet scientific name, alternative genera shown, optional notes, and whether the tester marked the result as `correct`, `incorrect`, or `unsure`.

When `EVAL_SUPABASE_URL` and `EVAL_SUPABASE_KEY` are configured, rows are written to the separate evaluation Supabase table. If those secrets are missing, the app falls back to `prototype/evaluations.csv` for local testing only.

Dear Garden Supabase is used only to read catalogue plants and image URLs.

## Identification notes

PlantNet returns a ranked list of probable species with confidence scores. This prototype treats scores of `70%` and above as high-confidence exact species suggestions, scores below `50%` as low confidence, and invites the user to add another photo of the same plant. PlantNet supports multiple photos of the same plant in one request, and its docs recommend sharp, well-lit images of multiple organs such as flower, leaf, fruit, or bark. When available, a clear flower photo is usually a strong second photo because flowers often carry distinctive species-level features.
