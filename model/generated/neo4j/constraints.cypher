// Neo4j constraints generated from hulubul
// DO NOT EDIT — regenerate with `make neo4j-constraints`.
// Uniqueness runs on Community Edition; existence/type need Enterprise.
// ---- Address -------------------------------------------------------------
CREATE CONSTRAINT address_id_unique IF NOT EXISTS
FOR (n:`Address`) REQUIRE n.`id` IS UNIQUE;  // NODE KEY on Enterprise
CREATE CONSTRAINT address_number_exists IF NOT EXISTS
FOR (n:`Address`) REQUIRE n.`number` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT address_number_type IF NOT EXISTS
FOR (n:`Address`) REQUIRE n.`number` IS :: STRING;  // Enterprise
CREATE CONSTRAINT address_street_exists IF NOT EXISTS
FOR (n:`Address`) REQUIRE n.`street` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT address_street_type IF NOT EXISTS
FOR (n:`Address`) REQUIRE n.`street` IS :: STRING;  // Enterprise
CREATE CONSTRAINT address_postCode_exists IF NOT EXISTS
FOR (n:`Address`) REQUIRE n.`postCode` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT address_postCode_type IF NOT EXISTS
FOR (n:`Address`) REQUIRE n.`postCode` IS :: STRING;  // Enterprise
CREATE CONSTRAINT address_comment_type IF NOT EXISTS
FOR (n:`Address`) REQUIRE n.`comment` IS :: STRING;  // Enterprise

// ---- Agent ---------------------------------------------------------------
CREATE CONSTRAINT agent_id_unique IF NOT EXISTS
FOR (n:`Agent`) REQUIRE n.`id` IS UNIQUE;  // NODE KEY on Enterprise
CREATE CONSTRAINT agent_name_exists IF NOT EXISTS
FOR (n:`Agent`) REQUIRE n.`name` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT agent_name_type IF NOT EXISTS
FOR (n:`Agent`) REQUIRE n.`name` IS :: STRING;  // Enterprise
CREATE CONSTRAINT agent_description_type IF NOT EXISTS
FOR (n:`Agent`) REQUIRE n.`description` IS :: STRING;  // Enterprise
CREATE CONSTRAINT agent_identifier_exists IF NOT EXISTS
FOR (n:`Agent`) REQUIRE n.`identifier` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT agent_identifier_type IF NOT EXISTS
FOR (n:`Agent`) REQUIRE n.`identifier` IS :: STRING;  // Enterprise

// ---- Area ----------------------------------------------------------------
CREATE CONSTRAINT area_id_unique IF NOT EXISTS
FOR (n:`Area`) REQUIRE n.`id` IS UNIQUE;  // NODE KEY on Enterprise
CREATE CONSTRAINT area_locality_type IF NOT EXISTS
FOR (n:`Area`) REQUIRE n.`locality` IS :: STRING;  // Enterprise
CREATE CONSTRAINT area_county_type IF NOT EXISTS
FOR (n:`Area`) REQUIRE n.`county` IS :: STRING;  // Enterprise
CREATE CONSTRAINT area_country_type IF NOT EXISTS
FOR (n:`Area`) REQUIRE n.`country` IS :: STRING;  // Enterprise
CREATE CONSTRAINT area_state_type IF NOT EXISTS
FOR (n:`Area`) REQUIRE n.`state` IS :: STRING;  // Enterprise
CREATE CONSTRAINT area_comment_type IF NOT EXISTS
FOR (n:`Area`) REQUIRE n.`comment` IS :: STRING;  // Enterprise

