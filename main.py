import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher
import tkinter as tk
from tkinter import messagebox, scrolledtext

# RapidFuzz for spelling correction / fuzzy matching
try:
    from rapidfuzz import process as rf_process, fuzz as rf_fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    rf_process = None
    rf_fuzz = None
    RAPIDFUZZ_AVAILABLE = False

# spaCy for advanced NLP (tokenisation, POS, lemmatisation, NER)
try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
        NLP_MODE = "spaCy"
    except OSError:
        # spaCy installed but model not downloaded yet
        nlp = None
        NLP_MODE = "Basic"
except ImportError:
    nlp = None
    NLP_MODE = "Basic"


# ---------------------------------------------------------------------------
# Words that should never be treated as product candidates
# ---------------------------------------------------------------------------
STOPWORDS = {
    "hello", "hi", "hey", "thanks", "thank", "please", "i", "am", "want",
    "need", "planning", "plan", "cook", "tonight", "today", "tomorrow",
    "so", "and", "to", "buy", "get", "find", "me", "for", "the", "a", "an",
    "some", "is", "are", "can", "could", "would", "show", "help", "like",
    "you", "came", "come", "also", "much", "many", "few", "lot",
    "lots", "couple", "pack", "packet", "bag", "box", "bottle", "tin",
    "jar", "piece", "pieces", "item", "items", "thing", "things", "stuff"
}

# Minimum fuzzy score thresholds
RAPIDFUZZ_THRESHOLD = 82   # out of 100 (RapidFuzz token_set_ratio)
DIFFLIB_THRESHOLD = 0.78   # ratio (0-1 scale)


class SupermarketChatbotApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Supermarket Assistant Chatbot")
        self.root.geometry("820x680")
        self.root.configure(bg="#F0F4F8")

        self.db_filename = "product_database.json"
        self.product_db = self.load_product_database()
        self.last_detected_items = []   # stores last search results for summary

        self.create_widgets()
        self.show_welcome_message()

    # ------------------------------------------------------------------
    # Database loading
    # ------------------------------------------------------------------

    def load_product_database(self):
        """Load product catalogue from product_database.json.
        Falls back to built-in defaults if the file is missing or broken."""
        default_db = {
            "apple":     {"shelf": "Shelf 1", "category": "Fresh Produce",        "synonyms": ["apples", "fresh apple", "green apple", "red apple"]},
            "milk":      {"shelf": "Shelf 3", "category": "Dairy and Chilled",    "synonyms": ["milks", "fresh milk", "whole milk", "skimmed milk"]},
            "bread":     {"shelf": "Shelf 2", "category": "Bakery",               "synonyms": ["breads", "loaf", "sliced bread", "white bread"]},
            "rice":      {"shelf": "Shelf 4", "category": "Grains and Pasta",     "synonyms": ["basmati rice", "white rice", "grain"]},
            "sugar":     {"shelf": "Shelf 4", "category": "Pantry and Baking",    "synonyms": ["white sugar", "cane sugar"]},
            "coffee":    {"shelf": "Shelf 6", "category": "Beverages",            "synonyms": ["coffee beans", "instant coffee", "espresso"]},
            "tea":       {"shelf": "Shelf 6", "category": "Beverages",            "synonyms": ["tea bags", "black tea", "green tea"]},
            "shampoo":   {"shelf": "Shelf 8", "category": "Personal Care",        "synonyms": ["hair shampoo", "anti-dandruff shampoo"]},
            "soap":      {"shelf": "Shelf 8", "category": "Personal Care",        "synonyms": ["bath soap", "body soap", "hand soap"]},
            "detergent": {"shelf": "Shelf 5", "category": "Household Cleaning",   "synonyms": ["washing powder", "laundry detergent"]},
            "biscuit":   {"shelf": "Shelf 7", "category": "Snacks",               "synonyms": ["biscuits", "cookies", "crackers"]},
            "juice":     {"shelf": "Shelf 6", "category": "Beverages",            "synonyms": ["orange juice", "fruit juice"]},
            "eggs":      {"shelf": "Shelf 3", "category": "Dairy and Chilled",    "synonyms": ["egg", "fresh eggs"]},
            "chocolate": {"shelf": "Shelf 7", "category": "Snacks",               "synonyms": ["dark chocolate", "milk chocolate", "chocolates"]},
            "toothpaste":{"shelf": "Shelf 8", "category": "Personal Care",        "synonyms": ["dental paste", "tooth paste"]},
        }

        if os.path.exists(self.db_filename):
            try:
                with open(self.db_filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load {self.db_filename}: {e}. Using defaults.")
                return default_db

        # File does not exist - write defaults and return them
        try:
            with open(self.db_filename, "w", encoding="utf-8") as f:
                json.dump(default_db, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not write {self.db_filename}: {e}")
        return default_db

    # ------------------------------------------------------------------
    # GUI construction
    # ------------------------------------------------------------------

    def create_widgets(self):
        """Build all Tkinter widgets."""

        # Header banner
        header = tk.Frame(self.root, bg="#065F46", height=90)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Supermarket Assistant Chatbot",
            font=("Segoe UI", 20, "bold"),
            fg="#FFFFFF", bg="#065F46"
        ).pack(pady=(14, 2))

        tk.Label(
            header,
            text="Find Products and Shelf Locations Instantly",
            font=("Segoe UI", 11),
            fg="#A7F3D0", bg="#065F46"
        ).pack()

        # NLP mode indicator in header corner
        tk.Label(
            header,
            text=f"NLP: {NLP_MODE}",
            font=("Segoe UI", 8),
            fg="#6EE7B7", bg="#065F46"
        ).place(relx=1.0, rely=1.0, anchor="se", x=-8, y=-4)

        # Input area
        input_frame = tk.LabelFrame(
            self.root,
            text="  Customer Request  ",
            font=("Segoe UI", 10, "bold"),
            bg="#F0F4F8", fg="#1F2937",
            padx=8, pady=6
        )
        input_frame.pack(fill=tk.X, padx=14, pady=10)

        tk.Label(
            input_frame,
            text="Type what you want to buy (e.g. 'I need 2 apples, milk and detergent'):",
            font=("Segoe UI", 9),
            bg="#F0F4F8", fg="#374151"
        ).pack(anchor=tk.W, padx=4, pady=(0, 4))

        entry_row = tk.Frame(input_frame, bg="#F0F4F8")
        entry_row.pack(fill=tk.X)

        self.input_entry = tk.Entry(
            entry_row,
            font=("Segoe UI", 12),
            relief=tk.SOLID, bd=1,
            fg="#111827", bg="#FFFFFF"
        )
        self.input_entry.pack(side=tk.LEFT, padx=(4, 8), pady=4, expand=True, fill=tk.X)
        self.input_entry.bind("<Return>", lambda _e: self.process_request())

        tk.Button(
            entry_row,
            text="Find Shelves",
            font=("Segoe UI", 10, "bold"),
            bg="#2563EB", fg="white",
            activebackground="#1D4ED8",
            relief=tk.FLAT, padx=14, pady=6,
            cursor="hand2",
            command=self.process_request
        ).pack(side=tk.RIGHT, padx=4)

        # Output area
        output_frame = tk.LabelFrame(
            self.root,
            text="  Chatbot Response and Shelf Locations  ",
            font=("Segoe UI", 10, "bold"),
            bg="#F0F4F8", fg="#1F2937"
        )
        output_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=2)

        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            font=("Consolas", 11),
            bg="#FFFFFF", fg="#1F2937",
            padx=12, pady=10,
            relief=tk.FLAT
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Colour tags for rich output display
        self.output_text.tag_config("header",    font=("Segoe UI", 12, "bold"), foreground="#065F46")
        self.output_text.tag_config("subheader", font=("Segoe UI", 10, "bold"), foreground="#1F2937")
        self.output_text.tag_config("found",     foreground="#065F46")
        self.output_text.tag_config("notfound",  foreground="#B91C1C")
        self.output_text.tag_config("info",      foreground="#6B7280", font=("Consolas", 10, "italic"))
        self.output_text.tag_config("separator", foreground="#9CA3AF")
        self.output_text.tag_config("user_text", foreground="#1E40AF")
        self.output_text.tag_config("quantity",  foreground="#7C3AED")

        # Action buttons
        btn_frame = tk.Frame(self.root, bg="#F0F4F8")
        btn_frame.pack(fill=tk.X, padx=14, pady=10)

        tk.Button(
            btn_frame,
            text="🖨️  Generate Shopping Summary File",
            font=("Segoe UI", 10, "bold"),
            bg="#059669", fg="white",
            activebackground="#047857",
            relief=tk.FLAT, padx=14, pady=6,
            cursor="hand2",
            command=self.generate_summary
        ).pack(side=tk.LEFT)

        tk.Button(
            btn_frame,
            text="Clear Output  ✕",
            font=("Segoe UI", 10),
            bg="#9CA3AF", fg="white",
            activebackground="#6B7280",
            relief=tk.FLAT, padx=12, pady=6,
            cursor="hand2",
            command=self.clear_output
        ).pack(side=tk.RIGHT)

    def show_welcome_message(self):
        """Display a greeting in the output area when the app starts."""
        self._write("\n  Welcome to the Supermarket Assistant!\n\n", "header")
        self._write("  How to use:\n", "subheader")
        self._write("  - Type what you want to buy in plain English.\n")
        self._write("  - Spelling mistakes and alternative names are handled automatically.\n")
        self._write("  - You can include quantities, e.g. '2 apples and a milk'.\n")
        self._write("  - Press Enter or click Find Shelves to search.\n\n")
        self._write(f"  NLP engine: {NLP_MODE}\n", "info")
        if NLP_MODE == "Basic":
            self._write("  Tip: Install the spaCy model for better accuracy:\n", "notfound")
            self._write("       python -m spacy download en_core_web_sm\n", "notfound")
        self._write("\n")

    # ------------------------------------------------------------------
    # Helper: write styled text to the output widget
    # ------------------------------------------------------------------

    def _write(self, text, tag=None):
        """Append text to the output widget with an optional colour tag."""
        if tag:
            self.output_text.insert(tk.END, text, tag)
        else:
            self.output_text.insert(tk.END, text)

    # ------------------------------------------------------------------
    # Text normalisation
    # ------------------------------------------------------------------

    def _normalize(self, text):
        """Lowercase, strip punctuation, collapse whitespace."""
        return re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()

    # ------------------------------------------------------------------
    # Quantity extraction
    # ------------------------------------------------------------------

    def extract_quantities(self, text):
        """Return a dict mapping product word -> integer quantity.

        Handles patterns like:
          '3 apples', 'two milks please', 'a bottle of soap'
        """
        word_to_num = {
            "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4,
            "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
        }
        qty_map = {}
        lower = text.lower()
        words = lower.split()

        for i, word in enumerate(words):
            qty = None

            # Digit quantity: e.g. "3"
            if word.isdigit():
                qty = int(word)

            # Word quantity: e.g. "two", "a"
            elif word in word_to_num:
                qty = word_to_num[word]

            if qty is not None:
                # Look ahead for the first non-stopword, non-digit word
                # (skip container words like "bottle", "bag" which are in STOPWORDS)
                for j in range(i + 1, min(i + 5, len(words))):
                    candidate = re.sub(r"[^a-z]", "", words[j])
                    if candidate and candidate not in STOPWORDS and not candidate.isdigit():
                        qty_map[candidate] = qty
                        break

        return qty_map

    # ------------------------------------------------------------------
    # Product matching helpers
    # ------------------------------------------------------------------

    def _build_lookup(self):
        """Build a flat list of all candidate strings and a dict mapping each to its product key."""
        all_candidates = []
        lookup = {}
        for key, details in self.product_db.items():
            for candidate in [key] + details.get("synonyms", []):
                c = candidate.strip().lower()
                if c and c not in lookup:
                    lookup[c] = key
                    all_candidates.append(c)
        return all_candidates, lookup

    def _is_plural_of(self, word, base):
        """Return True if word looks like a common English plural of base.

        Handles: +s, +es, and y->ies changes.
        Avoids the bug of rstrip('s') which truncates words like 'glass'.
        """
        if word == base + "s":
            return True
        if word == base + "es":
            return True
        if word.endswith("ies") and base.endswith("y") and word[:-3] + "y" == base:
            return True
        return False

    def _match_product(self, phrase):
        """Try to match a phrase to a database product key.

        Priority:
          1. Exact match against product key or any synonym.
          2. Singular / plural variant.
          3. Fuzzy match using RapidFuzz token_set_ratio (or difflib fallback).

        Returns (product_key, score) or (None, 0).
        """
        cleaned = self._normalize(phrase)
        if not cleaned:
            return None, 0

        all_candidates, lookup = self._build_lookup()

        # 1. Exact match
        if cleaned in lookup:
            return lookup[cleaned], 100

        # 2. Singular / plural variant
        for candidate in all_candidates:
            if self._is_plural_of(cleaned, candidate) or self._is_plural_of(candidate, cleaned):
                return lookup[candidate], 100

        # 3. Fuzzy matching
        if RAPIDFUZZ_AVAILABLE:
            result = rf_process.extractOne(
                cleaned, all_candidates,
                scorer=rf_fuzz.token_set_ratio  # better than plain ratio for short terms
            )
            if result:
                matched, score, _ = result
                if score >= RAPIDFUZZ_THRESHOLD:
                    return lookup[matched], score
        else:
            # Fallback to Python's built-in SequenceMatcher
            best_key, best_score = None, 0.0
            for candidate in all_candidates:
                score = SequenceMatcher(None, cleaned, candidate).ratio()
                if score > best_score:
                    best_score = score
                    best_key = candidate
            if best_score >= DIFFLIB_THRESHOLD and best_key:
                return lookup[best_key], round(best_score * 100, 1)

        return None, 0

    # ------------------------------------------------------------------
    # NLP product extraction
    # ------------------------------------------------------------------

    def extract_products(self, user_text):
        """Extract recognised products from user_text using NLP.

        Steps:
          1. Extract quantities (e.g. '3 apples' -> apples: 3).
          2. Collect candidate phrases using spaCy noun chunks + token fallback.
          3. Match each candidate against the product database.
          4. Report user-typed words that were not matched to any product.

        Returns:
            detected - list of dicts: {key, name, shelf, category, quantity}
            unknown  - list of user-typed words that were not matched
        """
        detected = []
        found_keys = set()

        # Step 1: Extract quantities
        qty_map = self.extract_quantities(user_text)

        # Step 2: Collect candidate phrases
        normalized = self._normalize(user_text)
        phrase_candidates = []
        user_word_candidates = []   # actual words typed by the user (for not-found reporting)

        # (a) spaCy-based candidates (noun chunks, lemmas, named entities)
        if nlp is not None:
            doc = nlp(user_text)

            # Noun chunks catch multi-word product names like "orange juice"
            for chunk in doc.noun_chunks:
                words = [re.sub(r"[^a-z]", "", t.text.lower()) for t in chunk]
                words = [w for w in words if w and w not in STOPWORDS and len(w) > 2]
                if words:
                    phrase_candidates.append(" ".join(words))

            # Individual nouns and proper nouns (using both raw form and lemma)
            for token in doc:
                if token.pos_ in ("NOUN", "PROPN"):
                    for form in (token.text.lower(), token.lemma_.lower()):
                        form = form.strip()
                        if form and form not in STOPWORDS and len(form) > 2 and form.isalpha():
                            phrase_candidates.append(form)

            # Named entities labelled as products
            for ent in doc.ents:
                if ent.label_ in {"PRODUCT", "ORG"}:
                    phrase_candidates.append(self._normalize(ent.text))

        # (b) Simple token fallback (always runs, handles basic inputs and spaCy misses)
        for word in normalized.split():
            if word and word not in STOPWORDS and len(word) > 2 and word.isalpha():
                phrase_candidates.append(word)
                user_word_candidates.append(word)  # track user-typed words

        # (c) Multi-word synonyms found literally in the input (highest priority)
        _, lookup = self._build_lookup()
        for candidate in lookup:
            if " " in candidate and candidate in normalized:
                phrase_candidates.insert(0, candidate)

        # Deduplicate while sorting longest-first (more specific matches first)
        seen = set()
        ordered_candidates = []
        for p in sorted(set(phrase_candidates), key=lambda x: (-len(x.split()), x)):
            if p not in seen:
                seen.add(p)
                ordered_candidates.append(p)

        # Step 3: Match each candidate against the database
        matched_words = set()   # tracks which words have already been claimed by a match

        for phrase in ordered_candidates:
            phrase_words = set(phrase.split())
            # Skip if all words in this phrase are already claimed by a previous match
            if phrase_words and phrase_words.issubset(matched_words):
                continue

            key, score = self._match_product(phrase)
            if key and key not in found_keys:
                details = self.product_db[key]

                # Try to find a quantity for this product
                quantity = None
                for w in list(phrase_words) + [key]:
                    if w in qty_map:
                        quantity = qty_map[w]
                        break

                detected.append({
                    "key": key,
                    "name": key.capitalize(),
                    "shelf": details["shelf"],
                    "category": details.get("category", "General"),
                    "quantity": quantity,
                })
                found_keys.add(key)
                matched_words.update(phrase_words)

        # Step 4: Find user-typed words that were not matched to any product
        unknown = []
        seen_unknown = set()
        for word in user_word_candidates:
            if word in seen_unknown or word in matched_words:
                continue
            # Check if the word was matched via fuzzy (just didn't land in matched_words)
            key, _ = self._match_product(word)
            if key:
                continue
            if word.isdigit():
                continue
            unknown.append(word)
            seen_unknown.add(word)

        return detected, unknown

    # ------------------------------------------------------------------
    # Main request handler
    # ------------------------------------------------------------------

    def process_request(self):
        """Handle the Find Shelves button or Enter key press."""
        user_input = self.input_entry.get().strip()

        if not user_input:
            messagebox.showwarning("Input Required", "Please enter a shopping request.")
            return

        detected, unknown = self.extract_products(user_input)
        self.last_detected_items = detected

        # Clear previous output
        self.output_text.delete("1.0", tk.END)

        # --- Customer request ---
        self._write("Customer Request\n", "header")
        self._write(f"  {user_input}\n\n", "user_text")

        # --- Detected products ---
        self._write("Detected Items and Shelf Locations\n", "subheader")
        self._write("-" * 52 + "\n", "separator")

        if detected:
            for item in detected:
                line = f"  - {item['name']:<15} ->  {item['shelf']:<10} ({item['category']})"
                self._write(line, "found")
                if item["quantity"]:
                    self._write(f"  x{item['quantity']}", "quantity")
                self._write("\n")
        else:
            self._write("  No matching products were found.\n", "notfound")

        self._write("-" * 52 + "\n", "separator")

        # --- Unknown words (only genuine user-typed words) ---
        if unknown:
            self._write("\nItems Not in Our Catalogue\n", "subheader")
            self._write("-" * 52 + "\n", "separator")
            for word in unknown:
                self._write(f"  - {word.capitalize()} - not found in product database\n", "notfound")
            self._write("-" * 52 + "\n", "separator")
            self._write("  Tip: check the spelling or ask a staff member for help.\n", "info")

        self._write("\n")
        self.output_text.see(tk.END)
        self.input_entry.delete(0, tk.END)

    # ------------------------------------------------------------------
    # Summary file generation
    # ------------------------------------------------------------------

    def generate_summary(self):
        """Write the current shopping list to a formatted plain-text file."""
        if not self.last_detected_items:
            messagebox.showinfo("No Items", "Please search for products first, then save a summary.")
            return

        filename = "shopping_summary.txt"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            "==========================================",
            "       SUPERMARKET SHOPPING SUMMARY       ",
            "==========================================",
            f"  Date: {now}",
            "------------------------------------------",
            f"  {'Item':<18} {'Qty':<6} {'Shelf':<12} Category",
            "------------------------------------------",
        ]

        for item in self.last_detected_items:
            qty = str(item["quantity"]) if item["quantity"] else "-"
            lines.append(f"  {item['name']:<18} {qty:<6} {item['shelf']:<12} {item['category']}")

        lines += [
            "------------------------------------------",
            f"  Total items: {len(self.last_detected_items)}",
            "==========================================",
            "  Thank you for shopping with us!         ",
            "==========================================",
        ]

        summary_text = "\n".join(lines)

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(summary_text)
            messagebox.showinfo("Summary Saved", f"Saved to '{filename}'.\n\n{summary_text}")
        except OSError as e:
            messagebox.showerror("File Error", f"Could not save summary:\n{e}")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def clear_output(self):
        """Clear the output area and reset stored results."""
        self.output_text.delete("1.0", tk.END)
        self.last_detected_items = []


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SupermarketChatbotApp(root)
    root.mainloop()
