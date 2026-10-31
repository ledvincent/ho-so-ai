"""Deterministic adapter for saved national portal by-code HTML. No model calls."""
import hashlib
import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

VERSION = "vpcp-by-code-3"


class ParseError(ValueError):
    pass


def text(node):
    # Decode entities and normalize layout whitespace only; preserve wording.
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def parse(raw: bytes, code: str, source_url: str, fetched_at: str, expected_name: str):
    soup = BeautifulSoup(raw.decode("utf-8"), "html.parser")
    identity = re.findall(r"obj\.procedure_code\s*=\s*'([^']+)'", str(soup))
    if identity != [code]:
        raise ParseError(f"Missing or mismatched procedure identity: {identity!r}")
    names = [text(h) for h in soup.select("h1.main-title") if text(h)]
    if len(names) != 1 or not names[0].casefold().startswith(expected_name.casefold()):
        raise ParseError(f"Unexpected procedure name: {names!r}")
    sections = {}
    for h in soup.select("h2.main-title-sub"):
        nodes = []
        for sibling in h.next_siblings:
            if getattr(sibling, "name", None) == "h2":
                break
            if getattr(sibling, "name", None):
                nodes.append(str(sibling))
        sections[text(h)] = BeautifulSoup("".join(nodes), "html.parser")
    required = ["Trình tự thực hiện", "Cách thức thực hiện", "Thành phần hồ sơ", "Cơ quan thực hiện", "Yêu cầu, điều kiện thực hiện"]
    if any(s not in sections for s in required):
        raise ParseError("Missing required section")
    document_sections = []
    for heading, node in sections.items():
        visible = BeautifulSoup(str(node), 'html.parser')
        for control in visible.select('script,style'):
            control.decompose()
        for control in visible.select('a[onclick]'):
            if re.fullmatch(r'\s*showMoreDes\(\d+\)\s*', control['onclick']):
                control.decompose()
        document_sections.append(dict(heading=heading,text_verbatim=visible.get_text('\n',strip=True)))
    # The portal's service-selection panel contains additional official audience,
    # authority and level information outside the main h2 sections. Preserve it
    # as evidence too; buttons/fee controls add no factual content.
    service=soup.select_one('#listDVC')
    if service:
        visible=BeautifulSoup(str(service),'html.parser')
        for control in visible.select('script,style,button,a'):
            control.decompose()
        document_sections.append(dict(heading='Thông tin dịch vụ và đối tượng thực hiện',text_verbatim=visible.get_text('\n',strip=True)))
    result = dict(code=code, name=names[0], source_url=source_url, fetched_at=fetched_at,
                  sha256=hashlib.sha256(raw).hexdigest(), parser_version=VERSION,
                  facts=[], requirements=[], methods=[], fees=[], forms=[], issues=[],
                  document=dict(name=names[0],sections=document_sections))
    for kind, heading in [("steps", required[0]), ("agency", required[3]), ("conditions", required[4])]:
        content = sections[heading].select(".content" if kind == "steps" else ".article")
        if not content:
            raise ParseError(f"Missing content for {heading}")
        for position, node in enumerate(content):
            value = text(node)
            if value:
                result["facts"].append(dict(kind=kind, position=position, text_verbatim=value))
    for row in sections[required[2]].select("tbody tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) != 3 or not text(cells[0]):
            raise ParseError("Unrecognized requirement row")
        counts = re.fullmatch(r"Bản chính:\s*(\d+)\s*-\s*Bản sao:\s*(\d+)", text(cells[2]))
        if not counts:
            raise ParseError("Unrecognized document quantities")
        group = row.find_parent(class_="item")
        links = []
        for a in cells[1].select("a[href]"):
            url = urljoin(source_url, a["href"])
            if parse_qs(urlparse(url).query).get("ma"):
                links.append(url)
                result["forms"].append(dict(url=url, label=text(a)))
        result["requirements"].append(dict(position=len(result["requirements"]),
            group_heading=text(group.select_one(".title")) if group else "",
            text_verbatim=text(cells[0]), originals=int(counts[1]), copies=int(counts[2]), form_urls=links))
    for row in sections[required[1]].select("tbody tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) != 4:
            raise ParseError("Unrecognized submission method row")
        method = text(cells[0])
        result["methods"].append(dict(position=len(result["methods"]), method=method,
            processing_time_verbatim=text(cells[1]), description_verbatim=text(cells[3])))
        for fee in cells[2].select("li") or [cells[2]]:
            details = fee.select("a[onclick]")
            detail_refs = [a["onclick"] for a in details]
            for a in details:
                a.decompose()
            value = text(fee)
            if not value:
                result["issues"].append("Empty fee cell for " + method)
            amount, currency = None, None
            m = re.fullmatch(r"(?:Phí|Lệ phí):\s*([\d.]+)\s*(Đồng|USD)", value)
            if m:
                amount = int(m[1].replace(".", ""))
                currency = "VND" if m[2] == "Đồng" else "USD"
            elif value in ("Phí: Miễn phí Đồng", "Lệ phí: Miễn phí Đồng"):
                amount, currency = 0, "VND"
            result["fees"].append(dict(method=method, text_verbatim=value,
                amount=amount, currency=currency, condition_verbatim=None,
                detail_refs=detail_refs, condition_status="not_separately_stated"))
    if not result["requirements"] or not result["methods"] or not any(f["kind"] == "steps" for f in result["facts"]):
        raise ParseError("Empty procedure")
    result["forms"] = list({f["url"]: f for f in result["forms"]}.values())
    result["status"] = "needs_source_details" if result["issues"] else "parsed"
    return result
