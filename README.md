# Project Management Commons

A free English dictionary of 408 project management terms, from *acceptance criteria* to *working agreements*, as a JSON file and as a StarDict dictionary.

- 325 definitions are original, written for this dictionary.
- 83 come from free sources, 5 verbatim and 78 adapted: TERMIUM Plus, Wikipedia, the PM² Guide, the U.S. GAO, NASA, Wikidata and the DAU glossary.
- Every entry names its source and licence.

## Files

- `dictionary-en.json`: the dictionary, a list of entries. Each entry has a `term`, its `aliases` (abbreviations and other names), its `definition` and its `attribution`, plus the `source`, `licence` and `url` the attribution is made of, and whether the definition is `original` or `adapted` from its source.
- `json-to-stardict.py`: builds the StarDict dictionary from `dictionary-en.json`.
- The [releases](https://github.com/Ypot/pm-commons/releases) hold the StarDict dictionary, ready to use.

## Use it in a dictionary program

Unzip the release into the dictionary folder of a StarDict reader, such as GoldenDict, KOReader or StarDict itself. Each article shows the definition and, below it, its attribution. Aliases lead to their term: *EV* finds *earned value*.

## Build the StarDict dictionary

```sh
python json-to-stardict.py dictionary-en.json Ypot-2026-Project_Management_Commons --bookname "Project Management Commons"
```

It needs Python 3 and nothing else, never overwrites existing files, and reads its output back before reporting success. The tests run with `python -m unittest test_json_to_stardict`.

## Licence

- The dictionary, `dictionary-en.json` and the StarDict dictionary built from it, is licensed under [CC BY-SA 4.0](LICENSE). The entries taken from free sources carry in their `attribution` what their source's licence requires; keep it when you reuse them.
- The code is licensed under the [GNU General Public License, version 3 or later](COPYING).
