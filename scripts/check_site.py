#!/usr/bin/env python3
"""Validate the publishable static site using only the Python standard library."""

from __future__ import annotations

import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


SITE_URL = "https://starweave-labs.github.io/"
VOID_TAGS = frozenset("area base br col embed hr img input link meta param source track wbr".split())
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
errors: list[str] = []


def fail(location: str, message: str) -> None:
    errors.append(f"{location}: {message}")


class Document(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.path = path
        self.name = str(path.relative_to(ROOT))
        self.ids: set[str] = set()
        self.stack: list[tuple[str, int]] = []
        self.counts: Counter[str] = Counter()
        self.metadata: dict[str, str] = {}
        self.links: list[tuple[str, str, str]] = []
        self.idrefs: list[tuple[str, str]] = []
        self.images: list[tuple[dict[str, str | None], str]] = []
        self.title = ""
        self.doctype = False
        self.lang = ""
        self.json_ld = ""
        self.collect_json = False

    def location(self) -> str:
        return f"{self.name}:{self.getpos()[0]}"

    def handle_decl(self, decl: str) -> None:
        self.doctype |= decl.lower() == "doctype html"

    def start(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        attrs = dict(attributes)
        location = self.location()
        names = [name for name, _ in attributes]
        for name, count in Counter(names).items():
            if count > 1:
                fail(location, f"duplicate attribute {name!r}")
        self.counts[tag] += 1
        if tag == "html":
            self.lang = attrs.get("lang") or ""
        if "id" in attrs:
            identifier = attrs["id"] or ""
            if not identifier or identifier in self.ids:
                fail(location, f"empty or duplicate id {identifier!r}")
            self.ids.add(identifier)
        for attribute in ("aria-labelledby", "aria-describedby", "aria-controls", "for"):
            for identifier in (attrs.get(attribute) or "").split():
                self.idrefs.append((identifier, location))
        if tag == "meta":
            key = attrs.get("name") or attrs.get("property")
            if key:
                self.metadata[key] = attrs.get("content") or ""
            if attrs.get("charset"):
                self.metadata["charset"] = attrs["charset"] or ""
        if tag == "link" and "canonical" in (attrs.get("rel") or "").split():
            self.metadata["canonical"] = attrs.get("href") or ""
        for attribute in ("href", "src", "poster"):
            if attribute in attrs:
                self.links.append((attrs[attribute] or "", location, attribute))
        if "srcset" in attrs:
            for candidate in (attrs["srcset"] or "").split(","):
                if candidate.strip():
                    self.links.append((candidate.split()[0], location, "srcset"))
        if tag == "img":
            self.images.append((attrs, location))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.collect_json = True
            self.json_ld = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.start(tag, attrs)
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.start(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.collect_json:
            try:
                json.loads(self.json_ld)
            except json.JSONDecodeError as error:
                fail(self.location(), f"invalid JSON-LD: {error.msg}")
            self.collect_json = False
        if not self.stack or self.stack[-1][0] != tag:
            expected = self.stack[-1][0] if self.stack else "no open element"
            fail(self.location(), f"unexpected </{tag}>; expected closing {expected}")
            return
        self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self.stack and self.stack[-1][0] == "title":
            self.title += data
        if self.collect_json:
            self.json_ld += data


def local_target(url: str, source: Path) -> tuple[Path, str] | None:
    parsed = urlsplit(url)
    # ZUVI is a separate GitHub Pages deployment at this exact project root.
    # Its SPA fragments belong to that deployment; nested assets remain local checks.
    if (
        parsed.scheme == "https"
        and parsed.netloc == "starweave-labs.github.io"
        and parsed.path == "/zuvi/"
        and not parsed.query
    ):
        return None
    if parsed.scheme or parsed.netloc:
        if parsed.scheme not in ("http", "https") or parsed.netloc != urlsplit(SITE_URL).netloc:
            return None
    path = unquote(parsed.path)
    if not path:
        target = source
    elif path.startswith("/") or parsed.netloc:
        target = ROOT / path.lstrip("/")
    else:
        target = source.parent / path
    target = target.resolve()
    if target.is_dir():
        target /= "index.html"
    if not target.is_relative_to(ROOT):
        fail(str(source.relative_to(ROOT)), f"local URL escapes the site directory: {url}")
        return None
    return target, unquote(parsed.fragment)


def dimensions(path: Path) -> tuple[float, float] | None:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR" and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if path.suffix.lower() == ".svg":
        try:
            svg = ET.fromstring(data)
            viewbox = svg.get("viewBox", "").split()
            if len(viewbox) == 4:
                return float(viewbox[2]), float(viewbox[3])
            return float(svg.attrib["width"]), float(svg.attrib["height"])
        except (ET.ParseError, KeyError, ValueError):
            fail(str(path.relative_to(ROOT)), "SVG needs valid XML and dimensions or viewBox")
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP" and len(data) >= 30:
        if data[12:16] == b"VP8X":
            return int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1
        if data[12:16] == b"VP8L" and data[20] == 0x2F:
            bits = int.from_bytes(data[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if data[12:16] == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
            return int.from_bytes(data[26:28], "little") & 0x3FFF, int.from_bytes(data[28:30], "little") & 0x3FFF
    return None


documents: dict[Path, Document] = {}
for name in ("index.html", "404.html", "robots.txt", "sitemap.xml"):
    if not (ROOT / name).is_file():
        fail(name, "required publishable file is missing")

for path in sorted(ROOT.glob("*.html")):
    document = Document(path)
    document.feed(path.read_text(encoding="utf-8"))
    document.close()
    documents[path] = document
    if document.stack:
        fail(document.name, "unclosed elements: " + ", ".join(f"<{tag}> at {line}" for tag, line in document.stack))
    if not document.doctype or not document.lang:
        fail(document.name, "HTML doctype and document language are required")
    for element in ("html", "head", "body", "main", "h1"):
        if document.counts[element] != 1:
            fail(document.name, f"expected one <{element}>, found {document.counts[element]}")
    if not document.title.strip():
        fail(document.name, "a nonempty page title is required")
    for key in ("charset", "viewport", "description", "canonical"):
        if not document.metadata.get(key):
            fail(document.name, f"required metadata {key!r} is missing")
    expected_canonical = SITE_URL if path.name == "index.html" else SITE_URL + path.name
    if document.metadata.get("canonical") != expected_canonical:
        fail(document.name, f"canonical must be {expected_canonical}")
    for identifier, location in document.idrefs:
        if identifier not in document.ids:
            fail(location, f"accessible label/control references missing id {identifier!r}")

for path, document in documents.items():
    for url, location, attribute in document.links:
        if not url.strip():
            fail(location, f"empty {attribute}")
            continue
        target = local_target(url, path)
        if target is None:
            continue
        destination, fragment = target
        if not destination.is_file():
            fail(location, f"missing local target {url!r}")
        elif fragment and destination in documents and fragment not in documents[destination].ids:
            fail(location, f"missing fragment {url!r}")
    for attrs, location in document.images:
        if "alt" not in attrs:
            fail(location, "image needs an alt attribute (empty for decorative images)")
        try:
            width, height = float(attrs.get("width") or ""), float(attrs.get("height") or "")
            if width <= 0 or height <= 0:
                raise ValueError
        except ValueError:
            fail(location, "image needs positive width and height attributes to reserve layout space")
            continue
        target = local_target(attrs.get("src") or "", path)
        if target and target[0].is_file():
            size = dimensions(target[0])
            if size and (size[0] <= 0 or size[1] <= 0 or abs(width / height - size[0] / size[1]) > 0.01):
                fail(location, f"image width/height ratio does not match {attrs.get('src')}")

homepage = documents.get(ROOT / "index.html")
if homepage:
    for key in ("og:type", "og:title", "og:description", "og:url", "og:image", "og:image:alt", "twitter:card", "twitter:image", "twitter:image:alt"):
        if not homepage.metadata.get(key):
            fail("index.html", f"required sharing metadata {key!r} is missing")
    if homepage.metadata.get("og:url") != SITE_URL:
        fail("index.html", "og:url must match the canonical site URL")
    if homepage.metadata.get("twitter:image") != homepage.metadata.get("og:image"):
        fail("index.html", "Open Graph and Twitter image URLs must match")
    image = local_target(homepage.metadata.get("og:image", ""), ROOT / "index.html")
    if not image or not image[0].is_file() or image[0].suffix.lower() != ".png":
        fail("index.html", "sharing image must resolve to a local PNG")
    else:
        size = dimensions(image[0])
        if size != (1200, 630):
            fail("index.html", f"sharing image must be 1200 × 630; found {size}")
        if homepage.metadata.get("og:image:width") != "1200" or homepage.metadata.get("og:image:height") != "630":
            fail("index.html", "Open Graph image dimensions must match 1200 × 630")

error_page = documents.get(ROOT / "404.html")
if error_page and "noindex" not in error_page.metadata.get("robots", ""):
    fail("404.html", "error page must carry a noindex robots directive")

for css in sorted((ROOT / "assets").glob("*.css")):
    for url in re.findall(r"url\(\s*['\"]?([^)'\"\s]+)", css.read_text(encoding="utf-8")):
        if url.startswith("#"):
            continue
        target = local_target(url, css)
        if target and not target[0].is_file():
            fail(str(css.relative_to(ROOT)), f"missing local CSS asset {url!r}")

try:
    sitemap = ET.parse(ROOT / "sitemap.xml")
    locations = [node.text for node in sitemap.iter() if node.tag.endswith("}loc") or node.tag == "loc"]
    if SITE_URL not in locations:
        fail("sitemap.xml", "homepage canonical URL is missing")
except (OSError, ET.ParseError) as error:
    fail("sitemap.xml", str(error))

robots = ROOT / "robots.txt"
if robots.is_file() and f"Sitemap: {SITE_URL}sitemap.xml" not in robots.read_text(encoding="utf-8"):
    fail("robots.txt", "the canonical sitemap URL is missing")

if errors:
    print("Static site validation failed:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    sys.exit(1)
print(f"Static site validation passed: {len(documents)} HTML pages, local assets, fragments, accessibility references, metadata and sharing image.")
