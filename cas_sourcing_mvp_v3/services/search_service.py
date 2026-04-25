from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlencode
import requests


DEFAULT_SUPPLIER_DOMAINS = [
    "sigmaaldrich.com",
    "fishersci.com",
    "thermofisher.com",
    "tcichemicals.com",
    "combi-blocks.com",
    "oakwoodchemical.com",
    "chemimpex.com",
    "vwr.com",
    "ambeed.com",
    "emolecules.com",
    "molport.com",
    "chemblink.com",
    "lookchem.com",
]


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str


def build_cas_supplier_queries(cas_number: str, chemical_name: str | None = None) -> list[str]:
    cas = cas_number.strip()
    chem = (chemical_name or "").strip()
    base_terms = [
        f'"{cas}" supplier price',
        f'"{cas}" chemical supplier',
        f'"{cas}" buy',
        f'"{cas}" quote',
    ]
    if chem:
        base_terms.extend([
            f'"{cas}" "{chem}" supplier',
            f'"{chem}" "{cas}" price',
        ])
    return base_terms


def direct_supplier_search_urls(cas_number: str) -> list[SearchResult]:
    cas = cas_number.strip()
    templates = [
        ("Sigma-Aldrich", "https://www.sigmaaldrich.com/US/en/search/{cas}"),
        ("Fisher Scientific", "https://www.fishersci.com/us/en/catalog/search/products?keyword={cas}"),
        ("Thermo Fisher", "https://www.thermofisher.com/search/results?keyword={cas}"),
        ("TCI Chemicals", "https://www.tcichemicals.com/US/en/search?text={cas}"),
        ("Combi-Blocks", "https://www.combi-blocks.com/cgi-bin/find.cgi?search={cas}"),
        ("VWR / Avantor", "https://us.vwr.com/store/search?keyword={cas}"),
        ("Oakwood Chemical", "https://oakwoodchemical.com/Search?term={cas}"),
        ("Chem-Impex", "https://www.chemimpex.com/search?search={cas}"),
        ("MolPort", "https://www.molport.com/shop/find-chemicals-by-cas-number/{cas}"),
        ("eMolecules", "https://search.emolecules.com/search/#?query={cas}"),
        ("Ambeed", "https://www.ambeed.com/search.html?search={cas}"),
        ("ChemBlink", "https://www.chemblink.com/search.aspx?search={cas}"),
    ]
    return [
        SearchResult(
            title=f"{name} CAS search",
            url=template.format(cas=cas),
            snippet="Direct supplier/search page for this CAS. Extraction depends on page accessibility.",
            source="direct_supplier_link",
        )
        for name, template in templates
    ]


def serpapi_search(
    queries: Iterable[str],
    api_key: str,
    max_results_per_query: int = 5,
    timeout: int = 20,
) -> list[SearchResult]:
    """Run CAS supplier discovery through SerpAPI if a key is supplied.

    SerpAPI is used as a discovery layer. We still extract and display source URLs so
    the user can audit every result.
    """
    if not api_key:
        return []

    results: list[SearchResult] = []
    seen_urls: set[str] = set()
    endpoint = "https://serpapi.com/search.json"

    for query in queries:
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "num": max_results_per_query,
        }
        try:
            response = requests.get(endpoint, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            continue

        for item in payload.get("organic_results", [])[:max_results_per_query]:
            url = item.get("link") or ""
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            results.append(
                SearchResult(
                    title=item.get("title") or "Untitled search result",
                    url=url,
                    snippet=item.get("snippet") or "",
                    source="serpapi",
                )
            )
    return results


def filter_likely_supplier_results(results: list[SearchResult]) -> list[SearchResult]:
    filtered: list[SearchResult] = []
    for result in results:
        haystack = f"{result.title} {result.url} {result.snippet}".lower()
        if any(domain in haystack for domain in DEFAULT_SUPPLIER_DOMAINS):
            filtered.append(result)
            continue
        if any(term in haystack for term in ["supplier", "price", "quote", "buy", "catalog", "chemical"]):
            filtered.append(result)
    return filtered
