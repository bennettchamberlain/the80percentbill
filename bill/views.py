from django.shortcuts import render

from .articles import ARTICLES

def int_to_roman(num):
    """Convert an integer to a Roman numeral (1-30)."""
    roman_numerals = {
        1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
        6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X",
        11: "XI", 12: "XII", 13: "XIII", 14: "XIV", 15: "XV",
        16: "XVI", 17: "XVII", 18: "XVIII", 19: "XIX", 20: "XX",
        21: "XXI", 22: "XXII", 23: "XXIII", 24: "XXIV", 25: "XXV",
        26: "XXVI", 27: "XXVII", 28: "XXVIII", 29: "XXIX", 30: "XXX"
    }
    return roman_numerals.get(num, str(num))


def index(request):
    """Display all 20 bill articles."""
    # Add Roman numerals to articles unless they have skip_numbering=True
    numbered_articles = []
    counter = 1
    
    for article in ARTICLES:
        title, desc, link, note, skip_numbering = article if len(article) == 5 else article + (False,)
        
        if skip_numbering:
            numbered_articles.append((title, desc, link, note))
        else:
            numbered_title = f"{int_to_roman(counter)}. {title}"
            numbered_articles.append((numbered_title, desc, link, note))
            counter += 1
    
    return render(request, "bill/index.html", {"articles": numbered_articles})

