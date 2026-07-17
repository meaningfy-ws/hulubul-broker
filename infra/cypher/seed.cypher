// Hulubul demo seed — deterministic, idempotent (every node/relationship MERGEd
// by graph id). Re-running is safe and yields the same fixture set.
//
// Model faithfulness: labels, relationship types and property names match
// model/linkml/*.yaml and the OGM at model/generated/neomodel/hulubul_ogm.py.
// GeoCoordinates is a value object (no identifier) and is inlined as
// latitude/longitude properties on its spatial object (per the linkml-store
// Neo4j mapping), not promoted to a node.
//
// Geography (Moldova ↔ diaspora): MD / RO / IT / DE.
// Covers RequestStatus values across 9 requests, 2 transporters with standing
// services, 2 senders, 2 receivers, parcels, and feedback.

// ============================================================================
// 1. Areas (nested containment: locality -> country via WITHIN_AREA)
// ============================================================================
MERGE (md:Area {id:'a-md'})          SET md.country='Moldova';
MERGE (ro:Area {id:'a-ro'})          SET ro.country='Romania';
MERGE (it:Area {id:'a-it'})          SET it.country='Italy';
MERGE (de:Area {id:'a-de'})          SET de.country='Germany';

MERGE (c:Area {id:'a-md-chisinau'}) SET c.locality='Chișinău', c.country='Moldova', c.latitude=47.0105, c.longitude=28.8638;
MERGE (b:Area {id:'a-md-balti'})    SET b.locality='Bălți', b.county='Bălți', b.country='Moldova', b.latitude=47.7648, b.longitude=27.9302;
MERGE (i:Area {id:'a-ro-iasi'})     SET i.locality='Iași', i.county='Iași', i.country='Romania', i.latitude=47.1585, i.longitude=27.6014;
MERGE (u:Area {id:'a-ro-bucuresti'}) SET u.locality='București', u.country='Romania', u.latitude=44.4268, u.longitude=26.1025;
MERGE (r:Area {id:'a-it-rome'})     SET r.locality='Roma', r.country='Italy', r.latitude=41.9028, r.longitude=12.4964;
MERGE (m:Area {id:'a-it-milan'})    SET m.locality='Milano', m.country='Italy', m.latitude=45.4642, m.longitude=9.1900;
MERGE (n:Area {id:'a-de-munich'})   SET n.locality='München', n.country='Germany', n.latitude=48.1351, n.longitude=11.5820;

MATCH (parent:Area {id:'a-md'}), (child:Area {id:'a-md-chisinau'}) MERGE (child)-[:WITHIN_AREA]->(parent);
MATCH (parent:Area {id:'a-md'}), (child:Area {id:'a-md-balti'})    MERGE (child)-[:WITHIN_AREA]->(parent);
MATCH (parent:Area {id:'a-ro'}), (child:Area {id:'a-ro-iasi'})     MERGE (child)-[:WITHIN_AREA]->(parent);
MATCH (parent:Area {id:'a-ro'}), (child:Area {id:'a-ro-bucuresti'}) MERGE (child)-[:WITHIN_AREA]->(parent);
MATCH (parent:Area {id:'a-it'}), (child:Area {id:'a-it-rome'})     MERGE (child)-[:WITHIN_AREA]->(parent);
MATCH (parent:Area {id:'a-it'}), (child:Area {id:'a-it-milan'})    MERGE (child)-[:WITHIN_AREA]->(parent);
MATCH (parent:Area {id:'a-de'}), (child:Area {id:'a-de-munich'})   MERGE (child)-[:WITHIN_AREA]->(parent);

// ============================================================================
// 2. Addresses (precise, pin-level) + named Places
// ============================================================================
MERGE (a:Address {id:'addr-md-chisinau-1'}) SET a.number='31', a.street='Ștefan cel Mare', a.postCode='MD-2001', a.latitude=47.0245, a.longitude=28.8316;
MERGE (a:Address {id:'addr-md-balti-1'})    SET a.number='7',  a.street='Pietrosul',       a.postCode='3100',  a.latitude=47.7700, a.longitude=27.9100;
MERGE (a:Address {id:'addr-ro-iasi-1'})     SET a.number='12', a.street='Copou',            a.postCode='700115',a.latitude=47.1700, a.longitude=27.5700;
MERGE (a:Address {id:'addr-de-munich-1'})   SET a.number='5',  a.street='Hauptstraße',      a.postCode='80331', a.latitude=48.1370, a.longitude=11.5750;
MERGE (a:Address {id:'addr-it-rome-1'})     SET a.number='22', a.street='Via Roma',         a.postCode='00184', a.latitude=41.8950, a.longitude=12.4850;

MATCH (a:Address {id:'addr-md-chisinau-1'}), (ar:Area {id:'a-md-chisinau'}) MERGE (a)-[:WITHIN_AREA]->(ar);
MATCH (a:Address {id:'addr-md-balti-1'}),    (ar:Area {id:'a-md-balti'})    MERGE (a)-[:WITHIN_AREA]->(ar);
MATCH (a:Address {id:'addr-ro-iasi-1'}),     (ar:Area {id:'a-ro-iasi'})     MERGE (a)-[:WITHIN_AREA]->(ar);
MATCH (a:Address {id:'addr-de-munich-1'}),   (ar:Area {id:'a-de-munich'})   MERGE (a)-[:WITHIN_AREA]->(ar);
MATCH (a:Address {id:'addr-it-rome-1'}),     (ar:Area {id:'a-it-rome'})     MERGE (a)-[:WITHIN_AREA]->(ar);