// ---- Channel -------------------------------------------------------------
CREATE CONSTRAINT channel_id_unique IF NOT EXISTS
FOR (n:`Channel`) REQUIRE n.`id` IS UNIQUE;  // NODE KEY on Enterprise
CREATE CONSTRAINT channel_description_type IF NOT EXISTS
FOR (n:`Channel`) REQUIRE n.`description` IS :: STRING;  // Enterprise
CREATE CONSTRAINT channel_alias_type IF NOT EXISTS
FOR (n:`Channel`) REQUIRE n.`alias` IS :: STRING;  // Enterprise
CREATE CONSTRAINT channel_systemID_exists IF NOT EXISTS
FOR (n:`Channel`) REQUIRE n.`systemID` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT channel_systemID_type IF NOT EXISTS
FOR (n:`Channel`) REQUIRE n.`systemID` IS :: STRING;  // Enterprise
CREATE CONSTRAINT channel_email_type IF NOT EXISTS
FOR (n:`Channel`) REQUIRE n.`email` IS :: STRING;  // Enterprise
CREATE CONSTRAINT channel_telephone_type IF NOT EXISTS
FOR (n:`Channel`) REQUIRE n.`telephone` IS :: STRING;  // Enterprise
CREATE CONSTRAINT channel_hasMedium_exists IF NOT EXISTS
FOR (n:`Channel`) REQUIRE n.`hasMedium` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT channel_hasMedium_type IF NOT EXISTS
FOR (n:`Channel`) REQUIRE n.`hasMedium` IS :: STRING;  // Enterprise
CREATE CONSTRAINT channel_validationStatus_exists IF NOT EXISTS
FOR (n:`Channel`) REQUIRE n.`validationStatus` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT channel_validationStatus_type IF NOT EXISTS
FOR (n:`Channel`) REQUIRE n.`validationStatus` IS :: STRING;  // Enterprise

// ---- DeliveryRequest -----------------------------------------------------
CREATE CONSTRAINT deliveryrequest_id_unique IF NOT EXISTS
FOR (n:`DeliveryRequest`) REQUIRE n.`id` IS UNIQUE;  // NODE KEY on Enterprise
CREATE CONSTRAINT deliveryrequest_preferredPeriod_type IF NOT EXISTS
FOR (n:`DeliveryRequest`) REQUIRE n.`preferredPeriod` IS :: STRING;  // Enterprise
CREATE CONSTRAINT deliveryrequest_created_exists IF NOT EXISTS
FOR (n:`DeliveryRequest`) REQUIRE n.`created` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT deliveryrequest_created_type IF NOT EXISTS
FOR (n:`DeliveryRequest`) REQUIRE n.`created` IS :: DATETIME;  // Enterprise
CREATE CONSTRAINT deliveryrequest_updated_exists IF NOT EXISTS
FOR (n:`DeliveryRequest`) REQUIRE n.`updated` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT deliveryrequest_updated_type IF NOT EXISTS
FOR (n:`DeliveryRequest`) REQUIRE n.`updated` IS :: DATETIME;  // Enterprise
CREATE CONSTRAINT deliveryrequest_closed_type IF NOT EXISTS
FOR (n:`DeliveryRequest`) REQUIRE n.`closed` IS :: DATETIME;  // Enterprise
CREATE CONSTRAINT deliveryrequest_hasStatus_exists IF NOT EXISTS
FOR (n:`DeliveryRequest`) REQUIRE n.`hasStatus` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT deliveryrequest_hasStatus_type IF NOT EXISTS
FOR (n:`DeliveryRequest`) REQUIRE n.`hasStatus` IS :: STRING;  // Enterprise

// ---- Feedback ------------------------------------------------------------
CREATE CONSTRAINT feedback_id_unique IF NOT EXISTS
FOR (n:`Feedback`) REQUIRE n.`id` IS UNIQUE;  // NODE KEY on Enterprise
CREATE CONSTRAINT feedback_rating_type IF NOT EXISTS
FOR (n:`Feedback`) REQUIRE n.`rating` IS :: INTEGER;  // Enterprise
CREATE CONSTRAINT feedback_comment_type IF NOT EXISTS
FOR (n:`Feedback`) REQUIRE n.`comment` IS :: STRING;  // Enterprise

// ---- Parcel --------------------------------------------------------------
CREATE CONSTRAINT parcel_id_unique IF NOT EXISTS
FOR (n:`Parcel`) REQUIRE n.`id` IS UNIQUE;  // NODE KEY on Enterprise
CREATE CONSTRAINT parcel_declaredContent_exists IF NOT EXISTS
FOR (n:`Parcel`) REQUIRE n.`declaredContent` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT parcel_declaredContent_type IF NOT EXISTS
FOR (n:`Parcel`) REQUIRE n.`declaredContent` IS :: STRING;  // Enterprise
CREATE CONSTRAINT parcel_weightKg_type IF NOT EXISTS
FOR (n:`Parcel`) REQUIRE n.`weightKg` IS :: FLOAT;  // Enterprise
CREATE CONSTRAINT parcel_dimensions_type IF NOT EXISTS
FOR (n:`Parcel`) REQUIRE n.`dimensions` IS :: STRING;  // Enterprise

