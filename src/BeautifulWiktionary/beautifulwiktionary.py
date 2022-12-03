#!/usr/bin/env python3

from urllib.request import urlopen, Request
import urllib.parse
from http.client import HTTPResponse
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem, HardwareType
import copy
import re
import sys
from typing import Optional
from bs4 import BeautifulSoup, element

def lazy_property(fn):
    '''Decorator that makes a property lazy-evaluated.
    '''
    attr_name = '_lazy_' + fn.__name__
    
    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)
    return _lazy_property

class BeautifulObject(object):
    def __init__(self):
        pass
        
    def _headers(self) -> dict:
        hn = [HardwareType.COMPUTER.value]
        user_agent_rotator = UserAgent(hardware_types=hn,limit=20)
        user_agent = user_agent_rotator.get_random_user_agent()
        
        headers = {'user-agent': user_agent}
        return headers
    
    def remove_html_comments(self, html: str) -> str:
        """
            Strips HTML comments. See https://stackoverflow.com/a/57996414
            :param html: html string to process
            :return: html string with comments stripped
            """
        result = re.sub(
            r'(<!--.*?-->)|(<!--[\S\s]+?-->)|(<!--[\S\s]*?$)', "", html)
        return result

class BeautifulWiktionary(BeautifulObject):
    def __init__(self, language: str, word: str):
        self.language = language.lower()
        self.word = word
        
    def check_excluded_ids(self, span_id: str) -> bool:
        excluded = ['Pronunciation', 'Alternative_forms', 'Etymology']
        for ex in excluded:
            if re.search(ex, span_id, re.IGNORECASE):
                return True
        return False
    
    def remove_dl_ul(self, li: element.Tag) -> element.Tag:
        try:
            dl_extract = li.dl.extract()
        except AttributeError:
            pass
            # sometimes citations are presented in <ul> so remove
        try:
            ul_extract = li.ul.extract()
        except AttributeError:
            pass
        return li
        
    def url(self) -> str:
        raw_word = self.word.replace(" ", "_")
        word = urllib.parse.quote(raw_word)
        if self.language == 'russian':
            url =  f'https://ru.wiktionary.org/wiki/{word}'
        elif self.language == 'english':
            url = f'https://en.wiktionary.org/wiki/{word}'
        return url
    
    
    def _extract_russian_soup(self, response: HTTPResponse) -> BeautifulSoup:
        new_soup = BeautifulSoup('', 'html.parser')
        # remove HTML comments before processing
        html_str = response.read().decode('UTF-8')
        cleaner_html = self.remove_html_comments(html_str)
        soup = BeautifulSoup(cleaner_html, 'html.parser')
        # get rid of certain tags to make it lighter
        # to work with
        [s.extract() for s in soup(['head', 'script', 'footer'])]
        for h2 in soup.find_all('h2'):
            for span in h2.children:
                try:
                    if 'Russian' in span['id']:
                        new_soup.append(copy.copy(h2))
                        # capture everything in the Russian section
                        for curr_sibling in h2.next_siblings:
                            if curr_sibling.name == "h2":
                                break
                            else:
                                new_soup.append(copy.copy(curr_sibling))
                        break
                except:
                    pass
        return new_soup
    
    @lazy_property
    def soup(self) -> Optional[BeautifulSoup]:
        try:
            response = urlopen(Request(self.url(), headers=self._headers()))
        except BaseException:
            print('error')
            return None
        if self.language == 'russian':
            new_soup = BeautifulSoup('', 'html.parser')
            # remove HTML comments before processing
            html_str = response.read().decode('UTF-8')
            cleaner_html = self.remove_html_comments(html_str)
            soup = BeautifulSoup(cleaner_html, 'html.parser')
            
            # get rid of script tags to make it lighter
            # to work with
            [s.extract() for s in soup(['head', 'script', 'footer'])]
            for h1 in soup.find_all('h1'):
                for span in h1.children:
                    try:
                        if 'Русский' in span['id']:
                            new_soup.append(copy.copy(h1))
                            # capture everything in the Russian section
                            for curr_sibling in h1.next_siblings:
                                if curr_sibling.name == "h1":
                                    break
                                else:
                                    new_soup.append(copy.copy(curr_sibling))
                            break
                    except BaseException:
                        pass
            return new_soup
        elif self.language == 'english':
            new_soup = self._extract_russian_soup(response)
            return new_soup
        else:
            return None
        
    def _en_wiki_ru_headword(self) -> Optional[str]:
        headword_regex = re.compile('.*headword.*')
        headword_elements = self.soup.find_all(
            "strong", {"lang": "ru", "class": headword_regex})
        return headword_elements[0].text
    
    def _ru_wiki_ru_headword(self) -> Optional[str]:
        morphology_h3 = self.soup.select('#Морфологические_и_синтаксические_свойства')[0].parent
        p = morphology_h3.find_next_sibling('p');
        raw_word = p.text
        # some words like выебать have an extra <p></p>
        # block so our target is at index 1 not 0
        if len(raw_word) == 1:
            p = inner_div.findChildren('p')[1]
            raw_word = p.text
        word = re.sub(r'[-·]', "", raw_word)
        # some words like кот have other info in parens after the correct
        # form. The following regex will remove   
        m = re.sub(r'\(.*\)', "", word)
        return m.strip()
    
    @lazy_property
    def headword(self) -> Optional[str]:
        if self.language == 'english':
            return self._en_wiki_ru_headword()
        elif self.language == 'russian':
            return self._ru_wiki_ru_headword()
        else:
            return None
        
    @lazy_property
    def definition(self) -> Optional[str]:
        if self.language == 'russian':
            found = False
            definitions = ""
            for h4 in self.soup.find_all('h4'):
                for span in h4.children:
                    try:
                        if 'Значение' in span['id']:
                            # this h4's next sibling is a an <ol> block that we need
                            for h4_sib in h4.next_siblings:
                                if h4_sib.name == "ol":
                                    contents = "".join(h4_sib.strings)
                                    if contents[-1] != '\n':
                                        contents += '\n'
                                    # some definitions include this reference which
                                    # should be eliminated
                                    contents = contents.replace('[Даль]', '')
                                    definitions += contents
                                    break;
                    except:
                        pass
                found = False
            formatted_definitions = ""
            for line in definitions.split('\n'):
                # remove any stress diacritical marks
                # e.g. in def of продолговатый
                line = re.sub(r'\u0301', "", line)
                m = re.search(r'[\w\d\s\.,-\\(\\)—]+', line, re.M)
                try:
                    formatted_definitions += f'; {m[0]}'.strip()
                except:
                    pass
            result = re.sub(r"^;\s(.*)$", r"\1", formatted_definitions)
            return result
        elif self.language == 'english':
            definitions = []
            
            # there are cases (as with the word 'бухта' where there are
            # multiple etymologies. In these cases, the page structure is
            # different. We will try both structures.
            
            for tag in ['h3', 'h4']:
                for h3_or_h4 in self.soup.find_all(tag):
                    found = False
                    for h3_or_h4_child in h3_or_h4.children:
                        if h3_or_h4_child.name == 'span':
                            if h3_or_h4_child.get('class'):
                                span_classes = h3_or_h4_child.get('class')
                                if 'mw-headline' in span_classes:
                                    span_id = h3_or_h4_child.get('id')
                                    # exclude any h3 whose span is not a part of speech
                                    if not self.check_excluded_ids(span_id):
                                        found = True
                                    break
                    if found:
                        ol = h3_or_h4.find_next_sibling('ol')
                        if ol is None:
                            continue
                        lis = ol.children
                        for li in lis:
                            # skip '\n' children
                            if li.name != 'li':
                                continue
                            # remove any extraneous detail tags + children, etc.
                            li = self.remove_dl_ul(li)
                            li_def = li.text.strip()
                            definitions.append(li_def)
            definition_list = '; '.join(definitions)
            # if a definition has a single line, remove the ;\s
            definition_list = re.sub(r'^(?:;\s)+(.*)$', '\\1', definition_list)
            # remove "see also" links
            definition_list = re.sub(r'\(see also[^\)]*\)+', "", definition_list)
            return definition_list
        else:
            return None
        