MERGE (p:Place {id:'pl-depot-chisinau'}) SET p.name='Central Depot Chișinău', p.hasIdentifier='depot-cmd', p.hasType='depot', p.latitude=47.0300, p.longitude=28.8400;
MERGE (p:Place {id:'pl-pickup-munich'})  SET p.name='München Hauptbahnhof pickup', p.hasIdentifier='poi-muc-hbf', p.hasType='pickup point', p.latitude=48.1402, p.longitude=11.5586;
MATCH (p:Place {id:'pl-depot-chisinau'}), (ar:Area {id:'a-md-chisinau'}) MERGE (p)-[:WITHIN_AREA]->(ar);
MATCH (p:Place {id:'pl-pickup-munich'}),  (ar:Area {id:'a-de-munich'})   MERGE (p)-[:WITHIN_AREA]->(ar);

// ============================================================================
// 3. Channels (communication endpoints / credentials)
// ============================================================================
MERGE (c:Channel {id:'ch-vas-tg'}) SET c.alias='Vasile Telegram', c.systemID='tg:555111', c.hasMedium='Telegram',       c.validationStatus='valid';
MERGE (c:Channel {id:'ch-vas-wa'}) SET c.alias='Vasile WhatsApp', c.systemID='wa:401234567', c.hasMedium='WhatsApp',     c.validationStatus='valid';
MERGE (c:Channel {id:'ch-vas-em'}) SET c.alias='Vasile email',   c.systemID='vasile@example.md', c.email='vasile@example.md', c.hasMedium='email', c.validationStatus='valid';
MERGE (c:Channel {id:'ch-dia-tg'}) SET c.alias='Diaspora Telegram', c.systemID='tg:555222', c.hasMedium='Telegram',     c.validationStatus='needsReview';
MERGE (c:Channel {id:'ch-dia-wa'}) SET c.alias='Diaspora WhatsApp', c.systemID='wa:407654321', c.hasMedium='WhatsApp',   c.validationStatus='valid';
MERGE (c:Channel {id:'ch-eln-wa'}) SET c.alias='Elena WhatsApp', c.systemID='wa:491701234',  c.hasMedium='WhatsApp',     c.validationStatus='valid';
MERGE (c:Channel {id:'ch-and-tg'}) SET c.alias='Andrei Telegram',c.systemID='tg:555333',    c.hasMedium='Telegram',     c.validationStatus='valid';
MERGE (c:Channel {id:'ch-and-wa'}) SET c.alias='Andrei WhatsApp',c.systemID='wa:392709999', c.hasMedium='WhatsApp',     c.validationStatus='needsReview';
MERGE (c:Channel {id:'ch-mar-wa'}) SET c.alias='Maria WhatsApp', c.systemID='wa:373612345', c.hasMedium='WhatsApp',     c.validationStatus='needsReview';
MERGE (c:Channel {id:'ch-ion-gsm'}) SET c.alias='Ion GSM',       c.systemID='tel:+37369123456', c.telephone='+37369123456', c.hasMedium='GSM', c.validationStatus='valid';

// ============================================================================
// 4. Agents (enduring parties) + channels + main location + service
// ============================================================================
MERGE (a:Agent {id:'ag-transporter-01'}) SET a.name='Vasile Transport',  a.identifier='VAS-MD-001', a.description='Moldova-based transporter, runs MD↔RO parcels weekly.';
MERGE (a:Agent {id:'ag-transporter-02'}) SET a.name='Diaspora Express',  a.identifier='DIA-RO-002', a.description='Romania-based transporter, diaspora routes to IT and DE.';
MERGE (a:Agent {id:'ag-sender-01'})       SET a.name='Elena (sender)',    a.identifier='ELN-S-101',  a.description='Sender in München, sends parcels home to Chișinău.';
MERGE (a:Agent {id:'ag-sender-02'})       SET a.name='Andrei (sender)',   a.identifier='AND-S-102',  a.description='Sender in Roma, sends parcels to Bălți.';
MERGE (a:Agent {id:'ag-receiver-01'})     SET a.name='Maria (receiver)',  a.identifier='MAR-R-201',  a.description='Receiver in Chișinău.';
MERGE (a:Agent {id:'ag-receiver-02'})     SET a.name='Ion (receiver)',    a.identifier='ION-R-202',  a.description='Receiver in Bălți.';

