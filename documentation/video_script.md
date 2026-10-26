# Demo video script

The demo video is generated automatically by `reviewpulse/demo_video.py` (section 8 of the notebook, or `python scripts/make_demo_video.py`). This file shows what it says and shows, shot by shot. The narration is a template filled with the results of the analysis, so the figures in braces below are computed on each run and are never typed by hand. The figures written out in full come from the data itself and do not depend on the models.

The video has 19 shots and about 720 words of narration. It lasts between 4:42 and 5:00: if the narration runs long, the voice speeds up slightly, and if it runs short, the pauses between shots grow. Subtitles are generated from the same text.

The order follows the grading scheme. The first two shots give the purpose and the market need. The next three show how the application is built and how easily it can be re-run, with the course concepts it applies and why it goes beyond the course. The dashboard shots show the quality of the application on real data. The last two sum up reproducibility and the value the tool would create if it were widely used.

## 1. Title screen

On screen: The ReviewPulse logo, name and tagline.

> Every day, people leave reviews on Google, and they say exactly what a business should fix. But nobody has time to read hundreds of them. This is ReviewPulse, an AI assistant that turns all the reviews of a business into a dashboard and clear actions, in about two minutes.

## 2. The problem

On screen: Card with the ESSEC Cergy figures (4.28 out of 5 over 250 ratings, 3.66 for written reviews, 22 one-star reviews, sample of 250 out of 382 reviews) and four real review excerpts.

> Take a place everyone here knows: the ESSEC campus in Cergy. Google Maps shows 382 reviews. Outscraper, the collection service we used, returned 250 of them: that is our dataset. Their average is 4.28 out of five. Looks great. But only 76 people wrote something, and their average drops to 3.66, with 22 one-star reviews. The average hides what people really say.

## 3. The repository

On screen: The GitHub repository, scrolling through the README down to the Open in Colab button, which is highlighted.

> Everything is open source on GitHub: a small Python package, the anonymized data, ten automated tests and the documentation. Reviewers' names are removed as soon as a file is loaded. The README explains the problem, the architecture and the results, and one button opens the project in Google Colab.

## 4. Three clicks in Colab

On screen: The notebook in Google Colab, scrolling through its sections. If Colab asks for a sign-in, the generator shows the content of the notebook instead.

> Reproducing it takes three clicks: open the notebook, pick the free GPU, and click Run all. The notebook pulls the latest code, installs the versioned requirements and downloads three open models from Hugging Face. No API key, no paid service, nothing to install on your computer. The last cell starts the web app.

## 5. Under the hood

On screen: Architecture card: load, sentiment, themes, statistics, diagnosis and replies, dashboard, with the model and the course concept of each step, and why the project goes beyond the course.

> Under the hood, a loader reads any CSV or Excel export and strips personal data. A multilingual BERT model rates each review: that is transfer learning. An mDeBERTa model assigns themes with zero-shot learning, without a single labeled example. Then Qwen 2.5 writes the diagnosis and the replies, grounded in the computed statistics. Chaining three transformer models, and testing them against real customer ratings, takes us beyond the course content.

## 6. Running an analysis

On screen: The app: the ESSEC file is dropped in, the name typed, School selected, the themes highlighted, then Analyze reviews is clicked.

> Here is the app. We drop the review file exported from Google, name the business and choose its type: a school. Each type comes with editable themes, such as admissions or the campus. Then we click Analyze.

## 7. Skipping the wait

On screen: The analysis runs off camera.

> On the free GPU, the analysis takes about a minute, so let's skip ahead.

## 8. Main figures

On screen: The key figures of the dashboard, highlighted.

> The dashboard opens with the main figures: 4.28 stars, 76 written reviews, {share of negative reviews} percent of them negative, and {unanswered complaints} complaints that never got an answer.

## 9. AI diagnosis

On screen: The diagnosis card, with the cursor on the three priority actions.

> Next, the AI diagnosis: strengths, weak points and three priority actions. The model does not read hundreds of reviews blindly: it receives the statistics and real excerpts. Its first recommendation here: {first action of the AI diagnosis}.

## 10. Insights

On screen: The two donut charts: sentiment and share of themes.

> The insights show how the written reviews split: {share of positive reviews} percent positive and {share of negative reviews} percent negative. {most mentioned theme} comes up most often.

## 11. Trend

On screen: The rating and complaints over time chart.

> Over time, the average fell from 4.8 in 2021 to 3.9 in 2023, and it is back at 4.5 in 2026.

## 12. Priority matrix

On screen: The priority matrix, with the cursor on the Fix first corner.

> The priority matrix places each theme by how often it is mentioned and how people feel about it. {theme in the fix first corner} sits in the Fix first corner: frequent, and mostly negative. {strongest theme} is a strength to promote.

## 13. Can we trust the AI?

On screen: The reliability line under the star ratings.

> Can we trust the AI? Customers' stars are the ground truth, so the app evaluates itself on every file. Here, the model agrees with customers {accuracy} percent of the time, against {baseline} percent for a naive baseline.

## 14. Filters

On screen: The Stars filter set to 1 to 2 stars, then the updated figures.

> Filters let you dig deeper. Let's keep only the one and two-star reviews: the whole dashboard updates instantly, without running the models again.

## 15. Unanswered complaints

On screen: The complaints without an answer and a reply drafted by the model.

> Here are the complaints that never got an answer, newest first. For each one, ReviewPulse drafts a reply in the language of the review. A human stays in the loop: the owner reads it, adjusts it and posts it.

## 16. All reviews

On screen: The table of every review, scrolling.

> At the bottom, every review sits in one table, written or star-only, answered or not, with the AI's reading of each one.

## 17. Permanent report

On screen: The static report exported for GitHub Pages.

> Each analysis can also be exported as a static page on GitHub Pages, with a permanent link that anyone can open without Colab.

## 18. Reproducible by design

On screen: Card with the three steps to re-run the project and what makes the results repeatable.

> To sum up the engineering: one notebook, the data in the repository, versioned dependencies, deterministic text generation and automated tests. A grader gets the same figures we show here. And to analyze another business, you simply drop its export: no code to change.

## 19. Value at scale and close

On screen: End card with the GitHub and GitHub Pages links and a note that the video was generated by the project.

> Large chains pay consultants to read their reviews. Independent restaurants, shops and schools rarely can. Used widely, ReviewPulse would turn hours of reading into a weekly to-do list, get complaints answered, and show customers that their feedback changes things, for free. This video was generated automatically by the project itself. ReviewPulse: from hundreds of reviews to clear actions.

## Checking the result

Watch the generated video once before submitting it. Check the pronunciation of names (ESSEC, Qwen, mDeBERTa), that each shot shows what the narration describes, and that the final length printed at the end of the cell is between 4:30 and 5:30. The `PRONUNCIATION` table at the top of `demo_video.py` fixes words the voice reads badly, and each sentence can be edited in `build_script`.