class BeautifulWiktionaryIndex(BeautifulObject):
    def __init__(self, language: str, startswith: str):
        self.language = language
        self.startswith = startswith
        
    def url(self) -> str:
        raw_word = self.startswith.replace(" ", "_")
        word = urllib.parse.quote(raw_word)
        if self.language == 'russian':
            url =  f'https://ru.wiktionary.org/wiki/%D0%A1%D0%BB%D1%83%D0%B6%D0%B5%D0%B1%D0%BD%D0%B0%D1%8F:%D0%92%D1%81%D0%B5_%D1%81%D1%82%D1%80%D0%B0%D0%BD%D0%B8%D1%86%D1%8B?from={word}&to=&namespace=0'
        elif self.language == 'english':
            url = f'https://en.wiktionary.org/w/index.php?title=Category:Russian_lemmas&pagefrom={word}#mw-pages'
        return url
    
    @lazy_property
    def soup(self) -> Optional[BeautifulSoup]:
        try:
            response = urlopen(Request(self.url(), headers=self._headers()))
        except BaseException:
            print('error')
            return None
        if self.language == 'russian':
            new_soup = BeautifulSoup('', 'html.parser')
            # remove HTML comments before processing
            html_str = response.read().decode('UTF-8')
            cleaner_html = self.remove_html_comments(html_str)
            soup = BeautifulSoup(cleaner_html, 'html.parser')
            
            # get rid of script tags to make it lighter
            # to work with
            [s.extract() for s in soup(['head', 'script', 'footer'])]
            new_soup = BeautifulSoup('', 'html.parser')
            first_index_nav = soup.select_one('#mw-content-text > div:nth-child(2)')
            new_soup.append(copy.copy(first_index_nav))
            # capture everything in the Russian section
            for curr_sibling in first_index_nav.next_siblings:
                if curr_sibling.name == "noscript":
                    break
                else:
                    new_soup.append(copy.copy(curr_sibling))
            return new_soup
        elif self.language == 'english':
            html_str = response.read().decode('UTF-8')
            cleaner_html = self.remove_html_comments(html_str)
            soup = BeautifulSoup(cleaner_html, 'html.parser')
            return soup.select_one('#mw-pages')
        else:
            return None
        
    @lazy_property
    def words(self) -> Optional[list]:
        w = []
        for li in self.soup.find_all('li'):
            if self.language == 'russian':
                if 'allpagesredirect' in li.get_attribute_list('class'):
                    continue
            w.append(li.text)
        return w
    
    @lazy_property
    def redirect_words(self) -> Optional[list]:
        if self.language == 'english':
            return self.words
        w = []
        for li in self.soup.find_all('li'):
            if 'allpagesredirect' not in li.get_attribute_list('class'):
                continue
            w.append(li.text)
        return w
    
    def _nav_word(self, direction: str) -> Optional[dict]:
        idx = (lambda : 1, lambda: 0)[direction == 'prev']()
        if self.language == 'russian':
            
            
            bottom_nav = self.soup.select('.mw-allpages-nav')[1]
            next_link = bottom_nav.select('a')[idx]
            
            m = re.search(r'\((.+)\)', next_link.text, re.M)
            word = m[1]
            
            url = next_link['href']
        else:
            word_list_div = self.soup.select_one('#mw-pages > div')
            nav_links = word_list_div.find_next_siblings('a')
            
            # the next word is easier to obtain
            if idx == 1:
                next_link = nav_links[idx]
                next_url = next_link['href']
                m = re.search(r'pagefrom=.+%0A(.+)#', next_url, re.M)
                word = urllib.parse.unquote(m[1])
                url = next_url
            else:
                # the prev link works backwards to the next
                prev_link = nav_links[idx]
                prev_url = prev_link['href']
                # we have to actually load the page!
                prev_url = f'https://en.wiktionary.org/{prev_url}'
                try:
                    response = urlopen(Request(prev_url, headers=self._headers()))
                except BaseException:
                    return None
                html_str = response.read().decode('UTF-8')
                cleaner_html = self.remove_html_comments(html_str)
                soup = BeautifulSoup(cleaner_html, 'html.parser')
                # find the first entry on the previous page's list
                list_div = soup.select_one('#mw-pages')
                first_item = list_div.find('li')
                
                word = first_item.text
                url = first_item['href']
                
                return None
            
        return {'word': word, 'url': url}
    
    @lazy_property
    def next_word(self) -> Optional[dict]:
        return self._nav_word('next')
    
    @lazy_property
    def prev_word(self) -> Optional[dict]:
        return self._nav_word('prev')
    
b = BeautifulWiktionary('russian', 'лампа')
print(b.definition)
# prints настольный осветительный прибор; то же, что электрическая лампа; разг. то же, что радиолампа

b = BeautifulWiktionary('english', 'лампа')
print(b.definition)
# prints lamp; torch; (electronics) vacuum tube (British: valve)
    
#bi = BeautifulWiktionaryIndex('english', 'автобус')
#print(bi.next_word)
#
#
## https://en.wiktionary.org/w/index.php?title=Category:Russian_lemmas&pagefrom=АДАПТИРОВАТЬ%0Aадаптировать#mw-pages
