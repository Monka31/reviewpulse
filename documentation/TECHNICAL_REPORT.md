# ReviewPulse technical report

This report explains how ReviewPulse works, why each tool was chosen, how its outputs are evaluated and what its limits are. The user guide covers how to use it.

## 1. Objective and scope

ReviewPulse takes the Google reviews of one business and produces a dashboard that an owner can act on: what customers like, what they complain about, how this changes over time, which complaints were left unanswered and how to reply to them. The target users are independent businesses with a few dozen to a few thousand reviews, such as restaurants, shops, hotels or schools, that cannot afford a customer-experience platform.

Three constraints shaped the design. The application had to be free to run, so it relies on open-source models and a free Colab GPU rather than a paid API. It had to be reproducible by a grader in one click, so everything starts from a single notebook and the data is stored in the repository. And it had to be built in a few days by a small team, so it reuses pre-trained models instead of training new ones.

## 2. Architecture

The code is a small Python package, `reviewpulse/`, used by three entry points that share the same pipeline: the Colab notebook, the Gradio web application (`app.py`) and a command-line script (`scripts/analyze.py`). One function, `run_pipeline`, loads a file, runs the analysis, asks the language model for the diagnosis and the reply drafts, and returns a result object that the dashboard, the evaluation and the report export all read.

The pipeline has five stages. Loading and cleaning turns any review file into one standard table. Sentiment analysis predicts a star rating for each written review. Theme detection assigns each review to the business's themes. Aggregation computes statistics per theme and over time. Generation writes the diagnosis and the replies. A sixth step, evaluation, compares the predicted sentiment with the stars customers gave.

The models are loaded once per session, on first use, and kept in memory, so a second analysis in the same session skips the download and loading time.

## 3. Data loading and cleaning (`data.py`)

Review files come from different sources with different column names, so the loader looks for known names in order of priority. The text can be called `text`, `review_text`, `review`, `comment` or `avis`, the stars `review_rating`, `stars`, `rating` or `note`, and so on. Only the text column is required.

The order matters for Outscraper exports. Their Excel and CSV files repeat place-level columns on every row: `rating` there is the average of the business (4.4 for ESSEC), and `reviews` is its total number of reviews. Matching `review_rating` before `rating`, and never treating `reviews` as text, avoids silently using the business average as every review's score. An automated test checks this case.

Columns that identify reviewers (name, profile link, identifier, photo) are dropped as soon as the file is read. HTML left by the export, such as `<br>` tags and `&amp;` entities, is converted to plain text. Stars written as "4", "4/5" or "4 stars" are all read as 4. The separator (comma, semicolon or tab) is detected from the header line, so French Excel exports work.

Reviews without text are common on Google: 174 of the 250 ESSEC ratings have no text. They cannot be analyzed by the language models, but they matter for the public average and for the trend over time. The loader therefore removes them from the text analysis but keeps their date, stars and reply status aside, so that the average rating, the trend chart and the table of all reviews still include them. Empty texts, texts shorter than three characters and exact duplicates are removed, and reviews are sorted from newest to oldest.

## 4. Sentiment analysis

Each written review goes through `nlptown/bert-base-multilingual-uncased-sentiment`, a BERT model fine-tuned on product reviews in English, Dutch, German, French, Spanish and Italian. It predicts a rating from one to five stars with a confidence score. We map one and two stars to negative, three to neutral and four and five to positive.

We chose this model because it handles French and English, the two languages of our datasets, and because its output is in stars, the same unit as the customer ratings. That makes the evaluation in section 8 direct. Reviews are truncated to 512 tokens and processed in batches of 32.

## 5. Theme detection with zero-shot classification

Themes are detected with `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`, a multilingual model trained for natural language inference. For each review and each theme, the model reads the review as a premise and the sentence "This review is about {theme}." as a hypothesis, and returns the probability that the review entails it. A review gets every theme whose probability reaches 0.5, so one review can mention several themes, and its main theme is the one with the highest score.

Zero-shot classification lets a business choose its own themes without labeling any example, which is why the application offers editable presets per business type. We preferred this multilingual model to the more common `facebook/bart-large-mnli`, which is trained on English only, because many reviews are in French. The hypothesis stays in English, and the multilingual model matches it against reviews in either language.

