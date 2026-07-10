"""neomodel OGM classes generated from hulubul.

DO NOT EDIT — regenerate with `make neomodel`.
Value objects (no identifier) are modelled as StructuredNodes reached by a
relationship: neomodel has no inlining.
"""
from neomodel import (
    StructuredNode,
    StringProperty, IntegerProperty, FloatProperty, BooleanProperty,
    DateProperty, DateTimeProperty, ArrayProperty,
    RelationshipTo, ZeroOrMore, ZeroOrOne, OneOrMore, One,
)


class Address(StructuredNode):
    """A precise, pin-level postal address."""
    withinArea = RelationshipTo('Area', 'WITHIN_AREA', cardinality=One)
    number = StringProperty(required=True)
    street = StringProperty(required=True)
    postCode = StringProperty(required=True)
    id = StringProperty(unique_index=True, required=True)
    comment = StringProperty()
    hasCoordinates = RelationshipTo('GeoCoordinates', 'HAS_COORDINATES', cardinality=ZeroOrOne)


class Agent(StructuredNode):
    """An enduring party — a person or an organisation — that participates in Hulubul. Holds stable identity, communication channels, an optional main location, and may publish a standing transport service and play episodic roles."""
    id = StringProperty(unique_index=True, required=True)
    name = StringProperty(required=True)
    description = StringProperty()
    identifier = StringProperty(required=True)
    hasContactPoint = RelationshipTo('Channel', 'HAS_CONTACT_POINT', cardinality=ZeroOrMore)
    hasMainContactPoint = RelationshipTo('Channel', 'HAS_MAIN_CONTACT_POINT', cardinality=ZeroOrOne)
    hasMainLocation = RelationshipTo('Address', 'HAS_MAIN_LOCATION', cardinality=ZeroOrOne)
    providesService = RelationshipTo('TransportService', 'PROVIDES_SERVICE', cardinality=ZeroOrOne)


class Area(StructuredNode):
    """A coarse administrative or geographic unit (locality, county, state, country) forming a nested containment hierarchy. Transporter service offers and matching operate on Area; exact pickup/delivery use Address."""
    withinArea = RelationshipTo('Area', 'WITHIN_AREA', cardinality=ZeroOrOne)
    locality = StringProperty()
    county = StringProperty()
    country = StringProperty()
    state = StringProperty()
    id = StringProperty(unique_index=True, required=True)
    comment = StringProperty()
    hasCoordinates = RelationshipTo('GeoCoordinates', 'HAS_COORDINATES', cardinality=ZeroOrOne)


class Channel(StructuredNode):
    """A communication channel bound to a single agent — the endpoint through which the agent is reached and, when validated, authenticated."""
    id = StringProperty(unique_index=True, required=True)
    description = StringProperty()
    alias = StringProperty()
    systemID = StringProperty(required=True)
    email = StringProperty()
    telephone = StringProperty()
    hasMedium = StringProperty(choices=(('GSM', 'GSM'), ('WhatsApp', 'WhatsApp'), ('Telegram', 'Telegram'), ('Viber', 'Viber'), ('email', 'email'),), required=True)
    validationStatus = StringProperty(choices=(('valid', 'valid'), ('invalid', 'invalid'), ('needsReview', 'needsReview'),), required=True)


class DeliveryRequest(StructuredNode):
    """A request to move one or more parcels from a pickup location to a drop-off location, carrying its participants, status and lifecycle timestamps."""
    id = StringProperty(unique_index=True, required=True)
    requestNote = ArrayProperty(StringProperty())
    preferredPeriod = StringProperty()
    created = DateTimeProperty(required=True)
    updated = DateTimeProperty(required=True)
    closed = DateTimeProperty()
    hasSender = RelationshipTo('Sender', 'HAS_SENDER', cardinality=One)
    hasReceiver = RelationshipTo('Receiver', 'HAS_RECEIVER', cardinality=One)
    hasTransporter = RelationshipTo('Transporter', 'HAS_TRANSPORTER', cardinality=ZeroOrOne)
    hasStatus = StringProperty(choices=(('new', 'new'), ('needsClarification', 'needsClarification'), ('complete', 'complete'), ('optionsProposed', 'optionsProposed'), ('waitingResponse', 'waitingResponse'), ('accepted', 'accepted'), ('rejected', 'rejected'), ('pickUpPlanned', 'pickUpPlanned'), ('pickedUp', 'pickedUp'), ('delivered', 'delivered'), ('cancelled', 'cancelled'),), required=True)
    hasDeliveryItem = RelationshipTo('Parcel', 'HAS_DELIVERY_ITEM', cardinality=OneOrMore)
    hasPickUpLocation = RelationshipTo('SpatialObject', 'HAS_PICK_UP_LOCATION', cardinality=One)
    hasDropOffLocation = RelationshipTo('SpatialObject', 'HAS_DROP_OFF_LOCATION', cardinality=One)
    hasAltDropOffLocation = RelationshipTo('SpatialObject', 'HAS_ALT_DROP_OFF_LOCATION', cardinality=ZeroOrOne)


