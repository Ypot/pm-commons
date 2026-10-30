# Copyright (C) 2026 Ypot <ypot@publik.slmail.me>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for json-to-stardict.py, run through its command line.

Run: python -m unittest test_json_to_stardict
"""

import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json-to-stardict.py")

ENTRIES = [
    {"term": "work package", "aliases": [], "definition": "The lowest level of the WBS.",
     "attribution": "Original definition, CC BY-SA 4.0"},
    {"term": "Agile", "aliases": [], "definition": "A mindset & its <practices>.",
     "attribution": "Source: Example guide, adapted"},
    {"term": "earned value", "aliases": ["EV"], "definition": "The value of the work done.",
     "attribution": "Original definition, CC BY-SA 4.0"},
    {"term": "RACI matrix", "aliases": ["RACI", "work package"],
     "definition": "A matrix of roles.", "attribution": "Original definition, CC BY-SA 4.0"},
]


def records(data, tail):
    out, pos = [], 0
    while pos < len(data):
        nul = data.index(b"\0", pos)
        out.append((data[pos:nul].decode("utf-8"), data[nul + 1:nul + 1 + tail]))
        pos = nul + 1 + tail
    return out


class JsonToStardict(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.out = os.path.join(self.dir, "Out")

    def tearDown(self):
        self.tmp.cleanup()

    def source(self, entries, raw=None):
        path = os.path.join(self.dir, "dictionary.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(raw if raw is not None else json.dumps(entries))
        return path

    def run_script(self, *args):
        return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True,
                              text=True, encoding="utf-8")

    def read(self, ext):
        with open(self.out + ext, "rb") as f:
            return f.read()

    def outputs(self):
        return sorted(f for f in os.listdir(self.dir) if f.startswith("Out"))

    def lookup(self, word):
        """Return the articles WORD reaches by the .idx and the .syn."""
        idx = [(w, *struct.unpack(">II", t)) for w, t in records(self.read(".idx"), 8)]
        dict_data = self.read(".dict")
        hits = [i for i, (w, *_) in enumerate(idx) if w == word]
        if os.path.exists(self.out + ".syn"):
            hits += [struct.unpack(">I", t)[0] for w, t in records(self.read(".syn"), 4)
                     if w == word]
        return [(idx[i][0], dict_data[idx[i][1]:idx[i][1] + idx[i][2]].decode("utf-8"))
                for i in sorted(set(hits))]

    def test_writes_articles_aliases_and_header(self):
        result = self.run_script(self.source(ENTRIES), self.out, "--bookname", "PM Book",
                                 "--description", "CC BY-SA 4.0, https://example.org")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout,
                         "terms: 4  aliases: 3\n"
                         "aliases that are also terms: 1 (work package)\n"
                         "terms and aliases checked through the output: 7\n")
        self.assertEqual(self.outputs(), ["Out.dict", "Out.idx", "Out.ifo", "Out.syn"])
        ifo = self.read(".ifo").decode("utf-8").splitlines()
        self.assertEqual(ifo[0], "StarDict's dict ifo file")
        fields = dict(line.split("=", 1) for line in ifo[1:])
        self.assertEqual(fields["bookname"], "PM Book")
        self.assertEqual(fields["wordcount"], "4")
        self.assertEqual(fields["synwordcount"], "3")
        self.assertEqual(fields["sametypesequence"], "h")
        self.assertEqual(fields["idxfilesize"], str(len(self.read(".idx"))))
        self.assertEqual(fields["description"], "CC BY-SA 4.0, https://example.org; "
                         "converted from dictionary.json by json-to-stardict.py")
        # StarDict order: ASCII case folded first, then bytes.
        self.assertEqual([w for w, _ in records(self.read(".idx"), 8)],
                         ["Agile", "earned value", "RACI matrix", "work package"])
        # The article is the definition alone, escaped for HTML: no attribution.
        self.assertEqual(self.lookup("Agile"), [("Agile", "A mindset &amp; its &lt;practices&gt;.")])
        self.assertNotIn(b"Source:", self.read(".dict"))
        self.assertEqual([w for w, _ in self.lookup("EV")], ["earned value"])
        self.assertEqual([w for w, _ in self.lookup("RACI")], ["RACI matrix"])
        # An alias that is another term reaches both articles.
        self.assertEqual([w for w, _ in self.lookup("work package")],
                         ["RACI matrix", "work package"])

    def test_without_aliases_writes_no_syn(self):
        # Only "term" and "definition" are needed.
        entries = [{"term": e["term"], "definition": e["definition"]} for e in ENTRIES]
        result = self.run_script(self.source(entries), self.out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.outputs(), ["Out.dict", "Out.idx", "Out.ifo"])
        fields = dict(line.split("=", 1) for line in self.read(".ifo").decode("utf-8").splitlines()[1:])
        self.assertNotIn("synwordcount", fields)
        self.assertEqual(fields["bookname"], "Out")
        self.assertEqual(result.stdout.splitlines()[0], "terms: 4  aliases: 0")

    def test_refuses_to_overwrite(self):
        source = self.source(ENTRIES)
        with open(self.out + ".ifo", "w", encoding="utf-8") as f:
            f.write("mine")
        before = hashlib.sha256(self.read(".ifo")).hexdigest()
        result = self.run_script(source, self.out)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr.strip(), f"refusing to overwrite: {self.out}.ifo")
        self.assertEqual(hashlib.sha256(self.read(".ifo")).hexdigest(), before)
        self.assertEqual(self.outputs(), ["Out.ifo"])

    def test_rejects_bad_entries_and_writes_nothing(self):
        cases = [
            (ENTRIES + [dict(ENTRIES[0])], "entry 5: term 'work package' appears twice"),
            ([dict(ENTRIES[0], definition=" ")], "entry 1: missing or empty 'definition'"),
            ([{k: v for k, v in ENTRIES[0].items() if k != "term"}],
             "entry 1: missing or empty 'term'"),
            ([dict(ENTRIES[2], aliases="EV")],
             "entry 1 (earned value): 'aliases' is not a list of non-empty strings"),
            ({"term": "x"}, "the top level is not a list of entries"),
        ]
        for entries, message in cases:
            with self.subTest(message=message):
                source = self.source(entries)
                result = self.run_script(source, self.out)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr.strip(), f"{source}: {message}")
                self.assertEqual(self.outputs(), [])

    def test_rejects_invalid_json(self):
        source = self.source(None, raw="[{")
        result = self.run_script(source, self.out)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.startswith(f"{source}: not readable as JSON: "))
        self.assertEqual(self.outputs(), [])


if __name__ == "__main__":
    unittest.main()
