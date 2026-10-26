# Supermarket Assistant Chatbot

A simple Python desktop chatbot that helps a customer search for supermarket products from plain English requests and shows the product shelf location.

## What it does

- Reads customer requests like "I need apples, milk and detergent"
- Recognises products and common variations such as plurals and synonyms
- Corrects small spelling mistakes using fuzzy matching
- Detects product quantities such as "2 apples" or "two milks"
- Looks up the product shelf and category from a JSON catalog
- Shows results in a Tkinter window
- Saves a shopping summary file if requested

## Project files

- main.py - main application logic and Tkinter GUI
- product_database.json - product catalog with shelf numbers, categories and synonyms
- requirements.txt - Python dependencies
- shopping_summary.txt - generated shopping summary output
- README.txt - project instructions

## Technologies used

- Python
- Tkinter
- spaCy
- RapidFuzz
- JSON

## Requirements

Make sure Python is installed first.

Required packages:

- spacy
- rapidfuzz

The spaCy English model is also needed for the best NLP results:

python -m spacy download en_core_web_sm

## Installation

Open a terminal in the project folder and run:

pip install -r requirements.txt

Then install the language model:

python -m spacy download en_core_web_sm

## Run the app

From the project directory:

python main.py

## Example requests

- apple, milk, bread
- I need rice and sugar
- I want apples, milk and detergent
- I need aple, bred and coffe
- give me eggs and a loaf
- 2 apples and 3 eggs
- a bottle of soap

## Notes

- The app is designed as a small university-level NLP project.
- If the spaCy model is not installed, the program can still run in a basic mode, but product recognition may be less accurate.
- The product list and shelf assignments are stored in product_database.json and can be adjusted easily.
- The shopping summary is written to shopping_summary.txt when the user clicks the summary button.
