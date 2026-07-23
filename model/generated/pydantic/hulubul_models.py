from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
)

metamodel_version = "1.11.0"
version = "None"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'hlb',
     'default_range': 'string',
     'description': 'Umbrella schema for the Hulubul V1 conceptual model — a '
                    'parcel-request intermediation service between Moldova, the '
                    'diaspora and international destinations. Imports the six '
                    'domain modules (spatial, channel, agent, service, request, '
                    'feedback) over the shared common base. Faithful to the five '
                    'source Enterprise Architect diagrams (2026-07-10); flagged '
                    'transcription artifacts are resolved to their plausible '
                    'reading with an inline note. Intended targets: Neo4j (via '
                    'linkml-store) and Pydantic.',
     'id': 'http://meaningfy.ws/ontology/hulubul/hulubul',
     'imports': ['hulubul_common',
                 'hulubul_spatial',
                 'hulubul_channel',
                 'hulubul_agent',
                 'hulubul_service',
                 'hulubul_request',
                 'hulubul_feedback'],
     'license': 'https://creativecommons.org/licenses/by/4.0/',
     'name': 'hulubul',
     'prefixes': {'hlb': {'prefix_prefix': 'hlb',
                          'prefix_reference': 'http://meaningfy.ws/ontology/hulubul/'}},
     'source_file': 'model/linkml/hulubul.yaml',
     'title': 'Hulubul V1 Conceptual Model'} )

class Medium(str, Enum):
    """
    The medium/platform of a communication channel.
    """
    GSM = "GSM"
    """
    Mobile phone / SMS / voice.
    """
    WhatsApp = "WhatsApp"
    """
    WhatsApp messaging.
    """
    Telegram = "Telegram"
    """
    Telegram messaging.
    """
    Viber = "Viber"
    """
    Viber messaging.
    """
    email = "email"
    """
    Email.
    """


class ChannelValidationStatus(str, Enum):
    """
    Whether control of a channel has been verified.
    """
    valid = "valid"
    """
    Control verified; usable as a trusted login.
    """
    invalid = "invalid"
    """
    Verification failed or channel unreachable.
    """
    needsReview = "needsReview"
    """
    Not yet verified; contact-only until validated.
    """


class ServiceType(str, Enum):
    """
    What a transport service carries.
    """
    peopleTransport = "peopleTransport"
    """
    Carries people.
    """
    parcelTransport = "parcelTransport"
    """
    Carries parcels.
    """


class Frequency(str, Enum):
    """
    Orientative coarse human-coordination label for how often a transporter serves an area — not a timetable/RRULE.
    """
    daily = "daily"
    """
    About once a day.
    """
    weekly = "weekly"
    """
    About once a week.
    """
    biweekly = "biweekly"
    """
    Presumed about twice a week (fortnightly covers every-two-weeks). Ambiguous in the source — confirm; twiceWeekly would disambiguate.
    """
    fortnightly = "fortnightly"
    """
    About once every two weeks.
    """
    monthly = "monthly"
    """
    About once a month.
    """


class RequestStatus(str, Enum):
    """
    Lifecycle states of a DeliveryRequest. Listed in intended progression order; access gates read these as reached-milestone, not numeric compare.
    """
    new = "new"
    """
    Just created; not yet triaged.
    """
    needsClarification = "needsClarification"
    """
    Awaiting more information from the sender.
    """
    complete = "complete"
    """
    Fully specified and ready to be matched.
    """
    optionsProposed = "optionsProposed"
    """
    One or more transporters have been proposed/recommended (recommended gate).
    """
    waitingResponse = "waitingResponse"
    """
    Awaiting a party's response to proposed options.
    """
    accepted = "accepted"
    """
    A transporter has committed; the job is on (accepted gate).
    """
    rejected = "rejected"
    """
    The proposed option(s) were declined.
    """
    pickUpPlanned = "pickUpPlanned"
    """
    Pickup has been scheduled.
    """
    pickedUp = "pickedUp"
    """
    Parcel(s) collected.
    """
    delivered = "delivered"
    """
    Parcel(s) delivered.
    """
    cancelled = "cancelled"
    """
    Request cancelled.
    """