// Agent -> Channels (contact points + main contact point).
MATCH (a:Agent {id:'ag-transporter-01'}), (c:Channel {id:'ch-vas-tg'}) MERGE (a)-[:HAS_MAIN_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-transporter-01'}), (c:Channel {id:'ch-vas-tg'}) MERGE (a)-[:HAS_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-transporter-01'}), (c:Channel {id:'ch-vas-wa'}) MERGE (a)-[:HAS_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-transporter-01'}), (c:Channel {id:'ch-vas-em'}) MERGE (a)-[:HAS_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-transporter-02'}), (c:Channel {id:'ch-dia-wa'}) MERGE (a)-[:HAS_MAIN_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-transporter-02'}), (c:Channel {id:'ch-dia-wa'}) MERGE (a)-[:HAS_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-transporter-02'}), (c:Channel {id:'ch-dia-tg'}) MERGE (a)-[:HAS_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-sender-01'}),       (c:Channel {id:'ch-eln-wa'}) MERGE (a)-[:HAS_MAIN_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-sender-01'}),       (c:Channel {id:'ch-eln-wa'}) MERGE (a)-[:HAS_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-sender-02'}),       (c:Channel {id:'ch-and-tg'}) MERGE (a)-[:HAS_MAIN_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-sender-02'}),       (c:Channel {id:'ch-and-tg'}) MERGE (a)-[:HAS_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-sender-02'}),       (c:Channel {id:'ch-and-wa'}) MERGE (a)-[:HAS_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-receiver-01'}),     (c:Channel {id:'ch-mar-wa'}) MERGE (a)-[:HAS_MAIN_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-receiver-01'}),     (c:Channel {id:'ch-mar-wa'}) MERGE (a)-[:HAS_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-receiver-02'}),     (c:Channel {id:'ch-ion-gsm'}) MERGE (a)-[:HAS_MAIN_CONTACT_POINT]->(c);
MATCH (a:Agent {id:'ag-receiver-02'}),     (c:Channel {id:'ch-ion-gsm'}) MERGE (a)-[:HAS_CONTACT_POINT]->(c);

// Agent -> main location (Address).
MATCH (a:Agent {id:'ag-transporter-01'}), (loc:Address {id:'addr-md-chisinau-1'}) MERGE (a)-[:HAS_MAIN_LOCATION]->(loc);
MATCH (a:Agent {id:'ag-transporter-02'}), (loc:Address {id:'addr-ro-iasi-1'})     MERGE (a)-[:HAS_MAIN_LOCATION]->(loc);
MATCH (a:Agent {id:'ag-sender-01'}),       (loc:Address {id:'addr-de-munich-1'})   MERGE (a)-[:HAS_MAIN_LOCATION]->(loc);
MATCH (a:Agent {id:'ag-sender-02'}),       (loc:Address {id:'addr-it-rome-1'})     MERGE (a)-[:HAS_MAIN_LOCATION]->(loc);
MATCH (a:Agent {id:'ag-receiver-01'}),     (loc:Address {id:'addr-md-chisinau-1'}) MERGE (a)-[:HAS_MAIN_LOCATION]->(loc);
MATCH (a:Agent {id:'ag-receiver-02'}),     (loc:Address {id:'addr-md-balti-1'})    MERGE (a)-[:HAS_MAIN_LOCATION]->(loc);

// ============================================================================
// 5. Transport services + service offers (standing capability layer)
//    TransportService -[:HAS_BASE_AREA|HAS_DESTINATION_AREA]-> ServiceOffer
//    ServiceOffer -[:WITHIN_AREA]-> Area ; Agent -[:PROVIDES_SERVICE]-> TransportService
//
//    Direction = diaspora -> home (DE/IT -> MD), matching the seeded requests:
//      Vasile  serves DE -> MD (and MD -> RO).
//      Diaspora serves IT, RO -> MD.
//    So Q3 (München -> Chișinău) resolves to Vasile; Roma -> Bălți to Diaspora.
// ============================================================================
// Vasile Transport — base/destination offers.
MERGE (so:ServiceOffer {id:'so-vas-pickup-de'}) SET so.description='Pickups in München, monthly.',   so.withFrequency='monthly';
MERGE (so:ServiceOffer {id:'so-vas-pickup-md'}) SET so.description='Pickups in Chișinău, weekly.',    so.withFrequency='weekly';
MERGE (so:ServiceOffer {id:'so-vas-drop-md'})   SET so.description='Drops in Chișinău, monthly.',     so.withFrequency='monthly';
MERGE (so:ServiceOffer {id:'so-vas-drop-ro'})   SET so.description='Drops in Iași, weekly.',          so.withFrequency='weekly';
// Diaspora Express — base/destination offers.
MERGE (so:ServiceOffer {id:'so-dia-pickup-it'}) SET so.description='Pickups in Roma, every two weeks.', so.withFrequency='fortnightly';
MERGE (so:ServiceOffer {id:'so-dia-pickup-ro'}) SET so.description='Pickups in Iași, twice a week.',   so.withFrequency='biweekly';
MERGE (so:ServiceOffer {id:'so-dia-drop-md-balti'})   SET so.description='Drops in Bălți, monthly.',      so.withFrequency='monthly';
MERGE (so:ServiceOffer {id:'so-dia-drop-md-chisinau'}) SET so.description='Drops in Chișinău, every two weeks.', so.withFrequency='fortnightly';

