#!/usr/bin/env python3
"""Convert a dictionary in JSON to StarDict.

Usage: json-to-stardict.py SOURCE OUTPUT [--bookname NAME] [--description TEXT]

SOURCE is a JSON list of entries, each an object with the strings
"term", "definition" and "attribution" and an "aliases" list of
strings, as in dictionary-en.json; other fields are ignored.  OUTPUT
is the file name without extension of the StarDict dictionary to
write: OUTPUT.ifo, .idx, .dict and, when there are aliases, .syn.
Existing files are never overwritten, and the source is only read.

Each term gets one article: its definition, then its attribution in
italics.  Each alias goes to the .syn and leads to its term's article;
an alias that is also another term leads to both articles.

Before reporting success the script reads its output back and checks
that every term and every alias reaches its article.
"""

import argparse
import html
import json
import os
import struct
import sys

MAGIC = "StarDict's dict ifo file"
EXTENSIONS = (".ifo", ".idx", ".syn", ".dict")


def stardict_key(word):
    """Return the StarDict sort key of the UTF-8 bytes WORD.

    StarDict sorts by ASCII-case-insensitive bytes, then by bytes;
    bytes.lower() folds ASCII letters only, which is exactly that.
    """
    return (word.lower(), word)


def esc(text):
    return html.escape(text, quote=False)


