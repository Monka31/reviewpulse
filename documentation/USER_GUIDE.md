# ReviewPulse user guide

This guide explains how to start ReviewPulse, how to analyze the reviews of a business, how to read each part of the dashboard and how to publish a report. You do not need to know how to program to use the application through Google Colab.

## 1. What you need

You need a Google account to use Colab, and a file of reviews. The project already contains the reviews of the ESSEC Cergy campus (`data/reviews_ESSEC_Cergy.csv`), so you can try the application without collecting anything. To analyze another business, section 6 explains how to export its Google reviews with Outscraper.

## 2. Start the application in Google Colab

Open the notebook at https://colab.research.google.com/github/Monka31/reviewpulse/blob/main/ReviewPulse.ipynb and sign in with your Google account.

Before running anything, choose a GPU: open `Runtime > Change runtime type`, select T4 GPU and click Save. The application also works without a GPU, but writing the diagnosis and the replies then takes several minutes instead of seconds.

Then click `Runtime > Run all`. If Colab warns that the notebook was not written by Google, click Run anyway. The notebook checks the GPU, downloads the code from GitHub, installs the libraries, downloads the three models (about two minutes the first time), analyzes the ESSEC reviews and displays the dashboard inside the notebook. Its last cell starts the web application and prints a link that looks like `https://xxxx.gradio.live`. Open that link: the application runs in your browser, on any computer or phone.

The link works for about 72 hours, as long as the Colab tab stays open and active. When Colab disconnects, run the last cell again to get a new link. If something looks out of date or broken, use `Runtime > Disconnect and delete runtime`, then `Runtime > Run all`. This starts from a clean copy of the latest code.

A red message mentioning `diffusers` and `huggingface-hub` may appear during installation. It concerns a library preinstalled on Colab that ReviewPulse does not use, and you can ignore it.

## 3. Run an analysis

The New analysis panel on the left holds every setting.

Drop the review file in the Review file area. It accepts the Excel or CSV file exported by Outscraper as it is, and any other CSV or Excel file with a column of review text. If you do not drop a file, the application uses the dataset selected in the list below it. A dropped file always takes priority over the list.

Type the name of the business as you want it to appear on the dashboard. When this field is empty, the name is read from the file.

Choose the business type: Restaurant, School / University, Hotel, Retail store or Generic business. Each type loads a list of themes adapted to it. For a school, for example, the themes are teaching quality, campus and facilities, admissions, staff and welcome, administration, student life, career opportunities and tuition fees. You can edit the list in the Themes to detect field (comma-separated, ten themes at most). Short and concrete themes work best, such as "waiting time" rather than "experience".

Choose the language of the AI diagnosis, EN or FR. Reply drafts are always written in the language of the review they answer.

Advanced settings holds three options. Max reviews limits the analysis to the most recent written reviews (500 by default). Reply drafts written during the analysis sets how many of the latest unanswered complaints get a reply draft straight away (5 by default; the others can be drafted on demand). Write the AI diagnosis can be unticked for a faster analysis without text generation.

Click Analyze reviews. A progress bar shows each step. On a T4 GPU, 300 reviews should take about one to two minutes.

## 4. Read the dashboard

The header shows the business type and name, the number of written reviews analyzed, the number of star-only ratings (people who gave stars without writing) and the period covered.

The four main figures come next. Average rating counts every rating in the file, star-only ones included, so it matches what Google shows. Written reviews gives the number of reviews with text and their own average, which is often lower because unhappy customers are more likely to write. Negative reviews is the share of written reviews the AI reads as negative. Complaints left unanswered counts negative reviews with no reply from the owner, together with the reply rate on complaints.

The AI diagnosis is written by the language model from the statistics and from real excerpts of reviews. It has three columns: strengths, points to improve and three priority actions.

The Insights section holds five charts. Sentiment of written reviews splits them into positive, neutral and negative. Share of mentions by theme shows which topics dominate the conversation. Rating and complaints over time draws the average stars per year or per month as a line, and the share of one and two-star ratings as bars, so you can see when things got worse or better. The priority matrix places each theme by how often it is mentioned (left to right) and by net sentiment, the share of positive minus negative reviews (bottom to top). Themes in the bottom right corner, Fix first, are mentioned often and mostly negatively: they deserve attention first. Each dot carries a number, and the list under the chart gives the theme, its number of mentions and its net score. Average stars by theme shows the stars customers gave when they mentioned each theme.