MATCH (so:ServiceOffer {id:'so-vas-pickup-de'}), (ar:Area {id:'a-de-munich'})   MERGE (so)-[:WITHIN_AREA]->(ar);
MATCH (so:ServiceOffer {id:'so-vas-pickup-md'}), (ar:Area {id:'a-md-chisinau'})  MERGE (so)-[:WITHIN_AREA]->(ar);
MATCH (so:ServiceOffer {id:'so-vas-drop-md'}),   (ar:Area {id:'a-md-chisinau'})  MERGE (so)-[:WITHIN_AREA]->(ar);
MATCH (so:ServiceOffer {id:'so-vas-drop-ro'}),   (ar:Area {id:'a-ro-iasi'})      MERGE (so)-[:WITHIN_AREA]->(ar);
MATCH (so:ServiceOffer {id:'so-dia-pickup-it'}),   (ar:Area {id:'a-it-rome'})    MERGE (so)-[:WITHIN_AREA]->(ar);
MATCH (so:ServiceOffer {id:'so-dia-pickup-ro'}),   (ar:Area {id:'a-ro-iasi'})    MERGE (so)-[:WITHIN_AREA]->(ar);
MATCH (so:ServiceOffer {id:'so-dia-drop-md-balti'}),   (ar:Area {id:'a-md-balti'})    MERGE (so)-[:WITHIN_AREA]->(ar);
MATCH (so:ServiceOffer {id:'so-dia-drop-md-chisinau'}), (ar:Area {id:'a-md-chisinau'}) MERGE (so)-[:WITHIN_AREA]->(ar);

MERGE (s:TransportService {id:'ts-vasile'})  SET s.serviceTitle='DE↔MD↔RO parcels',   s.description='Moldova transporter: diaspora pickups DE -> MD, plus MD -> RO.', s.serviceType=['parcelTransport'];
MERGE (s:TransportService {id:'ts-diaspora'}) SET s.serviceTitle='IT/RO↔MD diaspora', s.description='Diaspora routes: pickups IT/RO -> drops Moldova, parcels + people.', s.serviceType=['parcelTransport','peopleTransport'];

MATCH (s:TransportService {id:'ts-vasile'}), (so:ServiceOffer {id:'so-vas-pickup-de'}) MERGE (s)-[:HAS_BASE_AREA]->(so);
MATCH (s:TransportService {id:'ts-vasile'}), (so:ServiceOffer {id:'so-vas-pickup-md'}) MERGE (s)-[:HAS_BASE_AREA]->(so);
MATCH (s:TransportService {id:'ts-vasile'}), (so:ServiceOffer {id:'so-vas-drop-md'})   MERGE (s)-[:HAS_DESTINATION_AREA]->(so);
MATCH (s:TransportService {id:'ts-vasile'}), (so:ServiceOffer {id:'so-vas-drop-ro'})   MERGE (s)-[:HAS_DESTINATION_AREA]->(so);
MATCH (s:TransportService {id:'ts-diaspora'}), (so:ServiceOffer {id:'so-dia-pickup-it'})   MERGE (s)-[:HAS_BASE_AREA]->(so);
MATCH (s:TransportService {id:'ts-diaspora'}), (so:ServiceOffer {id:'so-dia-pickup-ro'})   MERGE (s)-[:HAS_BASE_AREA]->(so);
MATCH (s:TransportService {id:'ts-diaspora'}), (so:ServiceOffer {id:'so-dia-drop-md-balti'})   MERGE (s)-[:HAS_DESTINATION_AREA]->(so);
MATCH (s:TransportService {id:'ts-diaspora'}), (so:ServiceOffer {id:'so-dia-drop-md-chisinau'}) MERGE (s)-[:HAS_DESTINATION_AREA]->(so);

MATCH (a:Agent {id:'ag-transporter-01'}), (s:TransportService {id:'ts-vasile'})  MERGE (a)-[:PROVIDES_SERVICE]->(s);
MATCH (a:Agent {id:'ag-transporter-02'}), (s:TransportService {id:'ts-diaspora'}) MERGE (a)-[:PROVIDES_SERVICE]->(s);

// ============================================================================
// 6. Parcels
// ============================================================================
MERGE (p:Parcel {id:'p-001'})  SET p.declaredContent='Books',         p.weightKg=2.5, p.dimensions='30x20x10 cm';
MERGE (p:Parcel {id:'p-001b'}) SET p.declaredContent='Books vol.2',   p.weightKg=2.0, p.dimensions='30x20x10 cm';
MERGE (p:Parcel {id:'p-002'})  SET p.declaredContent='Electronics',   p.weightKg=1.2, p.dimensions='25x15x8 cm';
MERGE (p:Parcel {id:'p-003'})  SET p.declaredContent='Clothes',       p.weightKg=3.0, p.dimensions='40x30x20 cm';
MERGE (p:Parcel {id:'p-004'})  SET p.declaredContent='Documents',     p.weightKg=0.5, p.dimensions='A4 envelope';
MERGE (p:Parcel {id:'p-005'})  SET p.declaredContent='Medicines',     p.weightKg=0.8, p.dimensions='20x15x10 cm';
MERGE (p:Parcel {id:'p-006'})  SET p.declaredContent='Food package',  p.weightKg=4.0, p.dimensions='35x25x25 cm';
MERGE (p:Parcel {id:'p-007'})  SET p.declaredContent='Gifts',         p.weightKg=2.0, p.dimensions='30x25x15 cm';
MERGE (p:Parcel {id:'p-008'})  SET p.declaredContent='Spare parts',   p.weightKg=5.0, p.dimensions='40x30x20 cm';
MERGE (p:Parcel {id:'p-009'})  SET p.declaredContent='Toys',          p.weightKg=1.5, p.dimensions='30x20x15 cm';

