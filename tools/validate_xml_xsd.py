#!/usr/bin/env python
"""Validate an XML file against an XSD schema (FNS-style, cp1251).

Usage:
  python tools/validate_xml_xsd.py <file.xml> <schema.xsd>

Loads the schema (xs:appinfo schematron rules are ignored by the XSD validator —
structure/types/enumerations are checked, not the sch: business asserts).
Prints VALID, or INVALID with the schema error list.
"""
import sys
from lxml import etree


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    xml_path, xsd_path = sys.argv[1], sys.argv[2]
    schema = etree.XMLSchema(etree.parse(xsd_path))
    doc = etree.parse(xml_path)
    if schema.validate(doc):
        print("VALID")
        return
    print("INVALID")
    for e in schema.error_log:
        print(f"  line {e.line}: {e.message}")
    sys.exit(1)


if __name__ == "__main__":
    main()
