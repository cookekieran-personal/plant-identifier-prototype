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
SUPABASE_EVALUATIONS_TABLE = "prototype_evaluations"
```

Use a restricted Supabase key/policy for public testing. Do not paste real keys
into GitHub, README files, screenshots, or Streamlit page text.

## Storage

The app does not store photos. It stores only evaluation rows.

If Supabase is configured, rows are inserted into the Supabase table. If Supabase
insert fails or is not configured, local runs fall back to `prototype/evaluations.csv`.
That CSV is not reliable storage for a public Streamlit Cloud app.

Suggested Supabase table:

```sql
create table prototype_evaluations (
  id bigint generated always as identity primary key,
  created_at timestamptz default now(),
  test_id text not null,
  verdict text not null check (verdict in ('correct', 'incorrect', 'unsure')),
  suggested_genus text,
  plantnet_score double precision,
  plantnet_scientific_name text,
  plantnet_common_name text,
  alternative_genera text[],
  notes text
);
```

