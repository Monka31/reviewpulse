# AI tools and prompts log

The assignment asks us to show where and how we used AI tools, with the prompts. This log covers the AI assistants used to design and build ReviewPulse, then the prompts the application itself sends to its language model.

## 1. AI assistants used

We used Claude (Anthropic, on claude.ai) throughout the project: to choose the idea and the data source, to compare architectures, to write and debug the code, to design the interface and to draft the documentation and the video script. No other AI assistant, such as ChatGPT or GitHub Copilot, was used. The voice of the demo video is also produced by an AI model (Microsoft neural voices through edge-tts, or the open-source Kokoro model from Hugging Face), as described in the technical report.

The complete conversation, with every prompt quoted word for word and a summary of each answer, is in [conversation_transcript.md](conversation_transcript.md). The section below groups the same prompts by topic.

The prompts were written in French. Each one is quoted in French, followed by an English translation and the outcome. Every output was read, tested and corrected by the team before being kept. When code failed in Colab, we pasted the error message back and asked for a fix, so several prompts below are error reports.

## 2. Prompts used to build the project

### Understanding the assignment and organizing the team

Prompt 1. We uploaded the assignment PDF with "J'ai ce projet : [instructions de l'enseignant]" (I have this project: [teacher's instructions]). The assistant summarized the grading scheme, pointed out that reproducibility, duration compliance and documentation were points we could secure early, and suggested three first ideas: a customer-success copilot, a sales objection coach and a review analyzer.

Prompts 2 and 3. "Je vais créer un groupe avec tous les membres, fais-moi le message de bienvenue, fais tout en anglais en demandant si tout le monde est francophone. Demande comment ils veulent se répartir la tâche" (I am creating a group chat with all members, write the welcome message in English, ask whether everyone speaks French and how they want to split the work), then "S'ils ont déjà des idées etc" (and whether they already have ideas). The assistant drafted the welcome message with a proposed split into four roles.

### Choosing the idea

Prompt 4. "Quel projet pourrait être intéressant à faire, facile, rapide, utile, et qui utiliserait les bibliothèques présentées ?" (Which project would be interesting, easy, fast, useful, and use the presented libraries?) The assistant recommended a review analyzer built from pre-trained Hugging Face models, with a demo outline.

Prompt 5. "Peux-tu me faire plus de propositions de projet stp" (Can you give me more project ideas?) It proposed eleven ideas across marketing, sales, document processing and computer vision.

Prompt 6. "Donne une idée simple qui réponde aux critères, il faut que je puisse le faire rapidement" (Give one simple idea that meets the criteria, I must be able to build it quickly). It confirmed the review analyzer and gave a one-day build plan.

### Finding the data

Prompt 7. "Puis-je de mon côté récupérer les infos de n'importe quel magasin ou commerce pour ma démo ?" (Can I get the data of any store or business for my demo?) The assistant compared copying reviews by hand, the Google Places API (five reviews per place), open datasets and scraping, with the legal and privacy caveats.

Prompt 8. "Montre-moi comment avoir un fichier CSV avec tous les avis d'une entreprise, commerce, restaurant peu importe" (Show me how to get a CSV with all the reviews of any business). It wrote a script extracting one business from the Yelp Open Dataset. We did not use it, because Yelp has almost no French businesses.

Prompt 9. "Je veux le faire avec des commerces français, par exemple, super exemple, je veux le faire avec tous les avis qu'il y a sur l'ESSEC" (I want French businesses, for example all the reviews about ESSEC). It listed where ESSEC reviews can be found and how to collect them.

Prompt 10. "Est-il possible de faire une extension Chrome qui, en fonction de la page d'avis où l'on est, analyse tout seul ?" (Could a Chrome extension analyze the review page you are on?) It explained that it was feasible but longer to build and harder for graders to reproduce. We dropped the idea: "ok on oublie, faisons quelque chose de simple où l'on fournit un fichier CSV" (let's forget it and keep it simple, with a CSV file).

Prompts 11 and 12. "Peut-on le faire avec Apify ?" (Can we do it with Apify?), with the documentation of an Apify actor, then "ok faisons avec Outscraper : [exemple de sortie JSON]" (let's use Outscraper: [sample JSON output]). The assistant wrote the collection script that keeps only the text, stars, date and owner reply and drops every reviewer identity. It later became `scripts/collect_reviews_outscraper.py`.

### Explaining the project to the group

Prompts 13 to 15. "Peux-tu me faire le texte d'explication pour mon groupe pour leur expliquer le projet, l'intérêt etc, que pendant la démo on peut faire un test avec l'ESSEC, un test avec un restaurant afin de montrer les axes d'amélioration, les messages non répondus" (write a message explaining the project and its value to the group, with a demo testing ESSEC and a restaurant to show improvement areas and unanswered reviews), then a French version, then "Fais un message plus court sans emoji, qui ne fait pas IA" (make it shorter, without emojis, so it does not sound AI-written).

### Architecture decisions

Prompt 16. "Partons sur ce projet, que devons-nous faire ? La structure ? Quoi utiliser ? Tout est gratuit ? Dépôt GitHub ?" (What do we need to do, what structure, which tools, is everything free, GitHub repository?) The assistant proposed the repository structure, the free stack and a planning.

Prompts 17 to 19. "On fait quelque chose en local ou en ligne ?" (local or online?), "Comment se compose l'appli ? Comment est-elle hébergée, comment elle tourne ?" (what are the parts of the app, how is it hosted and run?) and "C'est un peu nul que ce soit périssable, ne peut-on pas faire quelque chose sur Supabase, Vercel ou autre pour avoir un lien permanent ?" (the temporary link is a pity, could we use Supabase or Vercel for a permanent link?). The assistant explained the Colab and Gradio setup, then compared Vercel with Supabase and Hugging Face Spaces.

Prompts 20 and 21. "Si on part sur Google Colab, combien de temps prendrait une analyse ?" (how long would an analysis take on Colab?) and "Donc concrètement, avec du recul et de la critique, que devons-nous faire ?" (stepping back critically, what should we do?). The assistant advised against the extra infrastructure, recommended Colab with Gradio for the application and GitHub Pages for permanent static reports, an evaluation against customer stars, and a 3-billion-parameter language model for better French. We followed this advice.

### Building the application

Prompt 22. "Fais l'appli complète, fais tout ce que tu peux faire, pense à tout, mets-toi à la place d'un développeur senior qui doit rendre la chose simple et facilement reproductible. Ensuite dis-moi ce qu'il me manque à faire." (Build the complete app, think of everything, act as a senior developer who must keep it simple and easily reproducible, then tell me what is left for me to do.) The assistant wrote the package, the Gradio application, the notebook, the report export, the tests and the first documentation, checked them with automated tests and an end-to-end run using tiny local models, and listed the remaining tasks.

Prompts 23 to 25. "Fais-moi la description du repo GitHub et tous les paramètres à activer ou non" (write the repository description and tell me which settings to enable), "Comment le déployer et utiliser l'outil ? Je ne vois pas Website" (how do I deploy and use it? I cannot find the Website field) and "Quoi mettre ici" (what goes here?) with a screenshot of the repository settings.

Prompt 26. "Voici un exemple de template avis (c'est celui de l'ESSEC), l'app est optimisée pour ?" (here is a review export, the ESSEC one: is the app optimized for it?), with the Outscraper Excel file. Testing it revealed three problems: the app read the place-level average (4.4) instead of each review's stars, kept HTML tags in the texts, and ignored star-only ratings. The assistant fixed all three, added a regression test and adjusted the school themes to what the reviews discuss (admissions, staff and welcome).

Prompts 27 to 29. Questions on how to use the app ("Comment fonctionne l'appli ? Je dois déposer les avis sur GitHub ? Je ne peux pas poser le Excel sur l'appli directement ?", how does it work, do I have to put the reviews on GitHub, can't I drop the Excel file directly?) and error reports from Colab: "Could not find ReviewPulse.ipynb", then "FileNotFoundError: data/reviews_ESSEC_Cergy.csv". The causes were an upload that had put the files in a subfolder, then a stale copy of the repository in Colab. The notebook now pulls the latest version on every run.

### Redesigning the interface

Prompt 30. "Je n'aime pas du tout l'interface de l'appli, peux-tu m'aider à changer le template ? Cela marche en HTML ? Comment ? Ne fais pas de modif avant ma validation" (I do not like the interface, can you change it, does it work with HTML, do not change anything before I approve). The assistant proposed three options and we chose the second: Gradio controls with an HTML dashboard ("ok partons sur l'option B si elle est facile de mise en place").

Prompts 31 to 33. The assistant drew a mockup of the dashboard for validation. We asked for "le bleu clair ESSEC" (ESSEC light blue), then "Peut-on ajouter des graphes ? J'aimerais pouvoir voir des camemberts etc ou d'autres graphes en fonction d'infos ou données particulières. Interface en anglais" (can we add charts, such as pie charts, depending on specific information? Interface in English). It added the five charts of the Insights section and the period, stars and theme filters. We approved with "go".

Prompts 34 to 36. Error reports after the redesign: "AttributeError: module 'reviewpulse' has no attribute 'run_pipeline'", twice, then an assertion error. The first cause was a name clash between the folder Colab cloned and the Python package, fixed by cloning into `reviewpulse_app`. The second was an incomplete upload to GitHub.

Prompt 37. "Penses-tu cela possible de faire en sorte qu'aucun texte ne se superpose ? Est-il également possible d'ajouter un tableau avec tous les avis ? Répondus ou pas, avec ou sans texte, tout dans un tableau" (can you make sure no text overlaps, with a screenshot of the priority matrix, and add a table with every review, answered or not, with or without text?). The matrix now uses numbered dots with a list under the chart, and the dashboard ends with a table of every review.

### Documentation

Prompt 38. "Peux-tu stp me faire toute la doc explicative, tout tout tout, répondant au cahier des charges" (write all the documentation, everything, matching the assignment), with a request to make the text sound human rather than AI-generated. The assistant wrote this log, the README, the user guide, the technical report, the data notes and the updated video script.

### Automated demo video

Prompts 39 to 43. "Penses-tu qu'il serait possible de faire une démo automatisée avec une voix off qui explique tout ?" (could the demo be automated, with a voice-over explaining everything?), "Peut-on le faire uniquement avec le fichier ESSEC ? Cela suffit-il ?" (can we do it with the ESSEC file only, is that enough?), "Comment automatiser la démo ?" (how would we automate it?), "Je veux tout automatiser à 100 %, est-ce possible ?" (I want it 100% automated, is that possible?) and "Je veux le faire uniquement avec les données de l'ESSEC, automatise tout, je veux que la démo puisse montrer le GitHub, le Google Colab, lance l'analyse, lance l'outil, défile tout, explique tout" (only the ESSEC data, automate everything, show GitHub and Colab, run the analysis, open the tool, scroll through everything and explain it all). The assistant compared a fully automated video with a recording narrated by the team, pointed out that a synthetic voice could cost points on delivery, and built `reviewpulse/demo_video.py` and section 8 of the notebook. The narration is written from the analysis results, so the video quotes only figures the application computed.

### Checking the demo against the assignment

Prompt 44. "Es-tu sûr que la vidéo de démo répond à tout ?" (Are you sure the demo video covers everything?), with the assignment and its grading scheme. The assistant compared the narration with each criterion. The name, the purpose, the market need, reproducibility, the cited tools and the duration were covered, but the video did not link the models to the concepts of the course, did not say why the project goes beyond the course, and said little about the value of the tool if it were widely used. It also found unfinished placeholders in the documentation.

Prompt 45. "J'aimerais que tu ajoutes à la vidéo ces différents points, ajoute qu'Outscraper nous a donné 250 avis sur l'ESSEC et non les 382 qu'il y a en ligne. Rends à la vidéo un peu plus de côté technique et montre la facilité d'implémentation et de répétabilité, c'est ce qui est demandé." (Add these points to the video, say that Outscraper gave us 250 ESSEC reviews rather than the 382 online, make the video more technical and show how easy it is to implement and repeat), followed by the names of the team members and "Peux-tu faire un extract de tous mes prompts ainsi que tes réponses et les intégrer ?" (extract all my prompts and your answers and add them to the documentation). The narration now gives the 250 out of 382 figure, names the course concept behind each model and explains the value at scale. Two shots were added, an architecture screen and a reproducibility screen, and two repetitive shots were removed to stay under five minutes. The full conversation was exported to `conversation_transcript.md`.

## 3. Prompts used inside the application

ReviewPulse sends two kinds of prompts to `Qwen/Qwen2.5-3B-Instruct`. Their exact text is in `reviewpulse/llm.py`.

The diagnosis prompt uses this system message: "You are a customer-experience consultant. You analyze online reviews for a business owner and give short, concrete, evidence-based advice. Never invent facts that are not supported by the data or the review excerpts you are given." The user message gives the business name and type, the number of reviews, the sentiment split, the average rating and reply rate, the mentions and net score of each theme, eight negative and five positive review excerpts, and asks for three Markdown sections (strengths, areas for improvement, three priority actions) in under 220 words and in the chosen language.

The reply prompt uses this system message: "You write public replies to customer reviews on behalf of a business. Replies are warm, professional, specific to what the customer wrote, and never defensive." The user message gives the business, the review and its stars, with these rules: write in the same language as the review, 60 to 110 words, thank the customer and acknowledge the specific issue, say what will be done, never blame the customer, never promise refunds or discounts, never invent facts, invite direct contact and sign as the business team.

We wrote the prompts this way so the model works from computed figures and real excerpts instead of guessing, follows a fixed output format that the dashboard can display, and stays within limits a business could accept. Generation is deterministic, so the same data gives the same text.