// ============================================================================
// 7. Delivery requests (with role nodes + participants + locations)
//    Role nodes: :Sender / :Receiver / :Transporter  (AgentInRole subtypes)
//    Each role -[:PLAYED_BY]-> Agent ; DeliveryRequest -[:HAS_*]-> role/location/parcel
// ============================================================================
// req-001: delivered/closed, elena -> maria via vasile
MERGE (s:Sender {id:'s-001'});
MERGE (r:Receiver {id:'r-001'}) SET r.deliveryNote='Leave at the entrance, floor 2.';
MERGE (t:Transporter {id:'t-001'});
MERGE (req:DeliveryRequest {id:'req-001'})
  SET req.hasStatus='delivered',
      req.created=datetime('2026-06-10T09:00:00'),
      req.updated=datetime('2026-06-14T16:30:00'),
      req.closed=datetime('2026-06-14T16:30:00'),
      req.preferredPeriod='mid-June 2026',
      req.requestNote=['Handle with care.'];
MATCH (s:Sender {id:'s-001'}), (a:Agent {id:'ag-sender-01'})      MERGE (s)-[:PLAYED_BY]->(a);
MATCH (r:Receiver {id:'r-001'}), (a:Agent {id:'ag-receiver-01'})  MERGE (r)-[:PLAYED_BY]->(a);
MATCH (t:Transporter {id:'t-001'}), (a:Agent {id:'ag-transporter-01'}) MERGE (t)-[:PLAYED_BY]->(a);
MATCH (req:DeliveryRequest {id:'req-001'}), (s:Sender {id:'s-001'})        MERGE (req)-[:HAS_SENDER]->(s);
MATCH (req:DeliveryRequest {id:'req-001'}), (r:Receiver {id:'r-001'})      MERGE (req)-[:HAS_RECEIVER]->(r);
MATCH (req:DeliveryRequest {id:'req-001'}), (t:Transporter {id:'t-001'})   MERGE (req)-[:HAS_TRANSPORTER]->(t);
MATCH (req:DeliveryRequest {id:'req-001'}), (p:Parcel {id:'p-001'})        MERGE (req)-[:HAS_DELIVERY_ITEM]->(p);
MATCH (req:DeliveryRequest {id:'req-001'}), (p:Parcel {id:'p-001b'})       MERGE (req)-[:HAS_DELIVERY_ITEM]->(p);
MATCH (req:DeliveryRequest {id:'req-001'}), (loc:Address {id:'addr-de-munich-1'})  MERGE (req)-[:HAS_PICK_UP_LOCATION]->(loc);
MATCH (req:DeliveryRequest {id:'req-001'}), (loc:Address {id:'addr-md-chisinau-1'}) MERGE (req)-[:HAS_DROP_OFF_LOCATION]->(loc);

// req-002: accepted, andrei -> ion via diaspora
MERGE (s:Sender {id:'s-002'});
MERGE (r:Receiver {id:'r-002'});
MERGE (t:Transporter {id:'t-002'});
MERGE (req:DeliveryRequest {id:'req-002'})
  SET req.hasStatus='accepted',
      req.created=datetime('2026-07-01T11:00:00'),
      req.updated=datetime('2026-07-02T08:15:00'),
      req.preferredPeriod='early July 2026',
      req.requestNote=['Fragile electronics.'];
MATCH (s:Sender {id:'s-002'}), (a:Agent {id:'ag-sender-02'})       MERGE (s)-[:PLAYED_BY]->(a);
MATCH (r:Receiver {id:'r-002'}), (a:Agent {id:'ag-receiver-02'})   MERGE (r)-[:PLAYED_BY]->(a);
MATCH (t:Transporter {id:'t-002'}), (a:Agent {id:'ag-transporter-02'}) MERGE (t)-[:PLAYED_BY]->(a);
MATCH (req:DeliveryRequest {id:'req-002'}), (s:Sender {id:'s-002'})       MERGE (req)-[:HAS_SENDER]->(s);
MATCH (req:DeliveryRequest {id:'req-002'}), (r:Receiver {id:'r-002'})     MERGE (req)-[:HAS_RECEIVER]->(r);
MATCH (req:DeliveryRequest {id:'req-002'}), (t:Transporter {id:'t-002'})  MERGE (req)-[:HAS_TRANSPORTER]->(t);
MATCH (req:DeliveryRequest {id:'req-002'}), (p:Parcel {id:'p-002'})       MERGE (req)-[:HAS_DELIVERY_ITEM]->(p);
MATCH (req:DeliveryRequest {id:'req-002'}), (loc:Address {id:'addr-it-rome-1'})  MERGE (req)-[:HAS_PICK_UP_LOCATION]->(loc);
MATCH (req:DeliveryRequest {id:'req-002'}), (loc:Address {id:'addr-md-balti-1'}) MERGE (req)-[:HAS_DROP_OFF_LOCATION]->(loc);

