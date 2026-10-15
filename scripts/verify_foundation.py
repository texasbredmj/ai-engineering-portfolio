"""Check evidence provenance and all packaged HTML links without network access."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.steps = 0
        self.alts = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        for attr in ('href', 'src'):
            if attr in a:
                self.links.append(a[attr])
        if tag == 'img':
            self.alts.append(a.get('alt', ''))
        if 'data-step' in a:
            self.steps += 1


def main():
    projects = json.loads((ROOT / 'showcase/projects.json').read_text(encoding='utf-8'))['projects']
    assert len(projects) == 8 and len({p['name'] for p in projects}) == 8
    for p in projects:
        evidence = json.loads((ROOT / p['evidence']).read_text(encoding='utf-8'))
        if p['record_index'] is not None:
            evidence = evidence['projects'][p['record_index']]
        assert p['name'] == evidence['name']
        assert p['commit'] == evidence['published_sha'] == evidence['remote_ci']['head_sha']
        assert re.fullmatch('[0-9a-f]{40}', p['commit'])
        assert p['ci'] == evidence['remote_ci']['url']
        assert p['source'] == evidence['repository_url']
        assert p['private'] == evidence['private']
        assert evidence['remote_ci']['conclusion'] == 'success'
        assert p['gaps'] and p['limitation']
    html = (ROOT / 'site/index.html').read_text(encoding='utf-8')
    page = Page()
    page.feed(html)
    assert len(page.ids) == len(set(page.ids)), 'Duplicate page IDs'
    assert page.steps == 5 and all(page.alts)
    assert len([i for i in page.ids if i.startswith('project-')]) == 8
    checked = 0
    for link in page.links:
        u = urlsplit(link)
        if u.scheme or u.netloc:
            continue
        path = (ROOT / 'site' / unquote(u.path)).resolve() if u.path else ROOT / 'site/index.html'
        assert path.is_relative_to((ROOT / 'site').resolve()), f'Link escapes site: {link}'
        assert path.exists(), f'Missing local link: {link}'
        if u.fragment and path.suffix == '.html':
            target = page
            if path != ROOT / 'site/index.html':
                target = Page()
                target.feed(path.read_text(encoding='utf-8'))
            assert u.fragment in target.ids, f'Missing anchor: {link}'
        checked += 1
    for folder in ('docs', 'evidence', 'resume'):
        for source in (ROOT / folder).rglob('*'):
            if source.is_file():
                packaged = ROOT / 'site' / source.relative_to(ROOT)
                assert packaged.read_bytes() == source.read_bytes(), f'Stale package: {source}'
    print(json.dumps({'inventory_projects': 8, 'evidence_commit_and_ci_matches': 8,
                      'guided_steps': 5, 'local_links_checked': checked,
                      'packaged_evidence_matches': True, 'external_links_rechecked': False}))


if __name__ == '__main__':
    main()
