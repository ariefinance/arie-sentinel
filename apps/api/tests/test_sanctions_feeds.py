"""Parser contract tests against representative samples of each official feed schema."""

from __future__ import annotations

from arie_sentinel.providers.sanctions_feeds import (
    parse_eu_fsf,
    parse_ofac_sdn,
    parse_uk_sanctions,
    parse_un_consolidated,
)

OFAC = b"""<?xml version="1.0"?>
<sdnList xmlns="http://tempuri.org/sdnList.xsd">
  <sdnEntry>
    <uid>36</uid>
    <firstName>ABU</firstName>
    <lastName>SALEM</lastName>
    <sdnType>Individual</sdnType>
    <akaList><aka><type>a.k.a.</type><firstName>ABU</firstName><lastName>SALIM</lastName></aka></akaList>
    <dateOfBirthList><dateOfBirthItem><dateOfBirth>1965</dateOfBirth></dateOfBirthItem></dateOfBirthList>
    <nationalityList><nationality><country>India</country></nationality></nationalityList>
    <idList><id><idType>Passport</idType><idNumber>A123456</idNumber></id></idList>
  </sdnEntry>
  <sdnEntry>
    <uid>77</uid>
    <lastName>ACME FRONT CO</lastName>
    <sdnType>Entity</sdnType>
  </sdnEntry>
</sdnList>"""

UN = b"""<?xml version="1.0"?>
<CONSOLIDATED_LIST>
  <INDIVIDUALS>
    <INDIVIDUAL>
      <DATAID>6908555</DATAID>
      <FIRST_NAME>MOHAMMED</FIRST_NAME>
      <SECOND_NAME>OMAR</SECOND_NAME>
      <NATIONALITY><VALUE>Afghanistan</VALUE></NATIONALITY>
      <INDIVIDUAL_ALIAS><ALIAS_NAME>Mullah Omar</ALIAS_NAME></INDIVIDUAL_ALIAS>
      <INDIVIDUAL_DATE_OF_BIRTH><YEAR>1960</YEAR></INDIVIDUAL_DATE_OF_BIRTH>
      <INDIVIDUAL_DOCUMENT><NUMBER>P999</NUMBER></INDIVIDUAL_DOCUMENT>
    </INDIVIDUAL>
  </INDIVIDUALS>
  <ENTITIES>
    <ENTITY><DATAID>1</DATAID><FIRST_NAME>Acme Front Co</FIRST_NAME>
      <ENTITY_ALIAS><ALIAS_NAME>Acme</ALIAS_NAME></ENTITY_ALIAS></ENTITY>
  </ENTITIES>
</CONSOLIDATED_LIST>"""

UK = b"""<?xml version="1.0"?>
<Designations>
  <Designation>
    <GroupID>7</GroupID>
    <GroupTypeDescription>Individual</GroupTypeDescription>
    <Names><Name><Name6>John Doe</Name6></Name></Names>
    <Aliases><Alias>Johnny</Alias></Aliases>
    <DateOfBirth>1970-01-01</DateOfBirth>
    <Nationality>Testland</Nationality>
    <PassportNumber>X999</PassportNumber>
  </Designation>
</Designations>"""

EU = b"""<?xml version="1.0"?>
<export>
  <sanctionEntity euReferenceNumber="EU.1.2">
    <subjectType code="person"/>
    <nameAlias wholeName="Ivan Ivanov" firstName="Ivan" lastName="Ivanov"/>
    <nameAlias wholeName="I. Ivanov"/>
    <birthdate birthdate="1980-05-05"/>
    <citizenship countryDescription="Russia"/>
    <identification number="PASS123"/>
  </sanctionEntity>
</export>"""


def test_parse_ofac_person_and_entity() -> None:
    rows = parse_ofac_sdn(OFAC)
    assert [r.name for r in rows] == ["ABU SALEM", "ACME FRONT CO"]
    person = rows[0]
    assert person.entity_type == "person"
    assert person.source_list == "OFAC"
    assert "ABU SALIM" in person.aliases
    assert person.birth_dates == ("1965",)
    assert person.countries == ("India",)
    assert person.identifiers == ("A123456",)
    assert rows[1].entity_type == "entity"


def test_parse_un_individual_and_entity() -> None:
    rows = parse_un_consolidated(UN)
    names = {r.name for r in rows}
    assert "MOHAMMED OMAR" in names
    assert "Acme Front Co" in names
    person = next(r for r in rows if r.name == "MOHAMMED OMAR")
    assert person.entity_type == "person"
    assert person.birth_dates == ("1960",)
    assert person.countries == ("Afghanistan",)
    assert "Mullah Omar" in person.aliases
    assert person.identifiers == ("P999",)


def test_parse_uk_designation() -> None:
    rows = parse_uk_sanctions(UK)
    assert len(rows) == 1
    row = rows[0]
    assert row.name == "John Doe"
    assert row.entity_type == "person"
    assert row.aliases == ("Johnny",)
    assert row.birth_dates == ("1970-01-01",)
    assert row.identifiers == ("X999",)
    assert row.source_list == "UK"


def test_parse_eu_sanction_entity() -> None:
    rows = parse_eu_fsf(EU)
    assert len(rows) == 1
    row = rows[0]
    assert row.name == "Ivan Ivanov"
    assert row.aliases == ("I. Ivanov",)
    assert row.entity_type == "person"
    assert row.birth_dates == ("1980-05-05",)
    assert row.countries == ("Russia",)
    assert row.identifiers == ("PASS123",)


def test_empty_feed_yields_no_entities_not_error() -> None:
    assert parse_ofac_sdn(b"<sdnList></sdnList>") == []
    assert parse_un_consolidated(b"<CONSOLIDATED_LIST></CONSOLIDATED_LIST>") == []
    assert parse_uk_sanctions(b"<Designations></Designations>") == []
    assert parse_eu_fsf(b"<export></export>") == []