// req-003: waitingResponse, elena -> maria via vasile
MERGE (s:Sender {id:'s-003'});
MERGE (r:Receiver {id:'r-003'});
MERGE (t:Transporter {id:'t-003'});
MERGE (req:DeliveryRequest {id:'req-003'})
  SET req.hasStatus='waitingResponse',
      req.created=datetime('2026-07-10T14:00:00'),
      req.updated=datetime('2026-07-11T09:30:00'),
      req.preferredPeriod='August 2026',
      req.requestNote=['Seasonal clothes.'];
MATCH (s:Sender {id:'s-003'}), (a:Agent {id:'ag-sender-01'})       MERGE (s)-[:PLAYED_BY]->(a);
MATCH (r:Receiver {id:'r-003'}), (a:Agent {id:'ag-receiver-01'})   MERGE (r)-[:PLAYED_BY]->(a);
MATCH (t:Transporter {id:'t-003'}), (a:Agent {id:'ag-transporter-01'}) MERGE (t)-[:PLAYED_BY]->(a);
MATCH (req:DeliveryRequest {id:'req-003'}), (s:Sender {id:'s-003'})       MERGE (req)-[:HAS_SENDER]->(s);
MATCH (req:DeliveryRequest {id:'req-003'}), (r:Receiver {id:'r-003'})     MERGE (req)-[:HAS_RECEIVER]->(r);
MATCH (req:DeliveryRequest {id:'req-003'}), (t:Transporter {id:'t-003'})  MERGE (req)-[:HAS_TRANSPORTER]->(t);
MATCH (req:DeliveryRequest {id:'req-003'}), (p:Parcel {id:'p-003'})       MERGE (req)-[:HAS_DELIVERY_ITEM]->(p);
MATCH (req:DeliveryRequest {id:'req-003'}), (loc:Address {id:'addr-de-munich-1'}) MERGE (req)-[:HAS_PICK_UP_LOCATION]->(loc);
MATCH (req:DeliveryRequest {id:'req-003'}), (loc:Place {id:'pl-depot-chisinau'})  MERGE (req)-[:HAS_DROP_OFF_LOCATION]->(loc);

// req-004: optionsProposed, andrei -> ion (no transporter assigned yet)
MERGE (s:Sender {id:'s-004'});
MERGE (r:Receiver {id:'r-004'});
MERGE (req:DeliveryRequest {id:'req-004'})
  SET req.hasStatus='optionsProposed',
      req.created=datetime('2026-07-12T10:00:00'),
      req.updated=datetime('2026-07-12T10:05:00'),
      req.preferredPeriod='July 2026',
      req.requestNote=['Documents only.'];
MATCH (s:Sender {id:'s-004'}), (a:Agent {id:'ag-sender-02'})      MERGE (s)-[:PLAYED_BY]->(a);
MATCH (r:Receiver {id:'r-004'}), (a:Agent {id:'ag-receiver-02'})  MERGE (r)-[:PLAYED_BY]->(a);
MATCH (req:DeliveryRequest {id:'req-004'}), (s:Sender {id:'s-004'})      MERGE (req)-[:HAS_SENDER]->(s);
MATCH (req:DeliveryRequest {id:'req-004'}), (r:Receiver {id:'r-004'})    MERGE (req)-[:HAS_RECEIVER]->(r);
MATCH (req:DeliveryRequest {id:'req-004'}), (p:Parcel {id:'p-004'})      MERGE (req)-[:HAS_DELIVERY_ITEM]->(p);
MATCH (req:DeliveryRequest {id:'req-004'}), (loc:Address {id:'addr-it-rome-1'})  MERGE (req)-[:HAS_PICK_UP_LOCATION]->(loc);
MATCH (req:DeliveryRequest {id:'req-004'}), (loc:Address {id:'addr-md-balti-1'}) MERGE (req)-[:HAS_DROP_OFF_LOCATION]->(loc);

// req-005: pickedUp, elena -> maria via vasile
MERGE (s:Sender {id:'s-005'});
MERGE (r:Receiver {id:'r-005'}) SET r.deliveryNote='Call before delivery.';
MERGE (t:Transporter {id:'t-004'});
MERGE (req:DeliveryRequest {id:'req-005'})
  SET req.hasStatus='pickedUp',
      req.created=datetime('2026-07-13T08:00:00'),
      req.updated=datetime('2026-07-13T18:00:00'),
      req.preferredPeriod='mid-July 2026',
      req.requestNote=['Medicines, keep upright.'];