def read_source(path):
    """Return (articles, links) for the JSON dictionary PATH; exit on bad input.

    ARTICLES maps each term to its article HTML; LINKS is the set of
    (alias, term) pairs for the .syn.
    """
    try:
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, ValueError) as err:
        sys.exit(f"{path}: not readable as JSON: {err}")
    if not isinstance(entries, list):
        sys.exit(f"{path}: the top level is not a list of entries")
    articles, links = {}, set()
    for number, entry in enumerate(entries, 1):
        where = f"{path}: entry {number}"
        if not isinstance(entry, dict):
            sys.exit(f"{where} is not an object")
        for field in ("term", "definition", "attribution"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                sys.exit(f"{where}: missing or empty {field!r}")
        term = entry["term"]
        aliases = entry.get("aliases", [])
        if not isinstance(aliases, list) or not all(isinstance(a, str) and a.strip()
                                                    for a in aliases):
            sys.exit(f"{where} ({term}): 'aliases' is not a list of non-empty strings")
        if term in articles:
            sys.exit(f"{where}: term {term!r} appears twice")
        articles[term] = f"{esc(entry['definition'])}<br><i>{esc(entry['attribution'])}</i>"
        links |= {(alias, term) for alias in aliases if alias != term}
    return articles, links


def build(articles, links):
    """Return (idx, syn, dict_bytes).

    IDX is a sorted list of (word, offset, size); SYN a sorted list of
    (alias, idx_position).
    """
    words = sorted((w.encode("utf-8") for w in articles), key=stardict_key)
    idx, position, parts, offset = [], {}, [], 0
    for word in words:
        body = articles[word.decode("utf-8")].encode("utf-8")
        position[word] = len(idx)
        idx.append((word, offset, len(body)))
        parts.append(body)
        offset += len(body)
    syn = sorted({(alias.encode("utf-8"), position[term.encode("utf-8")])
                  for alias, term in links},
                 key=lambda e: (stardict_key(e[0]), e[1]))
    return idx, syn, b"".join(parts)


def encode_idx(idx):
    return b"".join(w + b"\0" + struct.pack(">II", o, s) for w, o, s in idx)


def encode_syn(syn):
    return b"".join(w + b"\0" + struct.pack(">I", p) for w, p in syn)


def parse_records(data, tail):
    """Return [(word, tail_bytes)] for an index whose records end in TAIL bytes."""
    out, pos = [], 0
    while pos < len(data):
        nul = data.index(b"\0", pos)
        out.append((data[pos:nul], data[nul + 1:nul + 1 + tail]))
        pos = nul + 1 + tail
    return out


def verify(out, articles, links):
    """Read the written dictionary back; raise SystemExit on any mismatch.

    Return the number of terms and aliases checked.
    """
    def read(ext):
        with open(out + ext, "rb") as f:
            return f.read()
    dict_data = read(".dict")
    idx = [(w, *struct.unpack(">II", t)) for w, t in parse_records(read(".idx"), 8)]
    has_syn = os.path.exists(out + ".syn")
    syn = ([(w, struct.unpack(">I", t)[0]) for w, t in parse_records(read(".syn"), 4)]
           if has_syn else [])
    for name, keys in (("idx", [w for w, *_ in idx]), ("syn", [w for w, _ in syn])):
        if any(stardict_key(a) > stardict_key(b) for a, b in zip(keys, keys[1:])):
            raise SystemExit(f"verify: .{name} is not in StarDict order")
    ifo = dict(line.split("=", 1) for line in read(".ifo").decode("utf-8").splitlines()[1:])
    if int(ifo["wordcount"]) != len(idx) or int(ifo.get("synwordcount", 0)) != len(syn):
        raise SystemExit("verify: .ifo counts do not match the indexes")
    if has_syn != bool(links) or ("synwordcount" in ifo) != has_syn:
        raise SystemExit("verify: a .syn and its count must be there exactly when there are aliases")
    if int(ifo["idxfilesize"]) != os.path.getsize(out + ".idx"):
        raise SystemExit("verify: .ifo idxfilesize does not match the .idx")
    if any(pos >= len(idx) for _, pos in syn):
        raise SystemExit("verify: .syn points past the .idx")
    heads = [word for word, *_ in idx]
    if len(set(heads)) != len(heads) or set(heads) != {w.encode("utf-8") for w in articles}:
        raise SystemExit("verify: the .idx words are not the terms, once each")
    for word, offset, size in idx:
        if dict_data[offset:offset + size] != articles[word.decode("utf-8")].encode("utf-8"):
            raise SystemExit(f"verify: {word.decode('utf-8')!r} does not reach its article")
    reached = {(alias, heads[pos]) for alias, pos in syn}
    wanted = {(alias.encode("utf-8"), term.encode("utf-8")) for alias, term in links}
    if reached != wanted:
        raise SystemExit(f"verify: .syn adds {len(reached - wanted)} pairs "
                         f"and loses {len(wanted - reached)}")
    return len(heads) + len(wanted)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("source", help="JSON file: a list of entries")
    parser.add_argument("output", help="output file name without extension")
    parser.add_argument("--bookname", help="dictionary name shown by readers "
                        "(default: the output's base name)")
    parser.add_argument("--description", help="text that opens the .ifo description, "
                        "such as the licence and the home page")
    args = parser.parse_args()
    if not os.path.isfile(args.source):
        sys.exit(f"missing source file: {args.source}")
    existing = [args.output + ext for ext in EXTENSIONS if os.path.exists(args.output + ext)]
    if existing:
        sys.exit("refusing to overwrite: " + ", ".join(existing))

    articles, links = read_source(args.source)
    idx, syn, dict_data = build(articles, links)
    idx_data = encode_idx(idx)
    bookname = args.bookname or os.path.basename(args.output)
    description = "; ".join(filter(None, [
        args.description,
        f"converted from {os.path.basename(args.source)} by json-to-stardict.py"]))
    ifo = "\n".join([MAGIC, "version=3.0.0", f"bookname={bookname}",
                     f"wordcount={len(idx)}"]
                    + ([f"synwordcount={len(syn)}"] if syn else [])
                    + [f"idxfilesize={len(idx_data)}", "sametypesequence=h",
                       "description=" + " ".join(description.split()), ""])
    files = [(".dict", dict_data), (".idx", idx_data)]
    if syn:
        files.append((".syn", encode_syn(syn)))
    files.append((".ifo", ifo.encode("utf-8")))
    written = []
    try:
        for ext, data in files:
            with open(args.output + ext, "xb") as f:
                written.append(args.output + ext)
                f.write(data)
        checked = verify(args.output, articles, links)
    except BaseException:
        for path in written:
            os.remove(path)
        raise

    also_terms = sorted({alias for alias, _ in links if alias in articles})
    print(f"terms: {len(idx)}  aliases: {len(syn)}")
    print(f"aliases that are also terms: {len(also_terms)}"
          + (f" ({', '.join(also_terms)})" if also_terms else ""))
    print(f"terms and aliases checked through the output: {checked}")


if __name__ == "__main__":
    main()