The cost of zero-shot classification grows with the number of reviews times the number of themes, since every pair is a separate inference. Presets therefore hold six to eight themes, users are limited to ten, and reviews longer than 1,200 characters are truncated for this step only.

## 6. Aggregation and insights

For each theme, the application counts the reviews that mention it and splits them into positive, neutral and negative. The net score is the share of positive reviews minus the share of negative ones, from -100 to +100. A theme needs at least three mentions to be named a strength or a pain point, so that one angry review does not define the diagnosis.

The trend chart groups all ratings, star-only ones included, by year when the data spans more than two years and by month otherwise. Periods with fewer than three ratings are hidden and named under the chart, because an average of one or two ratings is not meaningful.

The priority matrix places each theme by its number of mentions on the horizontal axis and its net score on the vertical axis. The four quadrants read as Fix first (frequent and negative), Strengths to promote (frequent and positive), Niche strengths and Watch. To keep the chart readable with any data, dots carry a number and the theme names are listed under the chart. Dots that would overlap are moved slightly apart.

When a file has an owner-reply column, a negative review is counted as unanswered when its reply is empty. A review counts as negative when the model reads it as negative or when its author gave one or two stars, so that a complaint the model misreads still appears in the list.

## 7. Text generation (`llm.py`)

The diagnosis and the reply drafts are written by `Qwen/Qwen2.5-3B-Instruct`, a small open-source instruction model. With 3 billion parameters in half precision, it fits on the free T4 GPU of Colab, and it is the largest size of the Qwen2.5 family that leaves room for the two other models. We chose it over the 1.5-billion version because the replies are shown to customers, so the quality of the French matters more than a few seconds of generation. Without a GPU, the application switches to `Qwen2.5-0.5B-Instruct` so that it remains usable. Generation is deterministic (greedy decoding), so the same data and settings give the same text, which helps reproducibility.

The model does not read the reviews in bulk. For the diagnosis, it receives the computed statistics (sentiment split, average rating, reply rate, mentions and net score per theme) and a sample of real excerpts: the eight negative and five positive reviews the sentiment model is most confident about. The prompt asks for three Markdown sections (strengths, areas for improvement, three priority actions) in under 220 words, with each point tied to a theme, and tells the model never to state facts the data does not support. Giving the model numbers it would otherwise have to guess, and asking it to cite themes, limits hallucinations and makes the output easy to check against the charts.

For each reply, the model receives the review and its stars, with explicit rules: write in the language of the review, between 60 and 110 words, thank the customer and acknowledge the specific issue, never blame the customer, never promise refunds or discounts, never invent facts, invite direct contact, and sign as the team. Replies are drafted for the five most recent unanswered complaints during the analysis and on demand for the others, which keeps the analysis short. The full prompts are reproduced in `reviewpulse/llm.py` and summarized in the prompts log.

## 8. Evaluation method (`evaluation.py`)

Every Google review comes with the stars its author gave. These stars are labels we did not have to produce, so we use them to measure the sentiment model on each business's own reviews.

The application reports accuracy on the three sentiment classes, compared with a baseline that always predicts the most frequent class. On a business with mostly positive reviews, a useless model that always says "positive" already reaches a high accuracy, so the model is only useful if it beats that baseline. It also reports the share of exact star matches, the share within one star, the mean absolute error in stars, precision and recall for each class, and a confusion matrix of actual against predicted stars.

Two caveats apply. Customer stars are a noisy label: some people write a critical text and still give four stars, or the reverse. And three-star reviews are usually the hardest, because their texts mix praise and criticism. The evaluation results on the demo datasets are reported in section 13.

## 9. Interface and dashboard

The application uses Gradio for the controls (file upload, settings, filters, reply assistant) and renders the dashboard itself as HTML and CSS, with charts drawn as inline SVG by Python. This gives a layout built around what an owner needs to see, and the same code produces the dashboard in the application, in the notebook and in the static report, with no JavaScript. The visual identity uses a light blue close to ESSEC's, Inter for text and Plus Jakarta Sans for titles.

Filters re-slice the reviews already analyzed and redraw the dashboard, without calling the models again, which is why they respond instantly. Interactive Plotly versions of the main charts remain in the notebook for exploration.

## 10. Reproducibility

The notebook is the reference way to run the project. It clones the repository into a folder named `reviewpulse_app` (a name different from the Python package, to avoid an import clash we met during development), pulls the latest version, installs pinned dependency ranges from `requirements.txt`, checks that the package loads correctly and runs the analysis on the dataset stored in `data/`. Models are downloaded by name from Hugging Face. Text generation is deterministic.