MATCH (s:Sender {id:'s-005'}), (a:Agent {id:'ag-sender-01'})       MERGE (s)-[:PLAYED_BY]->(a);
MATCH (r:Receiver {id:'r-005'}), (a:Agent {id:'ag-receiver-01'})   MERGE (r)-[:PLAYED_BY]->(a);
MATCH (t:Transporter {id:'t-004'}), (a:Agent {id:'ag-transporter-01'}) MERGE (t)-[:PLAYED_BY]->(a);
MATCH (req:DeliveryRequest {id:'req-005'}), (s:Sender {id:'s-005'})       MERGE (req)-[:HAS_SENDER]->(s);
MATCH (req:DeliveryRequest {id:'req-005'}), (r:Receiver {id:'r-005'})     MERGE (req)-[:HAS_RECEIVER]->(r);
MATCH (req:DeliveryRequest {id:'req-005'}), (t:Transporter {id:'t-004'})  MERGE (req)-[:HAS_TRANSPORTER]->(t);
MATCH (req:DeliveryRequest {id:'req-005'}), (p:Parcel {id:'p-005'})       MERGE (req)-[:HAS_DELIVERY_ITEM]->(p);
MATCH (req:DeliveryRequest {id:'req-005'}), (loc:Address {id:'addr-de-munich-1'})  MERGE (req)-[:HAS_PICK_UP_LOCATION]->(loc);
MATCH (req:DeliveryRequest {id:'req-005'}), (loc:Address {id:'addr-md-chisinau-1'}) MERGE (req)-[:HAS_DROP_OFF_LOCATION]->(loc);

// req-006: complete (ready to match), andrei -> ion (no transporter)
MERGE (s:Sender {id:'s-006'});
MERGE (r:Receiver {id:'r-006'});
MERGE (req:DeliveryRequest {id:'req-006'})
  SET req.hasStatus='complete',
      req.created=datetime('2026-07-14T09:00:00'),
      req.updated=datetime('2026-07-14T09:00:00'),
      req.preferredPeriod='late July 2026';
MATCH (s:Sender {id:'s-006'}), (a:Agent {id:'ag-sender-02'})      MERGE (s)-[:PLAYED_BY]->(a);
MATCH (r:Receiver {id:'r-006'}), (a:Agent {id:'ag-receiver-02'})  MERGE (r)-[:PLAYED_BY]->(a);
MATCH (req:DeliveryRequest {id:'req-006'}), (s:Sender {id:'s-006'})      MERGE (req)-[:HAS_SENDER]->(s);
MATCH (req:DeliveryRequest {id:'req-006'}), (r:Receiver {id:'r-006'})    MERGE (req)-[:HAS_RECEIVER]->(r);
MATCH (req:DeliveryRequest {id:'req-006'}), (p:Parcel {id:'p-006'})      MERGE (req)-[:HAS_DELIVERY_ITEM]->(p);
MATCH (req:DeliveryRequest {id:'req-006'}), (loc:Address {id:'addr-it-rome-1'})  MERGE (req)-[:HAS_PICK_UP_LOCATION]->(loc);
MATCH (req:DeliveryRequest {id:'req-006'}), (loc:Address {id:'addr-md-balti-1'}) MERGE (req)-[:HAS_DROP_OFF_LOCATION]->(loc);

// req-007: new, elena -> maria (no transporter)
MERGE (s:Sender {id:'s-007'});
MERGE (r:Receiver {id:'r-007'});
MERGE (req:DeliveryRequest {id:'req-007'})
  SET req.hasStatus='new',
      req.created=datetime('2026-07-15T12:00:00'),
      req.updated=datetime('2026-07-15T12:00:00'),
      req.requestNote=['Gifts for family.'];
MATCH (s:Sender {id:'s-007'}), (a:Agent {id:'ag-sender-01'})      MERGE (s)-[:PLAYED_BY]->(a);
MATCH (r:Receiver {id:'r-007'}), (a:Agent {id:'ag-receiver-01'})  MERGE (r)-[:PLAYED_BY]->(a);
MATCH (req:DeliveryRequest {id:'req-007'}), (s:Sender {id:'s-007'})      MERGE (req)-[:HAS_SENDER]->(s);
MATCH (req:DeliveryRequest {id:'req-007'}), (r:Receiver {id:'r-007'})    MERGE (req)-[:HAS_RECEIVER]->(r);
MATCH (req:DeliveryRequest {id:'req-007'}), (p:Parcel {id:'p-007'})      MERGE (req)-[:HAS_DELIVERY_ITEM]->(p);
MATCH (req:DeliveryRequest {id:'req-007'}), (loc:Address {id:'addr-de-munich-1'})  MERGE (req)-[:HAS_PICK_UP_LOCATION]->(loc);
MATCH (req:DeliveryRequest {id:'req-007'}), (loc:Address {id:'addr-md-chisinau-1'}) MERGE (req)-[:HAS_DROP_OFF_LOCATION]->(loc);

// req-008: cancelled (after accepted), andrei -> ion via diaspora
MERGE (s:Sender {id:'s-008'});
MERGE (r:Receiver {id:'r-008'});
MERGE (t:Transporter {id:'t-005'});
MERGE (req:DeliveryRequest {id:'req-008'})
  SET req.hasStatus='cancelled',
      req.created=datetime('2026-06-20T10:00:00'),
      req.updated=datetime('2026-06-22T14:00:00'),
      req.closed=datetime('2026-06-22T14:00:00'),
      req.requestNote=['Sender cancelled — plans changed.'];
