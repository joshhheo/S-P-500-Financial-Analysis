"""Calculation XML supplement: Edgar loses prohibition/priority and locator identity."""
from collections import defaultdict
from decimal import Decimal
from urllib.parse import urlparse

from lxml import etree

X = '{http://www.w3.org/1999/xlink}'
L = '{http://www.xbrl.org/2003/linkbase}'


def read_calculations(contents, source):
    """Resolve duplicate/prohibited arcs across supplied calculation documents.

    Source locators must name the official schema for this filing's version.
    A custom locator remains custom even if its fragment imitates a standard ID.
    """
    grouped = defaultdict(list)
    expected_path = urlparse(source.schema).path
    supplied = {urlparse(doc.get('url', '')).path.rsplit('/', 1)[-1]
                for doc in source.documents}
    for content in contents:
        raw = content.encode() if isinstance(content, str) else content
        root = etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True))
        # Do not derive from a supplied fragment of a referenced calculation file.
        if source.documents:
            for reference in root.iter(L+'linkbaseRef'):
                if reference.get(X+'role') == 'http://www.xbrl.org/2003/role/calculationLinkbaseRef':
                    filename = urlparse(reference.get(X+'href', '')).path.rsplit('/', 1)[-1]
                    if filename not in supplied:
                        source.calculation_issue = 'Referenced calculation document was not supplied'
        for link in root.iter(L+'calculationLink'):
            role = link.get(X+'role')
            locators = defaultdict(list)
            for loc in link.findall(L+'loc'):
                href = loc.get(X+'href', '')
                parsed = urlparse(href)
                name = href
                if (parsed.hostname in ('xbrl.fasb.org', 'fasb.org', 'www.fasb.org')
                        and parsed.path == expected_path and parsed.fragment.startswith('us-gaap_')):
                    name = 'us-gaap:' + parsed.fragment[len('us-gaap_'):]
                locators[loc.get(X+'label')].append(name)
            for arc in link.findall(L+'calculationArc'):
                arcrole = arc.get(X+'arcrole')
                if arcrole not in ('http://www.xbrl.org/2003/arcrole/summation-item',
                                   'https://xbrl.org/2023/arcrole/summation-item'):
                    source.calculation_issue = 'Unsupported calculation arcrole'
                    continue
                weight = Decimal(arc.get('weight'))
                if weight not in (Decimal(1), Decimal(-1)):
                    source.calculation_issue = 'Unsupported calculation weight'
                    continue
                for parent in locators[arc.get(X+'from')]:
                    for child in locators[arc.get(X+'to')]:
                        grouped[(role, arcrole, parent, child, int(weight))].append(
                            (int(arc.get('priority', '0')), arc.get('use') == 'prohibited'))
    equations = defaultdict(list)
    for (role, arcrole, parent, child, weight), arcs in grouped.items():
        priority = max(p for p, _ in arcs)
        if any(prohibited for p, prohibited in arcs if p == priority):
            continue
        network = role
        if not arcrole.endswith('2003/arcrole/summation-item'):
            network = role + ' [Calculations 1.1]'
        equations[(network, parent)].append((child, weight))
    return dict(equations)
