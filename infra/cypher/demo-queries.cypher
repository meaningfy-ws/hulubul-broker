// Hulubul demo Cypher queries — run with: make neo4j-queries
// Each block is a self-contained query demonstrating a retrieval an agent
// (or the matching/recovery/dashboard) would perform against the graph.
// Section headers are printed via :echo-style comments; cypher-shell runs
// every statement in sequence.

// ===========================================================================
// Q1 — Schema introspection (what the MCP `get_*` tools expose to an agent).
// ===========================================================================
// Labels present in the graph:
CALL db.labels() YIELD label RETURN collect(label) AS labels;

// Relationship types:
CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS relationshipTypes;

// Property keys:
CALL db.propertyKeys() YIELD propertyKey RETURN collect(propertyKey) AS propertyKeys;

// ===========================================================================
// Q2 — Transporter profiles + served base/destination areas.
// ===========================================================================
MATCH (a:Agent)-[:PROVIDES_SERVICE]->(s:TransportService)
OPTIONAL MATCH (s)-[r:HAS_BASE_AREA|HAS_DESTINATION_AREA]->(o:ServiceOffer)-[:WITHIN_AREA]->(area:Area)
RETURN a.name AS transporter, s.serviceTitle AS service, s.serviceType AS types,
       [x IN collect(DISTINCT CASE type(r) WHEN 'HAS_BASE_AREA' THEN area.locality + ' (' + area.country + ')' END) WHERE x IS NOT NULL] AS baseAreas,
       [x IN collect(DISTINCT CASE type(r) WHEN 'HAS_DESTINATION_AREA' THEN area.locality + ' (' + area.country + ')' END) WHERE x IS NOT NULL] AS destinationAreas
ORDER BY transporter;

// ===========================================================================
// Q3 — Matching primitive: eligible transporters for a route
//      (pickup Area -> drop-off Area). Here: München (DE) -> Chișinău (MD).
// ===========================================================================
MATCH (pickup:Area {locality:'München'}), (dropoff:Area {locality:'Chișinău'})
MATCH (a:Agent)-[:PROVIDES_SERVICE]->(s:TransportService)
MATCH (s)-[:HAS_BASE_AREA]->(bo:ServiceOffer)-[:WITHIN_AREA]->(pickup)
MATCH (s)-[:HAS_DESTINATION_AREA]->(do:ServiceOffer)-[:WITHIN_AREA]->(dropoff)
RETURN a.name AS transporter, s.serviceTitle AS service,
       bo.withFrequency AS baseFrequency, do.withFrequency AS destinationFrequency;

// ===========================================================================
// Q4 — Open requests per sender (status not yet terminal).
// ===========================================================================
MATCH (req:DeliveryRequest)-[:HAS_SENDER]->(:Sender)-[:PLAYED_BY]->(a:Agent)
WHERE NOT req.hasStatus IN ['delivered', 'closed', 'cancelled']
RETURN a.name AS sender, req.id AS request, req.hasStatus AS status, req.created AS created
ORDER BY req.created;

// ===========================================================================
// Q5 — Request snapshot: full neighbourhood of one request
//      (participants, parcels, locations, status). This is the "request
//      snapshot" tool an agent would call during brokerage.
// ===========================================================================
MATCH (req:DeliveryRequest {id:'req-001'})
OPTIONAL MATCH (req)-[:HAS_SENDER]->(s:Sender)-[:PLAYED_BY]->(sender:Agent)
OPTIONAL MATCH (req)-[:HAS_RECEIVER]->(r:Receiver)-[:PLAYED_BY]->(receiver:Agent)
OPTIONAL MATCH (req)-[:HAS_TRANSPORTER]->(t:Transporter)-[:PLAYED_BY]->(transporter:Agent)
OPTIONAL MATCH (req)-[:HAS_DELIVERY_ITEM]->(p:Parcel)
OPTIONAL MATCH (req)-[:HAS_PICK_UP_LOCATION]->(pu)
OPTIONAL MATCH (req)-[:HAS_DROP_OFF_LOCATION]->(do)
RETURN req.id AS request, req.hasStatus AS status,
       sender.name AS sender, receiver.name AS receiver, transporter.name AS transporter,
       collect(DISTINCT p.declaredContent) AS parcels,
       head([l IN [pu] | labels(l)[0]]) AS pickupType,
       head([l IN [do] | labels(l)[0]]) AS dropoffType;

// ===========================================================================
// Q6 — Reputation: average feedback rating per transporter role
//      (Feedback -[:TO_RECIPIENT]-> Transporter).
// ===========================================================================
MATCH (t:Transporter)<-[:TO_RECIPIENT]-(fb:Feedback)
MATCH (t)-[:PLAYED_BY]->(a:Agent)
RETURN a.name AS transporter, count(fb) AS feedbackCount,
       round(avg(fb.rating) * 100) / 100 AS avgRating
ORDER BY avgRating DESC;

// ===========================================================================
// Q7 — Dispatch reachability: validated contact points per transporter.
// ===========================================================================
MATCH (a:Agent)-[:PROVIDES_SERVICE]->(:TransportService)
MATCH (a)-[:HAS_CONTACT_POINT]->(c:Channel)
WHERE c.validationStatus = 'valid'
RETURN a.name AS transporter,
       collect(c.hasMedium + ': ' + coalesce(c.systemID, '')) AS usableChannels
ORDER BY transporter;

// ===========================================================================
// Q8 — Request count by status (dashboard / recovery-sweep primitive).
// ===========================================================================
MATCH (req:DeliveryRequest)
RETURN req.hasStatus AS status, count(*) AS count
ORDER BY status;

// ===========================================================================
// Q9 — Recovery primitive: requests waiting longer than a threshold
//      (candidates for a nudge/timeout in the scheduler sweep, ADR-010).
// ===========================================================================
MATCH (req:DeliveryRequest)
WHERE req.hasStatus = 'waitingResponse'
RETURN req.id AS request, req.updated AS lastUpdated,
       duration.between(req.updated, datetime()).hours AS hoursWaiting
ORDER BY lastUpdated;
