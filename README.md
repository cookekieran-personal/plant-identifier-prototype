# Personal Plant Photo Prototype

Phone-friendly Streamlit prototype for testing PlantNet plant identification.

The app:

- takes or uploads a plant photo from a phone browser
- sends the temporary image to PlantNet
- shows PlantNet confidence separately for genus and exact species
- shows PlantNet reference images and relevant Dear Garden genus examples
- runs a card-based question flow for Rose, Hydrangea, Clematis, and Rhododendron
- asks for a second, more identifiable photo when the first photo has low genus confidence, or when the user is unsure or says the suggested genus is wrong
- asks the user whether the genus and exact species are both right, only the genus is right, both are wrong, or they are not sure
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

The app does not store photos. It stores only evaluation rows: the suggested genus, suggested species, PlantNet genus score, PlantNet species score, alternative genera shown, optional notes, and whether the tester marked the genus/species result as correct.

When `EVAL_SUPABASE_URL` and `EVAL_SUPABASE_KEY` are configured, rows are written to the separate evaluation Supabase table. If those secrets are missing, the app falls back to `prototype/evaluations.csv` for local testing only.

Dear Garden Supabase is used only to read catalogue plants and image URLs.

## Identification notes

PlantNet returns a ranked list of probable species with confidence scores. This prototype sums PlantNet species scores by genus so the UI can show genus confidence and exact-species confidence separately. Rose, Hydrangea, Clematis, and Rhododendron run card-based disambiguation because care needs vary within those genera. If the user reaches the second-photo stage, only the second photo is sent to PlantNet; the first photo is not retained or resubmitted. PlantNet docs recommend sharp, well-lit images of multiple organs such as flower, leaf, fruit, or bark. When available, a clear flower photo is usually a strong second photo because flowers often carry distinctive species-level features.
