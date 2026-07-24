// Operational conversation binding — application-owned outside LinkML.
// Unique binding per session ID; active-request link via BINDS_ACTIVE_REQUEST
// relationship only (never a foreign-key property).
CREATE CONSTRAINT operationalconversationbinding_sessionId_unique IF NOT EXISTS
FOR (n:OperationalConversationBinding) REQUIRE n.sessionId IS UNIQUE;
