# AI tools and prompts log

The assignment asks to report where and how AI tools were used. This file lists (1) the AI assistants used to design and build the project, with the prompts we gave them, and (2) the prompts the application itself sends to its language model.

## 1. AI assistants used during the project

| Tool | Used for |
|---|---|
| Claude (Anthropic), claude.ai | Brainstorming project ideas, choosing the data source, architecture choices, writing the code, documentation, tests and video script |
| _add other tools if used (ChatGPT, GitHub Copilot...)_ | |

Prompts were written in French; the English translation is given in brackets. Answers were reviewed, tested and adapted by the team.

### Ideation

1. Uploaded the assignment PDF, then: "J'ai ce projet : [assignment instructions]" (I have this project: [instructions]).
   Outcome: analysis of the grading scheme and three first ideas (customer-success copilot, sales objection coach, review analyzer).
2. "Quel projet pourrait être intéressant à faire, facile, rapide, utile, et qui utiliserait les bibliothèques présentées ?" (Which project would be interesting, easy, fast, useful, and use the presented libraries?)
   Outcome: recommendation of a review analyzer built from pre-trained Hugging Face models.
3. "Peux-tu me faire plus de propositions de projet stp" (Can you give me more project proposals?)
   Outcome: 11 ideas across marketing, sales, documents and computer vision.
4. "Donne une idée simple qui réponde aux critères, il faut que je puisse le faire rapidement" (Give one simple idea that meets the criteria, I must be able to build it quickly)
   Outcome: final choice of the review analyzer, with a one-day plan.

### Data collection

5. "Puis-je de mon côté récupérer les infos de n'importe quel magasin ou commerce pour ma démo ?" (Can I get the data of any store or business for my demo?)
   Outcome: comparison of manual copy, Google Places API (5 reviews max), open datasets and scraping, with legal and GDPR caveats.
6. "Montre-moi comment avoir un fichier CSV avec tous les avis d'une entreprise" (Show me how to get a CSV with all the reviews of a business)
   Outcome: extraction script for the Yelp Open Dataset (not used in the end: no French businesses).
7. "Je veux le faire avec des commerces français [...] avec tous les avis qu'il y a sur l'ESSEC" (I want French businesses [...] all the reviews about ESSEC)
   Outcome: sources of ESSEC reviews and a manual collection method.
8. "Est-il possible de faire une extension Chrome qui, en fonction de la page d'avis où l'on est, analyse tout seul ?" (Could a Chrome extension analyze the review page you are on?)
   Outcome: feasible but judged too long and harder to reproduce; dropped.
9. "Peut-on le faire avec Apify ?" then "Ok faisons avec Outscraper : [example of Outscraper JSON output]" (Can we do it with Apify? / Let's use Outscraper: [sample output])
   Outcome: Outscraper chosen; script `scripts/collect_reviews_outscraper.py` that keeps only text, stars, date and owner reply (reviewer identities removed).

### Architecture

10. "On fait quelque chose en local ou quelque chose en ligne ?" (Should we build it locally or online?)
    Outcome: Google Colab with a free GPU as the main environment.
11. "C'est un peu nul que ce soit périssable, ne peut-on pas faire quelque chose sur Supabase, Vercel ou autre pour avoir un lien permanent ?" (The temporary link is a pity, could we use Supabase, Vercel or similar for a permanent link?)
    Outcome: comparison of Vercel + Supabase and Hugging Face Spaces.
12. "Si on part sur Google Colab, combien de temps prendrait une analyse ?" (With Google Colab, how long would an analysis take?)
    Outcome: time estimates per step and ideas to speed things up (replies on demand).
13. "Donc concrètement, avec du recul et de la critique, que devons-nous faire ?" (So, stepping back critically, what should we do?)
    Outcome: Colab + Gradio as the product, static HTML reports on GitHub Pages for a permanent link without extra infrastructure, an evaluation section against customer stars, and a 3B LLM for better French.

### Build

14. "Fais l'appli complète, fais tout ce que tu peux faire, pense à tout, mets-toi à la place d'un développeur senior qui doit rendre la chose simple et facilement reproductible. Ensuite dis-moi ce qu'il me manque à faire." (Build the complete app, do everything you can, think of everything, act as a senior developer who must keep it simple and easily reproducible. Then tell me what is left for me to do.)
    Outcome: this repository (package, Gradio app, notebook, HTML reports, tests, documentation). The code was checked with automated tests and an end-to-end run before delivery.

_Add here the prompts used later (bug fixes, video script edits, slides...)._

## 2. Prompts used inside the application

ReviewPulse sends two kinds of prompts to `Qwen/Qwen2.5-3B-Instruct`. The exact text lives in `reviewpulse/llm.py`; summarized here:

**Executive summary.** System: "You are a customer-experience consultant. You analyze online reviews for a business owner and give short, concrete, evidence-based advice. Never invent facts that are not supported by the data or the review excerpts you are given." The user message contains the business name and type, the sentiment split, average rating and reply rate, the per-theme counts, 8 negative and 5 positive review excerpts, and asks for three Markdown sections (strengths, areas for improvement, 3 priority actions) in under 220 words.

**Reply draft.** System: "You write public replies to customer reviews on behalf of a business. Replies are warm, professional, specific to what the customer wrote, and never defensive." The user message contains the review and its stars, and these rules: same language as the review, 60 to 110 words, thank the customer and acknowledge the specific issue, no blame, no promised refunds, no invented facts, invite direct contact, sign as the business team.

Design choices: the model receives computed statistics and real excerpts (grounding) rather than being asked to read hundreds of reviews; output formats and length limits are explicit; generation is deterministic (`do_sample=False`) so results are reproducible.