class SpatialObject(ConfiguredBaseModel):
    """
    Root of the spatial hierarchy (aligned to geo:SpatialObject). Anything with spatial identity that may carry a geometry.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'aliases': ['Spatial Thing', 'Location'],
         'class_uri': 'hlb:SpatialObject',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/spatial',
         'slot_usage': {'comment': {'name': 'comment', 'required': False}}})

    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    comment: str | None = Field(default=None, description="""Free-text remark or annotation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject', 'Feedback'], 'slot_uri': 'hlb:comment'} })
    hasCoordinates: GeoCoordinates | None = Field(default=None, description="""The point geometry of this spatial object.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject'], 'slot_uri': 'hlb:hasCoordinates'} })


class Address(SpatialObject):
    """
    A precise, pin-level postal address.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['Postal Address', 'Street Address'],
         'class_uri': 'hlb:Address',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/spatial',
         'slot_usage': {'withinArea': {'name': 'withinArea', 'required': True}}})

    withinArea: str = Field(default=..., description="""The area this object sits within.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Address', 'Area', 'Place', 'ServiceOffer'],
         'slot_uri': 'hlb:withinArea'} })
    number: str = Field(default=..., description="""House/building number.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Address'], 'slot_uri': 'hlb:number'} })
    street: str = Field(default=..., description="""Street name.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Address'], 'slot_uri': 'hlb:street'} })
    postCode: str = Field(default=..., description="""Postal code.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Address'], 'slot_uri': 'hlb:postCode'} })
    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    comment: str | None = Field(default=None, description="""Free-text remark or annotation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject', 'Feedback'], 'slot_uri': 'hlb:comment'} })
    hasCoordinates: GeoCoordinates | None = Field(default=None, description="""The point geometry of this spatial object.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject'], 'slot_uri': 'hlb:hasCoordinates'} })


class Area(SpatialObject):
    """
    A coarse administrative or geographic unit (locality, county, state, country) forming a nested containment hierarchy. Transporter service offers and matching operate on Area; exact pickup/delivery use Address.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['Region', 'Locality', 'Administrative Area', 'Zone'],
         'class_uri': 'hlb:Area',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/spatial',
         'slot_usage': {'withinArea': {'multivalued': False,
                                       'name': 'withinArea',
                                       'required': False}}})

    withinArea: str | None = Field(default=None, description="""The area this object sits within.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Address', 'Area', 'Place', 'ServiceOffer'],
         'slot_uri': 'hlb:withinArea'} })
    locality: str | None = Field(default=None, description="""Town/city/locality name.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Area'], 'slot_uri': 'hlb:locality'} })
    county: str | None = Field(default=None, description="""County/district (raion).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Area'], 'slot_uri': 'hlb:county'} })
    country: str | None = Field(default=None, description="""Country name.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Area'], 'slot_uri': 'hlb:country'} })
    state: str | None = Field(default=None, description="""State/region within country.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Area'], 'slot_uri': 'hlb:state'} })
    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    comment: str | None = Field(default=None, description="""Free-text remark or annotation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject', 'Feedback'], 'slot_uri': 'hlb:comment'} })
    hasCoordinates: GeoCoordinates | None = Field(default=None, description="""The point geometry of this spatial object.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject'], 'slot_uri': 'hlb:hasCoordinates'} })


class Place(SpatialObject):
    """
    A named, typed point/place of interest (landmark, depot, pickup point) sitting within an Area. Distinct from coarse Area and precise Address.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['Named Place', 'Point of Interest', 'Landmark'],
         'class_uri': 'hlb:Place',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/spatial',
         'slot_usage': {'withinArea': {'name': 'withinArea', 'required': False}}})

    withinArea: str | None = Field(default=None, description="""The area this object sits within.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Address', 'Area', 'Place', 'ServiceOffer'],
         'slot_uri': 'hlb:withinArea'} })
    name: str | None = Field(default=None, description="""Human-readable name of the place.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Place', 'Agent'], 'slot_uri': 'hlb:name'} })
    hasIdentifier: str = Field(default=..., description="""Identifier of the place (e.g. gazetteer id).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Place'], 'slot_uri': 'hlb:hasIdentifier'} })
    hasType: str = Field(default=..., description="""Type of the place (e.g. depot, landmark, pickup point).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Place'], 'slot_uri': 'hlb:hasType'} })
    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    comment: str | None = Field(default=None, description="""Free-text remark or annotation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject', 'Feedback'], 'slot_uri': 'hlb:comment'} })
    hasCoordinates: GeoCoordinates | None = Field(default=None, description="""The point geometry of this spatial object.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject'], 'slot_uri': 'hlb:hasCoordinates'} })


class GeoCoordinates(ConfiguredBaseModel):
    """
    A WGS84 latitude/longitude point — the geometry attached to a spatial object (GeoSPARQL geo:Geometry analogue). Composed value object, inlined (no id) rather than a node.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['Coordinates', 'Point', 'Geometry', 'LatLong'],
         'class_uri': 'hlb:GeoCoordinates',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/spatial'})

    latitude: float = Field(default=..., description="""WGS84 latitude.""", json_schema_extra = { "linkml_meta": {'domain_of': ['GeoCoordinates'], 'slot_uri': 'hlb:latitude'} })
    longitude: float = Field(default=..., description="""WGS84 longitude.""", json_schema_extra = { "linkml_meta": {'domain_of': ['GeoCoordinates'], 'slot_uri': 'hlb:longitude'} })


class Channel(ConfiguredBaseModel):
    """
    A communication channel bound to a single agent — the endpoint through which the agent is reached and, when validated, authenticated.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['ContactPoint', 'Contact Channel', 'Account', 'Principal'],
         'class_uri': 'hlb:Channel',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/channel'})

    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    description: str | None = Field(default=None, description="""Free-text description.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Channel', 'Agent', 'TransportService', 'ServiceOffer'],
         'slot_uri': 'hlb:description'} })
    alias: str | None = Field(default=None, description="""Human label for the channel (e.g. \"mum's WhatsApp\").""", json_schema_extra = { "linkml_meta": {'domain_of': ['Channel'], 'slot_uri': 'hlb:alias'} })
    systemID: str = Field(default=..., description="""Provider/platform-issued identifier (e.g. Telegram chat/user id).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Channel'], 'slot_uri': 'hlb:systemID'} })
    email: str | None = Field(default=None, description="""Email address, when the medium is email.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Channel'], 'slot_uri': 'hlb:email'} })
    telephone: str | None = Field(default=None, description="""Phone number, when the medium is phone-based.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Channel'], 'slot_uri': 'hlb:telephone'} })
    hasMedium: Medium = Field(default=..., description="""The medium/platform of this channel.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Channel'], 'slot_uri': 'hlb:hasMedium'} })
    validationStatus: ChannelValidationStatus = Field(default=..., description="""Whether control of the channel has been verified.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Channel'], 'slot_uri': 'hlb:validationStatus'} })


class Agent(ConfiguredBaseModel):
    """
    An enduring party — a person or an organisation — that participates in Hulubul. Holds stable identity, communication channels, an optional main location, and may publish a standing transport service and play episodic roles.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['Party', 'Actor'],
         'class_uri': 'hlb:Agent',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/agent',
         'slot_usage': {'name': {'name': 'name', 'required': True}}})

    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    name: str = Field(default=..., description="""Human-readable name.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Place', 'Agent'], 'slot_uri': 'hlb:name'} })
    description: str | None = Field(default=None, description="""Free-text description.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Channel', 'Agent', 'TransportService', 'ServiceOffer'],
         'slot_uri': 'hlb:description'} })
    identifier: str = Field(default=..., description="""Stable unique business identifier of the agent within Hulubul.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Agent'], 'slot_uri': 'hlb:identifier'} })
    hasContactPoint: list[str] | None = Field(default=None, description="""Communication channels through which the agent can be reached and, when validated, authenticated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Agent'], 'slot_uri': 'hlb:hasContactPoint'} })
    hasMainContactPoint: str | None = Field(default=None, description="""The agent's primary/default channel; also the trusted login channel.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Agent'], 'slot_uri': 'hlb:hasMainContactPoint'} })
    hasMainLocation: str | None = Field(default=None, description="""The agent's principal location.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Agent'], 'slot_uri': 'hlb:hasMainLocation'} })
    providesService: str | None = Field(default=None, description="""The standing, request-agnostic transport offering published by this agent (present only for transporters).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Agent'], 'slot_uri': 'hlb:providesService'} })


class AgentInRole(ConfiguredBaseModel):
    """
    The episodic, situation-dependent role an Agent plays within a specific interaction; a reified participation. Anti-rigid: the same Agent plays different roles across different requests.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'aliases': ['Participation', 'Role', 'RoleAssignment'],
         'class_uri': 'hlb:AgentInRole',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/agent'})

    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    playedBy: str = Field(default=..., description="""The enduring agent enacting this role.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AgentInRole'], 'slot_uri': 'hlb:playedBy'} })
    hasAltContactPointInRole: str | None = Field(default=None, description="""An alternative channel to use for this participation, overriding the agent's default.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AgentInRole'], 'slot_uri': 'hlb:hasAltContactPointInRole'} })


