# Demo video script (target 4:50, allowed 4:30 to 5:30)

Narration is about 640 words, which is roughly 4:45 at a calm pace. Record the screen in 1080p, record the voice separately with a decent microphone, and cut every loading wait during editing. Fill in the [brackets] with the real figures from your analyses.

## 0:00 to 0:35 · The problem

Screen: a Google Maps page of a restaurant, scrolling through hundreds of reviews. Then a counter "1,000+ reviews".

> Imagine you run a restaurant. You have six hundred Google reviews, and ten more every week. You do not have time to read them. So you look at the average, 4.2 stars, and move on. But hidden in those reviews are the exact reasons customers do not come back. And some of the angriest reviews never got an answer, even though every future customer can read them.

## 0:35 to 1:05 · The solution

Screen: ReviewPulse title card, then the architecture diagram from the README.

> This is ReviewPulse. You give it the reviews of any business, and in about two minutes it tells you what customers love, what frustrates them, which complaints were never answered, and how to reply. Under the hood, three open-source models from Hugging Face work together: a multilingual sentiment model, a zero-shot model that detects themes without any training, and a small language model that writes the diagnosis and the replies. Everything runs for free in Google Colab.

## 1:05 to 2:20 · Live test 1: ESSEC

Screen: the Gradio app. Select the ESSEC dataset, business type "School / University", click Analyze. Cut the wait. Show the Overview tab.

> Let's start with a business everyone here knows: ESSEC. We collected [N] public Google reviews. [X]% are positive. The theme chart shows what people talk about: [best theme] is the clear strength, while [weakest theme] gets the most criticism. ReviewPulse turns this into a diagnosis with three priority actions, for example: [read one action]. In a few seconds we get what would take hours of reading, and we can see it is grounded in real reviews.

Keep the tone constructive: you are showing how ESSEC could improve the student and visitor experience.

## 2:20 to 3:40 · Live test 2: a restaurant

Screen: load the restaurant dataset, type "Restaurant". Overview, then the Unanswered reviews tab, then the Reply assistant.

> Now the classic use case: a restaurant, [name or "a restaurant in Paris"]. The average rating looks fine, but [X]% of reviews are negative, mostly about [theme] and [theme]. And here is the striking part: [N] negative reviews never received an answer. They are public, and they are the first thing a hesitant customer reads. Let's pick one. [Read the review in one sentence.] One click, and ReviewPulse drafts a reply in French, specific to the complaint, polite, and ready for the owner to adapt and post.

## 3:40 to 4:10 · Can we trust it?

Screen: Model evaluation tab, then the confusion matrix.

> Can we trust the AI? Every review comes with the stars the customer gave, so we can check. On the restaurant reviews, the model agrees with customers [X]% of the time, versus [Y]% for a naive baseline. Its weak spot is mixed three-star reviews, which is why the replies stay drafts reviewed by a human.

## 4:10 to 4:40 · Value at scale

Screen: the GitHub Pages report, then the README "Open in Colab" button.

> There are millions of independent businesses that cannot afford customer-insight consultants. Used widely, ReviewPulse would give each of them, for free, a clear view of what to fix, and a way to answer every unhappy customer within minutes. Every analysis can also be published as a permanent report, like this one.

## 4:40 to 4:55 · Close

Screen: title card with the project name, team names, GitHub link.

> ReviewPulse: from hundreds of reviews to three clear actions. The code, data and user guide are on GitHub, and you can run it yourself in one click. Thank you.

## Recording checklist

- Run the notebook and both analyses before recording; keep the app open in a full-screen browser tab at 100% zoom.
- Hide bookmarks and notifications; use a clean browser profile.
- Record each section separately, then assemble; it is easier to stay within time.
- Check the final duration: between 4:30 and 5:30.
- Add the GitHub link in the video description or on the last slide.
