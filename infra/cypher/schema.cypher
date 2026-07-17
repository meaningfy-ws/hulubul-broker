// Hulubul Neo4j schema — Community-safe subset + query indexes.
// Idempotent: every statement uses IF NOT EXISTS.
//
// Source of truth: model/linkml/hulubul.yaml (via make neo4j-constraints).
// This file applies ONLY what Neo4j Community can enforce:
//   * identifier slot -> uniqueness constraint  (Community)
// Existence (`IS NOT NULL`) and property-type (`IS :: TYPE`) constraints need
// Neo4j Enterprise and are intentionally omitted here (they are present in
// model/generated/neo4j/constraints.cypher for reference / Enterprise upgrades).
// The range indexes below are not generated (they encode query access paths,
// not the model) and are maintained by hand in this file.

// ============================================================================
// Uniqueness constraints (one per entity label — the `id` identifier slot).
// Mirrors the `IS UNIQUE` lines of model/generated/neo4j/constraints.cypher.
// ============================================================================
CREATE CONSTRAINT address_id_unique IF NOT EXISTS
FOR (n:Address) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT agent_id_unique IF NOT EXISTS
FOR (n:Agent) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT area_id_unique IF NOT EXISTS
FOR (n:Area) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT channel_id_unique IF NOT EXISTS
FOR (n:Channel) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT deliveryrequest_id_unique IF NOT EXISTS
FOR (n:DeliveryRequest) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT feedback_id_unique IF NOT EXISTS
FOR (n:Feedback) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT parcel_id_unique IF NOT EXISTS
FOR (n:Parcel) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT place_id_unique IF NOT EXISTS
FOR (n:Place) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT receiver_id_unique IF NOT EXISTS
FOR (n:Receiver) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT sender_id_unique IF NOT EXISTS
FOR (n:Sender) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT serviceoffer_id_unique IF NOT EXISTS
FOR (n:ServiceOffer) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT transportservice_id_unique IF NOT EXISTS
FOR (n:TransportService) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT transporter_id_unique IF NOT EXISTS
FOR (n:Transporter) REQUIRE n.id IS UNIQUE;

// ============================================================================
// Range indexes on hot query properties (access paths used by the agents /
// demo queries). Hand-maintained — not part of the generated model.
// ============================================================================
// Agent lookup by business identifier / name.
CREATE INDEX agent_identifier_idx IF NOT EXISTS FOR (n:Agent) ON (n.identifier);
CREATE INDEX agent_name_idx IF NOT EXISTS FOR (n:Agent) ON (n.name);
// Request lifecycle queries (status histogram, recovery sweep, ordering).
CREATE INDEX deliveryrequest_hasStatus_idx IF NOT EXISTS FOR (n:DeliveryRequest) ON (n.hasStatus);
CREATE INDEX deliveryrequest_created_idx IF NOT EXISTS FOR (n:DeliveryRequest) ON (n.created);
// Channel resolution for dispatch / authentication.
CREATE INDEX channel_systemID_idx IF NOT EXISTS FOR (n:Channel) ON (n.systemID);
CREATE INDEX channel_hasMedium_idx IF NOT EXISTS FOR (n:Channel) ON (n.hasMedium);
CREATE INDEX channel_validationStatus_idx IF NOT EXISTS FOR (n:Channel) ON (n.validationStatus);
// Area lookup for matching (locality / county / country).
CREATE INDEX area_locality_idx IF NOT EXISTS FOR (n:Area) ON (n.locality);
CREATE INDEX area_county_idx IF NOT EXISTS FOR (n:Area) ON (n.county);
CREATE INDEX area_country_idx IF NOT EXISTS FOR (n:Area) ON (n.country);
// Service search.
CREATE INDEX transportservice_serviceTitle_idx IF NOT EXISTS FOR (n:TransportService) ON (n.serviceTitle);
CREATE INDEX serviceoffer_withFrequency_idx IF NOT EXISTS FOR (n:ServiceOffer) ON (n.withFrequency);
// Parcel content search.
CREATE INDEX parcel_declaredContent_idx IF NOT EXISTS FOR (n:Parcel) ON (n.declaredContent);
// Place lookup.
CREATE INDEX place_name_idx IF NOT EXISTS FOR (n:Place) ON (n.name);
CREATE INDEX place_hasType_idx IF NOT EXISTS FOR (n:Place) ON (n.hasType);
// Feedback reputation aggregation.
CREATE INDEX feedback_rating_idx IF NOT EXISTS FOR (n:Feedback) ON (n.rating);