class Transporter(AgentInRole):
    """
    The role of the agent that carries the parcel(s) for a delivery request.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['Carrier', 'Courier'],
         'class_uri': 'hlb:Transporter',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/agent'})

    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    playedBy: str = Field(default=..., description="""The enduring agent enacting this role.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AgentInRole'], 'slot_uri': 'hlb:playedBy'} })
    hasAltContactPointInRole: str | None = Field(default=None, description="""An alternative channel to use for this participation, overriding the agent's default.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AgentInRole'], 'slot_uri': 'hlb:hasAltContactPointInRole'} })


class Sender(AgentInRole):
    """
    The role of the agent that initiates a delivery request and hands over the parcel(s). The sender also names the receiver.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['Consignor', 'Shipper'],
         'class_uri': 'hlb:Sender',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/agent'})

    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    playedBy: str = Field(default=..., description="""The enduring agent enacting this role.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AgentInRole'], 'slot_uri': 'hlb:playedBy'} })
    hasAltContactPointInRole: str | None = Field(default=None, description="""An alternative channel to use for this participation, overriding the agent's default.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AgentInRole'], 'slot_uri': 'hlb:hasAltContactPointInRole'} })


class Receiver(AgentInRole):
    """
    The role of the agent intended to take delivery of the parcel(s).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['Consignee', 'Recipient'],
         'class_uri': 'hlb:Receiver',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/agent'})

    deliveryNote: str | None = Field(default=None, description="""A note from or for the receiver regarding delivery (e.g. handover instructions).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Receiver'], 'slot_uri': 'hlb:deliveryNote'} })
    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    playedBy: str = Field(default=..., description="""The enduring agent enacting this role.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AgentInRole'], 'slot_uri': 'hlb:playedBy'} })
    hasAltContactPointInRole: str | None = Field(default=None, description="""An alternative channel to use for this participation, overriding the agent's default.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AgentInRole'], 'slot_uri': 'hlb:hasAltContactPointInRole'} })


