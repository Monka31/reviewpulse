# ReviewPulse user guide

This guide explains how to run ReviewPulse, use the app, analyze your own reviews and publish a report. No programming knowledge is needed for options A and the app itself.

## Option A: Google Colab (recommended, free, nothing to install)

1. Open the notebook: https://colab.research.google.com/github/Monka31/reviewpulse/blob/main/ReviewPulse.ipynb
2. Sign in with a Google account.
3. Menu `Runtime > Change runtime type`, select **T4 GPU**, click **Save**.
4. Menu `Runtime > Run all`. If Colab warns that the notebook is not authored by Google, click **Run anyway**.
5. Wait about 3 to 5 minutes on the first run (installation and model download).
6. Read the results directly in the notebook, or open the `https://xxxx.gradio.live` link printed by the last cell to use the web app.

The public link works for about 72 hours, as long as the notebook keeps running. To get a new link, run the last cell again.

## Option B: local installation

Requirements: Python 3.10 or newer, about 8 GB of free disk space. A NVIDIA GPU is strongly recommended; without one, the summary and replies take minutes instead of seconds.

```bash
git clone https://github.com/Monka31/reviewpulse.git
cd reviewpulse
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install torch                   # see https://pytorch.org for the GPU version
pip install -r requirements.txt
python app.py                       # then open http://127.0.0.1:7860
```

Command-line alternative, without the web interface:

```bash
python scripts/analyze.py data/demo_restaurant_synthetic.csv --type Restaurant --replies 5
```

It prints the key figures and writes `outputs/<business>_analyzed.csv` and `docs/reports/<business>.html`.

## Using the app

1. **Review file**: upload a CSV or Excel file, or pick one of the datasets in the list.
2. **Business name**: optional, read from the file when possible.
3. **Business type**: selects a list of themes adapted to restaurants, schools, hotels or stores. You can edit the themes (comma-separated, 10 at most).
4. Click **Analyze reviews**. About 1 to 2 minutes for 300 reviews on a T4 GPU.

Tabs:

- **Overview**: key figures, AI diagnosis with three priority actions, themes chart (positive, neutral and negative reviews per theme), star distribution and monthly trend.
- **Unanswered reviews**: negative reviews with no reply from the owner. Requires an owner-reply column in the file.
- **Reply assistant**: choose a review and click **Draft a reply**. The reply is written in the language of the review. Always check and adapt it before posting.
- **Model evaluation**: how often the AI agrees with the stars customers actually gave, compared with a naive baseline.
- **All reviews**: every review with its predicted sentiment and themes, downloadable as CSV.
- **Export report**: builds a static HTML report including reply drafts, ready to publish.

## Analyzing your own reviews

### File format

Any CSV (comma or semicolon separated) or Excel file works. Only a text column is required. Column names are detected automatically:

| Information | Accepted column names (examples) | Required |
|---|---|---|
| Review text | `text`, `review_text`, `review`, `comment`, `avis`, `texte` | Yes |
| Star rating | `rating`, `stars`, `review_rating`, `note` (values like `4`, `4/5`, `4 stars`) | No, enables the evaluation |
| Date | `date`, `review_datetime_utc`, `publishedAtDate` | No, enables the trend chart |
| Owner reply | `owner_answer`, `responseFromOwnerText`, `reply` | No, enables unanswered-review detection |
| Business | `place`, `name`, `business` | No |

Columns containing reviewer identities (`author_title`, `author_id`, `author_image`...) are removed when the file is loaded.

### Collecting Google reviews with Outscraper

1. Create an account on https://outscraper.com and open the **Google Maps Reviews** service.
2. Enter the business name and city (or paste its Google Maps link), choose the number of reviews, language `fr` and sorting **newest**.
3. Download the result (Excel, CSV or JSON), then convert it:

```bash
python scripts/collect_reviews_outscraper.py --file Outscraper-export.xlsx
```

The raw Outscraper Excel file can also be uploaded directly in the app: columns are detected and reviewer identities removed on load. Converting it first is still recommended before committing data to GitHub, because the raw export contains reviewers' names and profile links.

Or collect directly through the API (key in your Outscraper profile, never committed to GitHub):

```bash
pip install outscraper
export OUTSCRAPER_API_KEY="your_key"
python scripts/collect_reviews_outscraper.py --query "ESSEC Business School, Cergy" --limit 500
```

The CSV is saved in `data/` with only the place, date, rating, text and owner reply.

## Publishing a report with a permanent link (GitHub Pages)

1. Create the report: notebook section 6, the **Export report** tab, or `scripts/analyze.py`. It is written to `docs/reports/`, and `docs/index.html` lists all reports.
2. Add the `docs/` folder to the GitHub repository (upload through the GitHub website or `git push`).
3. One-time setup on GitHub: `Settings > Pages > Build and deployment > Source: Deploy from a branch`, branch `main`, folder `/docs`, **Save**.
4. After about a minute the site is online at `https://<github-user>.github.io/reviewpulse/`.

## Troubleshooting

| Problem | Solution |
|---|---|
| "No GPU" message, very slow generation | `Runtime > Change runtime type > T4 GPU`, then `Runtime > Run all`. |
| Colab: "cannot connect to GPU backend" | Free GPUs are limited at peak times. Wait a little or retry later; the analysis also runs on CPU, more slowly. |
| "No review text column found" | Rename the column containing the reviews to `text`. |
| Accents look broken in Excel | Open the CSV with `Data > From Text/CSV` and choose UTF-8. |
| The gradio.live link stopped working | The Colab session ended. Run the last cell again for a new link. |
| Out of memory on the GPU | Lower "Max reviews", or set the environment variable `REVIEWPULSE_LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct`. |

## For developers

- All settings (models, theme presets, thresholds) are in `reviewpulse/config.py`; models can be swapped with environment variables (`REVIEWPULSE_SENTIMENT_MODEL`, `REVIEWPULSE_ZERO_SHOT_MODEL`, `REVIEWPULSE_LLM_MODEL`).
- Every prompt sent to the LLM is in `reviewpulse/llm.py`.
- Tests run in seconds without downloading models: `pip install pytest && pytest -q` (they use a keyword-based mock backend, enabled with `REVIEWPULSE_MOCK=1`, which is not AI and must not be used for real analyses).