What people talk about shows, for each theme, how many reviews mention it and how they split between positive, neutral and negative. Star ratings shows the distribution of stars and the measured reliability of the AI on these reviews, compared with a naive baseline.

Complaints without an answer lists the negative reviews that received no reply, newest first. The latest ones come with an AI reply draft. Long reviews are shortened, and Read the full review shows the whole text. Show the other complaints opens the rest of the list. When the file contains no owner reply at all, a note warns that either the business never answers or the export did not include replies, which you can check on Google Maps.

All reviews is a table of every review in the file, written or star-only, with its date, stars, text, AI sentiment, themes and whether the owner answered. It is sorted from newest to oldest and folds with one click.

## 5. Filter, draft replies and export

The filters above the dashboard (Period, Stars and Theme) recompute every figure, chart, list and table from the reviews already analyzed, without running the models again, so they respond instantly. For example, choose 2025, 1 to 2 stars and admissions to read only last year's negative reviews about admissions. When a theme is selected, star-only ratings disappear from the table because they have no text and therefore no theme. Reset filters returns to the full view. The AI diagnosis always describes the whole dataset.

The Reply assistant, under the dashboard, lists the negative reviews of the current view, unanswered ones first. Pick one, read it, and click Draft a reply. The draft appears in an editable box with a copy button, and in the review's card on the dashboard. Clicking again writes a new version. Always read and adapt a draft before posting it: it is a suggestion, not a verified answer.

Model evaluation details how often the AI agrees with the stars customers gave: accuracy on the three sentiment classes compared with a naive baseline, exact star matches, matches within one star, mean error, precision and recall per class, and a confusion matrix.

Search reviews and export contains the full review table with a search box (type "parking" or "admission" to find every review that mentions it), a download of the analyzed reviews as CSV, and the Build the HTML report button described in section 7.

## 6. Analyze your own business

To collect the Google reviews of any business, create an account on https://outscraper.com and open the Google Maps Reviews service. Enter the business name and city, or paste its Google Maps link, set the number of reviews, the language (`fr` for a French business) and the sorting by newest, then start the task. Download the result as Excel or CSV. Drop this file directly in the application.

Before sharing review data or adding it to the GitHub repository, convert it with the collection script. The raw Outscraper export contains reviewers' names, profile links and photos, and the script keeps only the place, date, stars, text and owner reply:

```bash
python scripts/collect_reviews_outscraper.py --file Outscraper-export.xlsx
```

The anonymized file is saved in `data/`. In Colab, you can run this command in a new cell after uploading the export with the file panel on the left, adding a `!` before `python`.

The script can also collect reviews directly through the Outscraper API, with a key from your Outscraper profile. Never write the key in the code or commit it to GitHub:

```bash
pip install outscraper
export OUTSCRAPER_API_KEY="your_key"
python scripts/collect_reviews_outscraper.py --query "ESSEC Business School, Cergy" --limit 500
```

Other sources work as long as the file has a column of review text. Column names are recognized automatically: the text can be called `text`, `review_text`, `review`, `comment` or `avis`; the stars `review_rating`, `stars`, `rating` or `note` (values such as 4, 4/5 or "4 stars"); the date `date` or `review_datetime_utc`; the owner reply `owner_answer` or `reply`. Comma and semicolon separators both work. Stars, dates and replies are optional, but without them the evaluation, the trend chart or the unanswered-review detection cannot be computed, and the dashboard says so.

## 7. Publish a report with a permanent link

Each analysis can become a static web page with the same dashboard, plus the model evaluation, which anyone can open without Colab. In the application, open Search reviews and export, choose how many reply drafts to include and click Build the HTML report, then download the file. In the notebook, section 6 does the same and downloads a `site.zip` containing the report and the updated home page.