class TransportService(ConfiguredBaseModel):
    """
    A standing, request-agnostic offering published by a transporter agent, declaring service types and its base and destination service areas.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['Transporter Profile', 'Service Offering', 'Offer Profile'],
         'class_uri': 'hlb:TransportService',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/service',
         'slot_usage': {'description': {'name': 'description', 'required': True}}})

    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    description: str = Field(default=..., description="""Free-text description.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Channel', 'Agent', 'TransportService', 'ServiceOffer'],
         'slot_uri': 'hlb:description'} })
    serviceTitle: str = Field(default=..., description="""Short title of the offering.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TransportService'], 'slot_uri': 'hlb:serviceTitle'} })
    serviceType: list[ServiceType] = Field(default=..., description="""What the service carries (people and/or parcels).""", json_schema_extra = { "linkml_meta": {'domain_of': ['TransportService'], 'slot_uri': 'hlb:serviceType'} })
    hasBaseArea: list[str] = Field(default=..., description="""Pickup footprint — areas (with frequency) where the transporter can collect.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TransportService'], 'slot_uri': 'hlb:hasBaseArea'} })
    hasDestinationArea: list[str] = Field(default=..., description="""Delivery reach — areas (with frequency) the transporter serves as destinations.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TransportService'], 'slot_uri': 'hlb:hasDestinationArea'} })


class ServiceOffer(ConfiguredBaseModel):
    """
    A served area paired with an orientative frequency. The same shape serves both base and destination offers; direction is given by which association (hasBaseArea vs hasDestinationArea) it sits under, not by a flag. Given an id (graph node) because it carries an outgoing edge to Area.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['Service Area Offer', 'Area Offer', 'ServiceLocationSchedule'],
         'class_uri': 'hlb:ServiceOffer',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/service',
         'slot_usage': {'description': {'name': 'description', 'required': True},
                        'withinArea': {'name': 'withinArea', 'required': True}}})

    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    description: str = Field(default=..., description="""Free-text description.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Channel', 'Agent', 'TransportService', 'ServiceOffer'],
         'slot_uri': 'hlb:description'} })
    withinArea: str = Field(default=..., description="""The area this object sits within.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Address', 'Area', 'Place', 'ServiceOffer'],
         'slot_uri': 'hlb:withinArea'} })
    withFrequency: Frequency = Field(default=..., description="""How often the transporter is in/through the area (orientative).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ServiceOffer'], 'slot_uri': 'hlb:withFrequency'} })


class DeliveryRequest(ConfiguredBaseModel):
    """
    A request to move one or more parcels from a pickup location to a drop-off location, carrying its participants, status and lifecycle timestamps.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['Transport Request', 'Shipment Request', 'ParcelRequest'],
         'class_uri': 'hlb:DeliveryRequest',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/request'})

    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    requestNote: list[str] | None = Field(default=None, description="""Free-text notes attached to the request.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DeliveryRequest'], 'slot_uri': 'hlb:requestNote'} })
    preferredPeriod: str | None = Field(default=None, description="""The requester's preferred timeframe (orientative, free text).""", json_schema_extra = { "linkml_meta": {'domain_of': ['DeliveryRequest'], 'slot_uri': 'hlb:preferredPeriod'} })
    created: datetime  = Field(default=..., description="""When the request was created.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DeliveryRequest'], 'slot_uri': 'hlb:created'} })
    updated: datetime  = Field(default=..., description="""When the request was last modified.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DeliveryRequest'], 'slot_uri': 'hlb:updated'} })
    closed: datetime | None = Field(default=None, description="""When the request was closed/terminated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DeliveryRequest'], 'slot_uri': 'hlb:closed'} })
    hasSender: str = Field(default=..., description="""The sender participation for this request.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DeliveryRequest'], 'slot_uri': 'hlb:hasSender'} })
    hasReceiver: str = Field(default=..., description="""The primary receiver participation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DeliveryRequest'], 'slot_uri': 'hlb:hasReceiver'} })
    hasTransporter: str | None = Field(default=None, description="""The assigned transporter participation, once one is selected.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DeliveryRequest'], 'slot_uri': 'hlb:hasTransporter'} })
    hasStatus: RequestStatus = Field(default=..., description="""Current lifecycle status.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DeliveryRequest'], 'slot_uri': 'hlb:hasStatus'} })
    hasDeliveryItem: list[str] = Field(default=..., description="""The parcel(s) to be delivered.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DeliveryRequest'], 'slot_uri': 'hlb:hasDeliveryItem'} })
    hasPickUpLocation: str = Field(default=..., description="""Where the parcel(s) are collected — an Address or a named Place.""", json_schema_extra = { "linkml_meta": {'any_of': [{'range': 'Address'}, {'range': 'Place'}],
         'domain_of': ['DeliveryRequest'],
         'slot_uri': 'hlb:hasPickUpLocation'} })
    hasDropOffLocation: str = Field(default=..., description="""Where the parcel(s) are delivered — an Address or a named Place.""", json_schema_extra = { "linkml_meta": {'any_of': [{'range': 'Address'}, {'range': 'Place'}],
         'domain_of': ['DeliveryRequest'],
         'slot_uri': 'hlb:hasDropOffLocation'} })
    hasAltDropOffLocation: str | None = Field(default=None, description="""An alternative drop-off location (Address or Place). Owner resolved to request-level per diagram 2 (a Receiver-level variant was drawn in diagram 3 — not modelled here).""", json_schema_extra = { "linkml_meta": {'any_of': [{'range': 'Address'}, {'range': 'Place'}],
         'domain_of': ['DeliveryRequest'],
         'slot_uri': 'hlb:hasAltDropOffLocation'} })


class Parcel(ConfiguredBaseModel):
    """
    A physical item to be delivered as part of a request.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['Package', 'Item', 'Shipment Item'],
         'class_uri': 'hlb:Parcel',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/request'})

    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    declaredContent: str = Field(default=..., description="""The sender's declared description of contents.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Parcel'], 'slot_uri': 'hlb:declaredContent'} })
    photoURL: list[str] | None = Field(default=None, description="""URLs of photos of the parcel.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Parcel'], 'slot_uri': 'hlb:photoURL'} })
    weightKg: float | None = Field(default=None, description="""Weight in kilograms.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Parcel'], 'slot_uri': 'hlb:weightKg'} })
    dimensions: str | None = Field(default=None, description="""Free-text dimensions (e.g. \"30x20x10 cm\").""", json_schema_extra = { "linkml_meta": {'domain_of': ['Parcel'], 'slot_uri': 'hlb:dimensions'} })
    hasAltReceiver: str | None = Field(default=None, description="""An alternative receiver for this specific parcel.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Parcel'], 'slot_uri': 'hlb:hasAltReceiver'} })


class Feedback(ConfiguredBaseModel):
    """
    A reified rating and/or comment left by one participation about another, optionally scoped to a delivery request.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'aliases': ['Rating', 'Review', 'Testimonial'],
         'class_uri': 'hlb:Feedback',
         'from_schema': 'http://meaningfy.ws/ontology/hulubul/feedback'})

    id: str = Field(default=..., description="""Graph node identity for this instance (distinct from any business identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject',
                       'Channel',
                       'Agent',
                       'AgentInRole',
                       'TransportService',
                       'ServiceOffer',
                       'DeliveryRequest',
                       'Parcel',
                       'Feedback']} })
    rating: int | None = Field(default=None, description="""Numeric score.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feedback'], 'slot_uri': 'hlb:rating'} })
    comment: str | None = Field(default=None, description="""Free-text remark.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SpatialObject', 'Feedback'], 'slot_uri': 'hlb:comment'} })
    fromProvider: str = Field(default=..., description="""The participation that authored the feedback.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feedback'], 'slot_uri': 'hlb:fromProvider'} })
    toRecipient: str = Field(default=..., description="""The participation the feedback is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feedback'], 'slot_uri': 'hlb:toRecipient'} })
    aboutRequest: str | None = Field(default=None, description="""The delivery request the feedback concerns.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feedback'], 'slot_uri': 'hlb:aboutRequest'} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
SpatialObject.model_rebuild()
Address.model_rebuild()
Area.model_rebuild()
Place.model_rebuild()
GeoCoordinates.model_rebuild()
Channel.model_rebuild()
Agent.model_rebuild()
AgentInRole.model_rebuild()
Transporter.model_rebuild()
Sender.model_rebuild()
Receiver.model_rebuild()
TransportService.model_rebuild()
ServiceOffer.model_rebuild()
DeliveryRequest.model_rebuild()
Parcel.model_rebuild()
Feedback.model_rebuild()
