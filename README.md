# BeautifulWiktionary

Provides an simplified approach to using BeautifulSoup to scrape Wiktionary for useful information. Currently it is restricted to the English and Russian versions of Wiktionary and to the Russian language within both. But that may be expanded over time.

## Installation

```bash
pip install -i https://test.pypi.org/simple/ BeautifulWiktionary==0.0.3
```

## Usage

To load a standard Wiktionary entry page:

```python
from BeautifulWiktionary.beautifulwiktionary import *

bw = BeautifulWiktionary('english', 'кот')
print(bw.soup())
```

### Headword

The headword of an entry is the main word for the page with syllabic stress marks applied.

```python
# headword with syllabic stress marks
b = BeautifulWiktionary('russian', 'выебать')
print(b.headword)
# prints вы́ебать
```

### Definitions

The `BeautifulWiktionary` class can return the definitions for the word. If the object is instantiated with `english` as the language, the returned definition will be in English. If is is instantiated with `russian` as the language, the definitions will be returned in Russian. All senses of the word are included.

```python
b = BeautifulWiktionary('russian', 'лампа')
print(b.definition)
# prints настольный осветительный прибор; то же, что электрическая лампа; разг. то же, что радиолампа

b = BeautifulWiktionary('english', 'лампа')
print(b.definition)
# prints lamp; torch; (electronics) vacuum tube (British: valve)
```

To load an index page:

```python
from BeautifulWiktionary.beautifulwiktionary import *

bi = BeautifulWiktionaryIndex('english', 'автобус')

# print the page's soup:
print(bi.soup)

# list of words from the index page
print(bi.words)

# list of words that are redirects (always None in English)
print(bi.redirect_words)

# info about the next index page
print(bi.next_word)
# {'word': 'адаптировать', 'url': '/w/index.php?title=Category:Russian_lemmas&pagefrom=%D0%90...}

# info about the previous index page
print(bi.prev_word)
# {'word': 'абрис', 'url': '/w/index.php...'}
```

