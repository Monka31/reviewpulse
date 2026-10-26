# Data

## Datasets in the repository

`data/reviews_ESSEC_Cergy.csv` holds 250 Google Maps reviews of the ESSEC Business School Cergy-Pontoise campus, collected with Outscraper on October 25, 2026. They run from November 2020 to October 2026. 76 reviews have a text and 174 are star-only ratings. The Google Maps listing showed 382 reviews in total at the time of collection, so the file covers about two thirds of them. The export contained no reply from the school to any review.

`data/reviews_<restaurant>.csv` [to add: the restaurant used in the second demo, collected the same way.]

`data/demo_restaurant_synthetic.csv` holds 30 reviews of a fictional restaurant, "Demo Bistro", written by the team to test the application. They are synthetic, labeled as such in the file, and never presented as real data.

## Format

Every dataset uses the same five columns. `place` is the name of the business. `date` is the publication date of the review (UTC). `rating` is the number of stars given by the author, from 1 to 5. `text` is the review, empty for star-only ratings. `owner_answer` is the public reply of the business, empty when there is none.

The application also reads other formats, such as raw Outscraper exports, Kaggle datasets or a spreadsheet typed by hand. The user guide lists the column names it recognizes.

## Collection

Reviews were collected with the Outscraper Google Maps Reviews service (https://outscraper.com), which returns the reviews of a place with their text, stars, date and owner reply. The export was converted with `scripts/collect_reviews_outscraper.py`, which keeps the five columns above and discards everything else. The same script can collect reviews directly through the Outscraper API with a personal key, read from an environment variable and never stored in the code.

Before choosing Outscraper, we looked at the Yelp Open Dataset on Kaggle, which has almost no French businesses, and at the official Google Places API, which returns only five reviews per place.

## Privacy

The raw Outscraper export contains the name, profile link, identifier and photo of each reviewer. None of these are kept: the collection script drops them, and the application also drops them when a raw export is loaded directly. The repository contains no personal data about reviewers. The data is used for analysis only.

Google reviews are public, but large-scale automated collection may conflict with Google's terms of service. This project is an academic prototype built on a small number of places, not a data collection service.
