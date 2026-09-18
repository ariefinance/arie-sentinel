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

    # Officers (registry) -> DIRECTOR_OF / OFFICER_OF
    for evidence, source in rows:
        observed = evidence.observed_value or {}
        position = observed.get("position")
        name = observed.get("name")
        if (
            source.source_class is SourceClass.CORPORATE_REGISTRY
            and position
            and isinstance(name, str)
        ):
            node_id = add_node(
                GraphNode(f"person:{normalize_entity_name(name)}", "Person", name, str(position))
            )
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

    # Supplied contact -> relationship edge
    for candidate in inv.candidates:
        person_id = add_node(
            GraphNode(
                f"person:{normalize_entity_name(candidate.label_fragment)}",
                "Person",
                candidate.label_fragment,
            )
        )
        if candidate.relationship_state is RelationshipState.VERIFIED:
            edge_type, state = "OFFICER_OF", "CONFIRMED"
        else:
            edge_type, state = "CLAIMS_TO_REPRESENT", "UNVERIFIED"
        edges.append(
            GraphEdge(
                person_id,
                company_id,
                edge_type,
                candidate.match_basis or "Supplied contact; relationship not established.",
                state,
                [],
            )
        )

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
            node_id = add_node(GraphNode(f"lei:{lei}", "LEI", lei))
            edges.append(
                GraphEdge(
                    company_id,
                    node_id,
                    "MATCHED_TO",
                    "GLEIF legal-entity identifier.",
                    "CONFIRMED",
                    [],
                )
            )

    # Regulator / licence sources -> LICENSED_BY (reported/claimed)
    for source in {s for _, s in rows}:
        if (
            source.license_class == "public-government-source"
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
                    source.limitations or "Regulatory source retained.",
                    "REPORTED",
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