class Feedback(StructuredNode):
    """A reified rating and/or comment left by one participation about another, optionally scoped to a delivery request."""
    id = StringProperty(unique_index=True, required=True)
    rating = IntegerProperty()
    comment = StringProperty()
    fromProvider = RelationshipTo('AgentInRole', 'FROM_PROVIDER', cardinality=One)
    toRecipient = RelationshipTo('AgentInRole', 'TO_RECIPIENT', cardinality=One)
    aboutRequest = RelationshipTo('DeliveryRequest', 'ABOUT_REQUEST', cardinality=ZeroOrOne)


class GeoCoordinates(StructuredNode):
    """A WGS84 latitude/longitude point — the geometry attached to a spatial object (GeoSPARQL geo:Geometry analogue). Composed value object, inlined (no id) rather than a node."""
    latitude = FloatProperty(required=True)
    longitude = FloatProperty(required=True)


class Parcel(StructuredNode):
    """A physical item to be delivered as part of a request."""
    id = StringProperty(unique_index=True, required=True)
    declaredContent = StringProperty(required=True)
    photoURL = ArrayProperty(StringProperty())
    weightKg = FloatProperty()
    dimensions = StringProperty()
    hasAltReceiver = RelationshipTo('Receiver', 'HAS_ALT_RECEIVER', cardinality=ZeroOrOne)


class Place(StructuredNode):
    """A named, typed point/place of interest (landmark, depot, pickup point) sitting within an Area. Distinct from coarse Area and precise Address."""
    withinArea = RelationshipTo('Area', 'WITHIN_AREA', cardinality=ZeroOrOne)
    name = StringProperty()
    hasIdentifier = StringProperty(required=True)
    hasType = StringProperty(required=True)
    id = StringProperty(unique_index=True, required=True)
    comment = StringProperty()
    hasCoordinates = RelationshipTo('GeoCoordinates', 'HAS_COORDINATES', cardinality=ZeroOrOne)


class Receiver(StructuredNode):
    """The role of the agent intended to take delivery of the parcel(s)."""
    deliveryNote = StringProperty()
    id = StringProperty(unique_index=True, required=True)
    playedBy = RelationshipTo('Agent', 'PLAYED_BY', cardinality=One)
    hasAltContactPointInRole = RelationshipTo('Channel', 'HAS_ALT_CONTACT_POINT_IN_ROLE', cardinality=ZeroOrOne)


class Sender(StructuredNode):
    """The role of the agent that initiates a delivery request and hands over the parcel(s). The sender also names the receiver."""
    id = StringProperty(unique_index=True, required=True)
    playedBy = RelationshipTo('Agent', 'PLAYED_BY', cardinality=One)
    hasAltContactPointInRole = RelationshipTo('Channel', 'HAS_ALT_CONTACT_POINT_IN_ROLE', cardinality=ZeroOrOne)


class ServiceOffer(StructuredNode):
    """A served area paired with an orientative frequency. The same shape serves both base and destination offers; direction is given by which association (hasBaseArea vs hasDestinationArea) it sits under, not by a flag. Given an id (graph node) because it carries an outgoing edge to Area."""
    id = StringProperty(unique_index=True, required=True)
    description = StringProperty(required=True)
    withinArea = RelationshipTo('Area', 'WITHIN_AREA', cardinality=One)
    withFrequency = StringProperty(choices=(('daily', 'daily'), ('weekly', 'weekly'), ('biweekly', 'biweekly'), ('fortnightly', 'fortnightly'), ('monthly', 'monthly'),), required=True)


class TransportService(StructuredNode):
    """A standing, request-agnostic offering published by a transporter agent, declaring service types and its base and destination service areas."""
    id = StringProperty(unique_index=True, required=True)
    description = StringProperty(required=True)
    serviceTitle = StringProperty(required=True)
    serviceType = ArrayProperty(StringProperty(choices=(('peopleTransport', 'peopleTransport'), ('parcelTransport', 'parcelTransport'),)), required=True)
    hasBaseArea = RelationshipTo('ServiceOffer', 'HAS_BASE_AREA', cardinality=OneOrMore)
    hasDestinationArea = RelationshipTo('ServiceOffer', 'HAS_DESTINATION_AREA', cardinality=OneOrMore)


class Transporter(StructuredNode):
    """The role of the agent that carries the parcel(s) for a delivery request."""
    id = StringProperty(unique_index=True, required=True)
    playedBy = RelationshipTo('Agent', 'PLAYED_BY', cardinality=One)
    hasAltContactPointInRole = RelationshipTo('Channel', 'HAS_ALT_CONTACT_POINT_IN_ROLE', cardinality=ZeroOrOne)



