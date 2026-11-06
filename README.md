# Project Management Commons

A free English dictionary of 408 project management terms, from *acceptance criteria* to *working agreements*, as a JSON file and as a StarDict dictionary.

- 342 definitions are original, written for this dictionary.
- 66 come from free sources, 3 verbatim and 63 adapted: TERMIUM Plus, Wikipedia, the PM² Guide, the U.S. GAO, NASA, Wikidata and the DAU glossary.
- The spelling is American throughout, so a definition taken from a source in British English is adapted to it.

## Files

- `dictionary-en.json`: the dictionary, a list of entries. Each entry has a `term`, its `aliases` (abbreviations and other names), its `definition` and its `attribution`, plus the `source`, `licence` and `url` the attribution is made of, and whether the definition is `original` or `adapted` from its source.
- `json-to-stardict.py`: builds the StarDict dictionary from `dictionary-en.json`.
- The [releases](https://github.com/Ypot/pm-commons/releases) hold the StarDict dictionary, ready to use.

## Use it in a dictionary program

Unzip the release into the dictionary folder of a StarDict reader, such as GoldenDict, KOReader or StarDict itself. Each article shows the definition. Aliases lead to their term: *EV* finds *earned value*. The dictionary's information, as the reader shows it, gives the licence and points here for the sources.

## Build the StarDict dictionary

```sh
python json-to-stardict.py dictionary-en.json Ypot-2026-Project_Management_Commons \
  --bookname "Project Management Commons" \
  --description "Project Management Commons by Ypot, licensed under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Definitions taken from other works are credited, with their source, licence and changes, in dictionary-en.json at https://github.com/Ypot/pm-commons. Contains information licensed under the Open Government Licence – Canada (https://open.canada.ca/en/open-government-licence-canada)"
```

Keep the description when you build it: it is where the StarDict dictionary credits its sources. The script needs Python 3 and nothing else, never overwrites existing files, and reads its output back before reporting success. The tests run with `python -m unittest test_json_to_stardict`.

## Licence and sources

- The dictionary, `dictionary-en.json` and the StarDict dictionary built from it, is licensed under [CC BY-SA 4.0](LICENSE).
- Each definition taken from another work names in its `attribution` the work, its licence (CC BY-SA 4.0, CC BY 4.0, Open Government Licence – Canada 2.0, CC0 1.0 or public domain), its address and whether it was adapted. Keep that attribution when you reuse the definition.
- Contains information licensed under the [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada).
- The code is licensed under the [GNU General Public License, version 3 or later](COPYING).
