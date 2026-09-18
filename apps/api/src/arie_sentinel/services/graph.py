"""Relationship graph derived from stored, provenance-bearing records.

Nodes and edges are computed from what the investigation actually established — no
relationship is invented, and every edge carries its basis and source ids. The graph
is derived on read (not a separate persisted graph store): PostgreSQL already holds
the underlying records, so no graph database is introduced.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.core import Identifier, Investigation
from ..models.enums import RelationshipState, ScreeningState, SourceClass
from ..models.evidence import Evidence, ScreeningResult, Source
from ..providers.normalization import normalize_entity_name
from .contradictions import REGULATOR_LICENCE_LICENSE_CLASS


# Node types: Company | Person | Address | Domain | LEI | Regulator | SanctionsEntity
@dataclass(frozen=True)
class GraphNode:
    id: str
    type: str
    label: str
    detail: str = ""


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    type: str  # DIRECTOR_OF | REGISTERED_AT | USES_DOMAIN | ... (see module docstring domains)
    basis: str
    state: str
    source_ids: list[uuid.UUID] = field(default_factory=list)


@dataclass(frozen=True)
class Graph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]


def build_graph(session: Session, investigation: Investigation) -> Graph:
    inv = investigation
    counterparty = inv.counterparty
    company_id = "company:subject"
    company_label = counterparty.legal_name if counterparty else inv.company_label
    nodes: dict[str, GraphNode] = {
        company_id: GraphNode(company_id, "Company", company_label, "Subject of the investigation")
    }
    edges: list[GraphEdge] = []

    def add_node(node: GraphNode) -> str:
        nodes.setdefault(node.id, node)
        return node.id

    rows = list(
        session.execute(
            select(Evidence, Source)
            .join(Source, Evidence.source_id == Source.source_id)
            .where(Source.investigation_id == inv.investigation_id)
        )
    )

    # Registered address (from any registry evidence carrying one)
    for evidence, source in rows:
        observed = evidence.observed_value or {}
        address = observed.get("registered_address")
        if (
            source.source_class is SourceClass.CORPORATE_REGISTRY
            and isinstance(address, str)
            and address
        ):
            node_id = add_node(
                GraphNode(f"address:{normalize_entity_name(address)}", "Address", address)
            )
            edges.append(
                GraphEdge(
                    company_id,
                    node_id,
                    "REGISTERED_AT",
                    "Registry record lists this registered address.",
                    "REPORTED",
                    [source.source_id],
                )
            )
            break

    # Officers (registry) -> DIRECTOR_OF / OFFICER_OF, with source provenance.
    officer_names: set[str] = set()
    officer_sources: dict[str, list[uuid.UUID]] = {}
    for evidence, source in rows:
        observed = evidence.observed_value or {}
        position = observed.get("position")
        name = observed.get("name")
        if (
            source.source_class is SourceClass.CORPORATE_REGISTRY
            and position
            and isinstance(name, str)
        ):
            norm = normalize_entity_name(name)
            node_id = add_node(GraphNode(f"person:{norm}", "Person", name, str(position)))
            edge_type = "DIRECTOR_OF" if "director" in str(position).lower() else "OFFICER_OF"
            edges.append(
                GraphEdge(
                    node_id,
                    company_id,
                    edge_type,
                    f"Registry lists {name} as {position}.",
                    "CORROBORATED",
                    [source.source_id],
                )
            )
            officer_names.add(norm)
            officer_sources.setdefault(norm, []).append(source.source_id)

    # Persons with significant control (Companies House PSC) -> accurate relationship
    # type PERSON_WITH_SIGNIFICANT_CONTROL_OF, with source provenance.
    for evidence, source in rows:
        observed = evidence.observed_value or {}
        if observed.get("kind") != "psc":
            continue
        name = observed.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        natures = observed.get("natures_of_control")
        nature_text = ", ".join(str(n) for n in natures) if isinstance(natures, list) else ""
        norm = normalize_entity_name(name)
        node_id = add_node(GraphNode(f"person:{norm}", "Person", name, "PSC"))
        suffix = f" ({nature_text})." if nature_text else "."
        edges.append(
            GraphEdge(
                node_id,
                company_id,
                "PERSON_WITH_SIGNIFICANT_CONTROL_OF",
                f"Companies House records this person as having significant control{suffix}",
                "CORROBORATED",
                [source.source_id],
            )
        )

    # Supplied contact -> relationship edge, faithfully preserving the evidence state.
    # Evidence-backed relations (VERIFIED/CORROBORATED) carry the officer source ids;
    # a pure intake claim carries no external source and is clearly marked CLAIMED.
    state_map = {
        RelationshipState.VERIFIED: ("OFFICER_OF", "CONFIRMED"),
        RelationshipState.CORROBORATED: ("ASSOCIATED_WITH", "CORROBORATED"),
        RelationshipState.SELF_ASSERTED: ("CLAIMS_TO_REPRESENT", "CLAIMED"),
        RelationshipState.UNVERIFIED: ("CLAIMS_TO_REPRESENT", "UNVERIFIED"),
        RelationshipState.CONTRADICTED: ("CLAIMS_TO_REPRESENT", "CONTRADICTED"),
    }
    for candidate in inv.candidates:
        norm = normalize_entity_name(candidate.label_fragment)
        # A verified contact already appears as an officer edge (with provenance).
        if candidate.relationship_state is RelationshipState.VERIFIED and norm in officer_names:
            continue
        person_id = add_node(GraphNode(f"person:{norm}", "Person", candidate.label_fragment))
        rel_state = candidate.relationship_state or RelationshipState.UNVERIFIED
        edge_type, state = state_map.get(rel_state, ("CLAIMS_TO_REPRESENT", "UNVERIFIED"))
        evidence_ids = officer_sources.get(norm, [])
        if evidence_ids:
            basis = candidate.match_basis or "Registry evidence links this person to the company."
        else:
            basis = candidate.match_basis or (
                "Supplied contact (intake claim); no independent relationship evidence retained."
            )
        edges.append(GraphEdge(person_id, company_id, edge_type, basis, state, list(evidence_ids)))

    # Domains -> USES_DOMAIN
    for evidence, source in rows:
        observed = evidence.observed_value or {}
        domain = observed.get("domain")
        if source.source_class is SourceClass.DOMAIN_REGISTRATION and isinstance(domain, str):
            node_id = add_node(GraphNode(f"domain:{domain}", "Domain", domain))
            edges.append(
                GraphEdge(
                    company_id,
                    node_id,
                    "USES_DOMAIN",
                    "Domain associated with the company (ownership not proven).",
                    "REPORTED",
                    [source.source_id],
                )
            )

    # LEI node
    if counterparty is not None:
        lei = session.scalar(
            select(Identifier.id_value).where(
                Identifier.counterparty_id == counterparty.counterparty_id,
                Identifier.id_type == "lei",
            )
        )
        if lei:
            gleif_sources = [
                s.source_id
                for _, s in rows
                if s.source_class is SourceClass.CORPORATE_REGISTRY
                and s.title.startswith("GLEIF LEI record")
            ]
            node_id = add_node(GraphNode(f"lei:{lei}", "LEI", lei))
            edges.append(
                GraphEdge(
                    company_id,
                    node_id,
                    "HAS_LEI",
                    "GLEIF legal-entity identifier for the resolved company.",
                    "CONFIRMED" if gleif_sources else "REPORTED",
                    gleif_sources,
                )
            )

    # GLEIF direct parent/child -> PARENT_OF (with provenance).
    for evidence, source in rows:
        observed = evidence.observed_value or {}
        if observed.get("kind") != "gleif_relationships":
            continue
        parent_lei = observed.get("parent_lei")
        if isinstance(parent_lei, str) and parent_lei:
            node_id = add_node(
                GraphNode(f"lei:{parent_lei}", "Company", parent_lei, "GLEIF parent")
            )
            edges.append(
                GraphEdge(
                    node_id,
                    company_id,
                    "PARENT_OF",
                    "GLEIF records this entity as the direct parent.",
                    "CONFIRMED",
                    [source.source_id],
                )
            )
        children = observed.get("child_leis")
        if isinstance(children, list):
            for child in children:
                if not isinstance(child, str) or not child:
                    continue
                node_id = add_node(GraphNode(f"lei:{child}", "Company", child, "GLEIF subsidiary"))
                edges.append(
                    GraphEdge(
                        company_id,
                        node_id,
                        "PARENT_OF",
                        "GLEIF records the company as the direct parent of this entity.",
                        "CONFIRMED",
                        [source.source_id],
                    )
                )

    # Regulator / licence sources -> LICENSED_BY. Only a regulator's verification of
    # this entity's licence qualifies; a corporate registry / generic government
    # publication does NOT establish a licensing relationship.
    for source in {s for _, s in rows}:
        if (
            source.license_class == REGULATOR_LICENCE_LICENSE_CLASS
            and source.source_class is not SourceClass.CORPORATE_REGISTRY
        ):
            node_id = add_node(
                GraphNode(f"regulator:{source.source_id}", "Regulator", source.title)
            )
            edges.append(
                GraphEdge(
                    company_id,
                    node_id,
                    "LICENSED_BY",
                    source.limitations or "Regulator verification retained.",
                    "CORROBORATED",
                    [source.source_id],
                )
            )

    # Potential sanctions matches -> MATCHED_TO
    screening = session.scalars(
        select(ScreeningResult).where(
            ScreeningResult.investigation_id == inv.investigation_id,
            ScreeningResult.state.in_(
                [ScreeningState.POTENTIAL_MATCH, ScreeningState.MATCH_REQUIRES_REVIEW]
            ),
        )
    )
    for result in screening:
        node_id = add_node(
            GraphNode(
                f"sanction:{result.screening_result_id}",
                "SanctionsEntity",
                result.matched_profile_id or result.list_or_source,
                result.list_or_source,
            )
        )
        edges.append(
            GraphEdge(
                company_id,
                node_id,
                "MATCHED_TO",
                result.match_basis or "Potential screening match — analyst review required.",
                result.state.value,
                [result.source_id] if result.source_id else [],
            )
        )

    return Graph(nodes=list(nodes.values()), edges=edges)