On GitHub, upload the report to the `docs/reports/` folder of the repository and the home page `index.html` to `docs/`. The first time only, activate GitHub Pages in `Settings > Pages` with the source Deploy from a branch, the branch `main` and the folder `/docs`. One or two minutes later the report is online at `https://monka31.github.io/reviewpulse/`, which lists every published report.

## 8. Run ReviewPulse on your own computer

This option suits people comfortable with a terminal. You need Python 3.10 or newer and about 8 GB of free disk space for the models. Without an NVIDIA GPU, the application works but text generation is slow.

```bash
git clone https://github.com/Monka31/reviewpulse.git
cd reviewpulse
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install torch                  # see https://pytorch.org for the GPU version
pip install -r requirements.txt
python app.py                      # then open http://127.0.0.1:7860
```

The command line gives the same analysis without the interface. It prints the main figures and writes the analyzed reviews to `outputs/` and an HTML report to `docs/reports/`:

```bash
python scripts/analyze.py data/reviews_ESSEC_Cergy.csv --name "ESSEC Business School" --type "School / University" --replies 5
```

`python scripts/analyze.py --help` lists every option, including the summary language and custom themes.

## 9. Troubleshooting

If the notebook says there is no GPU, or generation is very slow, choose `Runtime > Change runtime type > T4 GPU`, then run everything again. If Colab cannot connect to a GPU, free GPUs are probably all in use: wait a little and retry, or run on a CPU and accept slower generation.

If the setup cell stops with "Code not found", the copy of the repository on GitHub is incomplete. Check that the `reviewpulse/` folder of the repository contains its ten Python files, then use `Runtime > Disconnect and delete runtime` and run everything again.

If the application says that no review text column was found, rename the column that holds the reviews to `text`. If accents look broken when you open a CSV in Excel, import it through `Data > From Text/CSV` and choose UTF-8. If the `gradio.live` link stops working, the Colab session has ended: run the last cell again. If the GPU runs out of memory, lower Max reviews in the advanced settings.

## 10. Generate the demo video automatically

Section 8 of the notebook builds the demo video with no manual step. Set `MAKE_DEMO_VIDEO = True` in that cell and run it, or run everything. It takes about fifteen minutes on a T4 GPU and downloads `ReviewPulse_demo.mp4` at the end.

The cell analyzes the ESSEC reviews, writes the narration from the real results (ratings, share of negative reviews, unanswered complaints, the theme to fix first, the first priority action, the measured accuracy), and has it read by an AI voice. A headless browser then opens the GitHub repository and the notebook, shows a screen on the architecture and the course concepts, opens the application, uploads the file, starts the analysis, scrolls through the dashboard, applies a filter, shows the reply drafts, scrolls through the table of all reviews, and shows the published report and a closing screen on reproducibility. Each shot lasts exactly as long as its sentence, and the waiting time of the analysis is cut. ffmpeg assembles a 1080p video with subtitles, between 4:42 and 5:00.

`VOICE_ENGINE = "edge"` uses Microsoft neural voices through edge-tts and is the recommended setting. `"kokoro"` uses the open-source Kokoro voice model from Hugging Face. `VOICE` sets the voice, for example `en-US-AvaNeural`, `en-US-AndrewNeural` or `en-GB-SoniaNeural`. When Colab does not let a browser open the notebook without signing in, the video shows the content of the notebook instead.

From a terminal, the same video comes from `python scripts/make_demo_video.py`, after `pip install playwright edge-tts` and `playwright install --with-deps chromium`.

## 11. For developers

All settings (models, theme presets, thresholds) are in `reviewpulse/config.py`. Models can be replaced without touching the code through the environment variables `REVIEWPULSE_SENTIMENT_MODEL`, `REVIEWPULSE_ZERO_SHOT_MODEL` and `REVIEWPULSE_LLM_MODEL`. Every prompt sent to the language model is in `reviewpulse/llm.py`. The analysis can also be called from Python with `reviewpulse.run_pipeline(path, business_type="Restaurant")`.

The tests run in a few seconds without downloading any model, using a keyword-based mock backend that is enabled only for testing and must never be used for a real analysis:

```bash
pip install pytest
pytest -q
```