// ---- Place ---------------------------------------------------------------
CREATE CONSTRAINT place_id_unique IF NOT EXISTS
FOR (n:`Place`) REQUIRE n.`id` IS UNIQUE;  // NODE KEY on Enterprise
CREATE CONSTRAINT place_name_type IF NOT EXISTS
FOR (n:`Place`) REQUIRE n.`name` IS :: STRING;  // Enterprise
CREATE CONSTRAINT place_hasIdentifier_exists IF NOT EXISTS
FOR (n:`Place`) REQUIRE n.`hasIdentifier` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT place_hasIdentifier_type IF NOT EXISTS
FOR (n:`Place`) REQUIRE n.`hasIdentifier` IS :: STRING;  // Enterprise
CREATE CONSTRAINT place_hasType_exists IF NOT EXISTS
FOR (n:`Place`) REQUIRE n.`hasType` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT place_hasType_type IF NOT EXISTS
FOR (n:`Place`) REQUIRE n.`hasType` IS :: STRING;  // Enterprise
CREATE CONSTRAINT place_comment_type IF NOT EXISTS
FOR (n:`Place`) REQUIRE n.`comment` IS :: STRING;  // Enterprise

// ---- Receiver ------------------------------------------------------------
CREATE CONSTRAINT receiver_id_unique IF NOT EXISTS
FOR (n:`Receiver`) REQUIRE n.`id` IS UNIQUE;  // NODE KEY on Enterprise
CREATE CONSTRAINT receiver_deliveryNote_type IF NOT EXISTS
FOR (n:`Receiver`) REQUIRE n.`deliveryNote` IS :: STRING;  // Enterprise

// ---- Sender --------------------------------------------------------------
CREATE CONSTRAINT sender_id_unique IF NOT EXISTS
FOR (n:`Sender`) REQUIRE n.`id` IS UNIQUE;  // NODE KEY on Enterprise

// ---- ServiceOffer --------------------------------------------------------
CREATE CONSTRAINT serviceoffer_id_unique IF NOT EXISTS
FOR (n:`ServiceOffer`) REQUIRE n.`id` IS UNIQUE;  // NODE KEY on Enterprise
CREATE CONSTRAINT serviceoffer_description_exists IF NOT EXISTS
FOR (n:`ServiceOffer`) REQUIRE n.`description` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT serviceoffer_description_type IF NOT EXISTS
FOR (n:`ServiceOffer`) REQUIRE n.`description` IS :: STRING;  // Enterprise
CREATE CONSTRAINT serviceoffer_withFrequency_exists IF NOT EXISTS
FOR (n:`ServiceOffer`) REQUIRE n.`withFrequency` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT serviceoffer_withFrequency_type IF NOT EXISTS
FOR (n:`ServiceOffer`) REQUIRE n.`withFrequency` IS :: STRING;  // Enterprise

// ---- TransportService ----------------------------------------------------
CREATE CONSTRAINT transportservice_id_unique IF NOT EXISTS
FOR (n:`TransportService`) REQUIRE n.`id` IS UNIQUE;  // NODE KEY on Enterprise
CREATE CONSTRAINT transportservice_description_exists IF NOT EXISTS
FOR (n:`TransportService`) REQUIRE n.`description` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT transportservice_description_type IF NOT EXISTS
FOR (n:`TransportService`) REQUIRE n.`description` IS :: STRING;  // Enterprise
CREATE CONSTRAINT transportservice_serviceTitle_exists IF NOT EXISTS
FOR (n:`TransportService`) REQUIRE n.`serviceTitle` IS NOT NULL;  // Enterprise
CREATE CONSTRAINT transportservice_serviceTitle_type IF NOT EXISTS
FOR (n:`TransportService`) REQUIRE n.`serviceTitle` IS :: STRING;  // Enterprise

// ---- Transporter ---------------------------------------------------------
CREATE CONSTRAINT transporter_id_unique IF NOT EXISTS
FOR (n:`Transporter`) REQUIRE n.`id` IS UNIQUE;  // NODE KEY on Enterprise

