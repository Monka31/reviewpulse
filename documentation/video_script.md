# Demo video script

Target length 4:50 (allowed 4:30 to 5:30). The narration is about 650 words, roughly 4:45 at a calm pace. Record the screen in 1080p and the voice separately with a decent microphone, then cut every loading wait during editing. Replace the text in brackets with the figures from the final analyses.

## 0:00 to 0:35, the problem

On screen: the Google Maps page of a restaurant, scrolling through hundreds of reviews.

> Imagine you run a restaurant. You have hundreds of Google reviews and more every week. You don't have time to read them, so you check the average, four stars, and move on. But the reasons customers don't come back are written in those reviews. And some of the angriest ones never got an answer, even though every future customer can read them.

## 0:35 to 1:05, the solution

On screen: the ReviewPulse home screen, then the architecture diagram from the README.

> This is ReviewPulse. You drop in the reviews of any business, and in about two minutes you get a dashboard: what customers love, what frustrates them, which complaints were never answered, and a reply ready for each one. Three open-source models from Hugging Face do the work: one reads the sentiment, one sorts each review into themes without any training, and a small language model writes the diagnosis and the replies. It all runs for free in Google Colab.

## 1:05 to 2:20, live test 1: ESSEC

On screen: drop the ESSEC file, choose School / University, click Analyze reviews. Cut the wait. Show the main figures, then the trend chart, then the priority matrix.

> Let's start with a business everyone here knows: ESSEC. On Google, the Cergy campus has 4.28 stars. But only 76 people wrote a review, and when they write, the average falls to 3.66. 22 of them gave one star, and none got a reply. Over time, the rating dipped in 2023 before recovering this year. The priority matrix shows where to act: [theme in Fix first] is mentioned often and mostly negatively, while [best theme] is a clear strength. And the diagnosis turns it into three actions, for example: [read one action].

Keep the tone constructive: show how the school could improve the experience of students and visitors.

## 2:20 to 3:35, live test 2: a restaurant

On screen: load the restaurant file, choose Restaurant. Show the main figures, filter on 1 to 2 stars, then the unanswered complaints with a reply draft.

> Now the classic case, a restaurant: [name, or "a restaurant in Paris"]. The average looks fine, but [X]% of written reviews are negative, mostly about [theme] and [theme]. Let's filter on one and two-star reviews: the whole dashboard updates instantly. Here are the complaints nobody answered, [N] of them. Take this one: [summarize the review in one sentence]. ReviewPulse has already drafted a reply in French that answers the actual complaint. The owner reads it, adjusts it and posts it.

## 3:35 to 4:05, can we trust it?

On screen: the reliability line under Star ratings, then the Model evaluation section and its confusion matrix.

> Can we trust the AI? Every review comes with the stars its author gave, so we can check. On these reviews, the model agrees with customers [X]% of the time, against [Y]% for a naive guess. It struggles most with mixed three-star reviews, which is why the replies stay drafts that a person approves.

## 4:05 to 4:35, value at scale

On screen: the published report on GitHub Pages, then the README and its Open in Colab button.

> Large chains pay consultants for this analysis. Most independent businesses can't. With ReviewPulse, any owner gets it for free, in minutes, and can answer every unhappy customer while it still matters. Each analysis can also be published as a permanent report, like this one.

## 4:35 to 4:50, close

On screen: the name, the team members and the GitHub link.

> ReviewPulse: from hundreds of reviews to three clear actions. The code, the data and the user guide are on GitHub, and anyone can run it in one click. Thank you.

## Before recording

Run the notebook and both analyses before you start, and keep the application open in a full-screen browser tab at 100% zoom, with bookmarks and notifications hidden. Record each section separately and assemble them afterwards, which makes it easier to stay on time. Check that the final video lasts between 4:30 and 5:30, and show the GitHub link on the last screen.