MATCH (s:Sender {id:'s-008'}), (a:Agent {id:'ag-sender-02'})       MERGE (s)-[:PLAYED_BY]->(a);
MATCH (r:Receiver {id:'r-008'}), (a:Agent {id:'ag-receiver-02'})   MERGE (r)-[:PLAYED_BY]->(a);
MATCH (t:Transporter {id:'t-005'}), (a:Agent {id:'ag-transporter-02'}) MERGE (t)-[:PLAYED_BY]->(a);
MATCH (req:DeliveryRequest {id:'req-008'}), (s:Sender {id:'s-008'})       MERGE (req)-[:HAS_SENDER]->(s);
MATCH (req:DeliveryRequest {id:'req-008'}), (r:Receiver {id:'r-008'})     MERGE (req)-[:HAS_RECEIVER]->(r);
MATCH (req:DeliveryRequest {id:'req-008'}), (t:Transporter {id:'t-005'})  MERGE (req)-[:HAS_TRANSPORTER]->(t);
MATCH (req:DeliveryRequest {id:'req-008'}), (p:Parcel {id:'p-008'})       MERGE (req)-[:HAS_DELIVERY_ITEM]->(p);
MATCH (req:DeliveryRequest {id:'req-008'}), (loc:Address {id:'addr-it-rome-1'})  MERGE (req)-[:HAS_PICK_UP_LOCATION]->(loc);
MATCH (req:DeliveryRequest {id:'req-008'}), (loc:Address {id:'addr-md-balti-1'}) MERGE (req)-[:HAS_DROP_OFF_LOCATION]->(loc);

// req-009: needsClarification, elena -> maria (intake clarification pending)
MERGE (s:Sender {id:'s-009'});
MERGE (r:Receiver {id:'r-009'});
MERGE (req:DeliveryRequest {id:'req-009'})
  SET req.hasStatus='needsClarification',
      req.created=datetime('2026-07-16T09:30:00'),
      req.updated=datetime('2026-07-16T09:35:00'),
      req.requestNote=['Parcel weight not specified yet.'];
MATCH (s:Sender {id:'s-009'}), (a:Agent {id:'ag-sender-01'})      MERGE (s)-[:PLAYED_BY]->(a);
MATCH (r:Receiver {id:'r-009'}), (a:Agent {id:'ag-receiver-01'})  MERGE (r)-[:PLAYED_BY]->(a);
MATCH (req:DeliveryRequest {id:'req-009'}), (s:Sender {id:'s-009'})      MERGE (req)-[:HAS_SENDER]->(s);
MATCH (req:DeliveryRequest {id:'req-009'}), (r:Receiver {id:'r-009'})    MERGE (req)-[:HAS_RECEIVER]->(r);
MATCH (req:DeliveryRequest {id:'req-009'}), (p:Parcel {id:'p-009'})      MERGE (req)-[:HAS_DELIVERY_ITEM]->(p);
MATCH (req:DeliveryRequest {id:'req-009'}), (loc:Address {id:'addr-de-munich-1'})  MERGE (req)-[:HAS_PICK_UP_LOCATION]->(loc);
MATCH (req:DeliveryRequest {id:'req-009'}), (loc:Address {id:'addr-md-chisinau-1'}) MERGE (req)-[:HAS_DROP_OFF_LOCATION]->(loc);

// ============================================================================
// 8. Feedback (reified rating/comment between participations)
//    Feedback -[:FROM_PROVIDER]-> AgentInRole (author)
//    Feedback -[:TO_RECIPIENT]-> AgentInRole (subject)
//    Feedback -[:ABOUT_REQUEST]-> DeliveryRequest (optional)
// ============================================================================
MERGE (f:Feedback {id:'fb-001'}) SET f.rating=4, f.comment='Punctual pickup, good communication.';
MERGE (f:Feedback {id:'fb-002'}) SET f.rating=5, f.comment='Parcel arrived intact, thank you!';
MERGE (f:Feedback {id:'fb-003'}) SET f.rating=5, f.comment='Easy handover, clear instructions.';
MATCH (f:Feedback {id:'fb-001'}), (s:Sender {id:'s-001'})        MERGE (f)-[:FROM_PROVIDER]->(s);
MATCH (f:Feedback {id:'fb-001'}), (t:Transporter {id:'t-001'})   MERGE (f)-[:TO_RECIPIENT]->(t);
MATCH (f:Feedback {id:'fb-001'}), (req:DeliveryRequest {id:'req-001'}) MERGE (f)-[:ABOUT_REQUEST]->(req);
MATCH (f:Feedback {id:'fb-002'}), (r:Receiver {id:'r-001'})      MERGE (f)-[:FROM_PROVIDER]->(r);
MATCH (f:Feedback {id:'fb-002'}), (t:Transporter {id:'t-001'})   MERGE (f)-[:TO_RECIPIENT]->(t);
MATCH (f:Feedback {id:'fb-002'}), (req:DeliveryRequest {id:'req-001'}) MERGE (f)-[:ABOUT_REQUEST]->(req);
MATCH (f:Feedback {id:'fb-003'}), (t:Transporter {id:'t-001'})   MERGE (f)-[:FROM_PROVIDER]->(t);
MATCH (f:Feedback {id:'fb-003'}), (s:Sender {id:'s-001'})        MERGE (f)-[:TO_RECIPIENT]->(s);
MATCH (f:Feedback {id:'fb-003'}), (req:DeliveryRequest {id:'req-001'}) MERGE (f)-[:ABOUT_REQUEST]->(req);