The test suite (`tests/test_pipeline.py`) runs in a few seconds without any model, using a keyword-based mock backend that exists only for testing. It covers file loading for several formats (Outscraper exports, semicolon CSV, text-only files), the anonymization, the place-level rating trap, the full pipeline, the filters, the table of all reviews, the report export and the construction of the application. The real model code path was also run end to end with tiny randomly initialized models before the first Colab run.

## 11. Automated demo video (`demo_video.py`)

The demo video is produced by the project itself. The narration is a template filled with the figures of the analysis, so it never quotes a number the application did not compute; when the model does worse than the naive baseline, the narration says so. The voice comes from edge-tts or from the Kokoro model. Instead of recording the screen in real time, a headless Chromium driven by Playwright takes one screenshot per animation step (fifteen per second for scrolling and cursor moves) and holds the last frame of each shot for as long as its sentence lasts. Time on screen is therefore independent of how long the models take, which removes the waiting time and keeps the video between 4:42 and 5:00. If the narration runs long, the voice speeds up slightly; if it runs short, the pauses between shots grow. ffmpeg then joins the frames, the narration track and subtitles generated from the same text. Two static screens are built in HTML by the same module: one describes the pipeline step by step with the course concept each model illustrates, the other lists what makes the project repeatable. When the review export holds fewer reviews than Google Maps displays, the narration says so (`ONLINE_TOTALS` in the module: 250 returned by Outscraper out of 382 for ESSEC).

## 12. Alternatives considered

We compared several ideas before choosing review analysis, including a sales-call objection coach based on speech transcription and a support-ticket triage tool. Review analysis won because it needs no training, uses public data, has an obvious business value and makes a visual demo.

For the data, the Yelp Open Dataset offered millions of reviews but almost no French businesses. The official Google Places API returns only five reviews per place. A Chrome extension reading the review page in the browser would have made a striking demo, but it was longer to build and much harder for a grader to reproduce. We chose Outscraper exports, which give every review of a place with its stars, date and owner reply.

For hosting, a site on Vercel with a Supabase database would have given a permanent application, but it added two services, credentials and points of failure a few days before the deadline, and made reproduction harder. Hugging Face Spaces offers a permanent link but no free GPU, which makes text generation very slow. We kept Colab for the application and used GitHub Pages for permanent static reports, which needs no server at all.

## 13. Results on the demo datasets

On the ESSEC Cergy campus (250 ratings collected on October 25, 2026, 76 of them with text), the data alone shows a public average of 4.28 out of 5, an average of 3.66 among written reviews, 22 written reviews at one star, no owner reply in the export, and a dip in 2023 (3.9 out of 5, 28% of ratings at one or two stars) followed by a recovery to 4.5 in 2026.

Outscraper returned 250 of the 382 reviews that Google Maps displayed at the time, so these figures describe a sample of about two thirds of the reviews, not the full listing. The figures that depend on the models (accuracy against customer stars and against the majority-class baseline, the themes in each quadrant of the priority matrix, the first priority action of the diagnosis) are recomputed on every run. They are shown in the dashboard and quoted automatically by the demo video, so the video always matches the code and data in this repository.

## 14. Ethics and privacy

Reviewer names, identifiers, profile links and photos are removed before any analysis and never stored in the repository. Only the text, stars, date and owner reply are kept, and only for analysis. Reply drafts are labeled as AI drafts to be checked by a person, and the application never posts anything. The ESSEC case is presented constructively, as an example of what a school could improve. Large-scale collection of Google Maps data may conflict with Google's terms of service, so the project is an academic prototype and not a scraping service.

## 15. Limitations and next steps

The sentiment model misreads irony and mixed reviews, and its accuracy depends on the business, which is why it is measured each time. Zero-shot themes depend on wording, and a theme such as "experience" catches almost everything. The small language model can produce generic replies. Colab sessions are temporary and free GPUs are not guaranteed.

The next steps would be aspect-based sentiment (the sentiment of each theme within a review, instead of one sentiment per review), a larger or fine-tuned language model for replies, automatic periodic collection with alerts on new negative reviews, a comparison view between several branches or competitors, and a permanent hosted version with a GPU.
