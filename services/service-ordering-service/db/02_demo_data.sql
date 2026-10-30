INSERT INTO service_specification (id, name, slice_type, lifecycle_status) VALUES
  ('SPEC-C2-URLLC',     'C2 Connectivity',      'URLLC', 'active'),
  ('SPEC-IMAGERY-EMBB', 'Imagery Connectivity', 'eMBB',  'active');

INSERT INTO service_spec_characteristic (specification_id, name, position, value_type, value) VALUES
  ('SPEC-C2-URLLC', 'sst',              1, 'integer', '2'),
  ('SPEC-C2-URLLC', 'sd',               2, 'string',  '000001'),
  ('SPEC-C2-URLLC', 'dnn',              3, 'string',  'c2'),
  ('SPEC-C2-URLLC', '5qi',              4, 'integer', '7'),
  ('SPEC-C2-URLLC', 'arp',              5, 'integer', '2'),
  ('SPEC-C2-URLLC', 'ambrUplinkMbps',   6, 'integer', '20'),
  ('SPEC-C2-URLLC', 'ambrDownlinkMbps', 7, 'integer', '20'),
  ('SPEC-IMAGERY-EMBB', 'sst',              1, 'integer', '1'),
  ('SPEC-IMAGERY-EMBB', 'sd',               2, 'string',  '000002'),
  ('SPEC-IMAGERY-EMBB', 'dnn',              3, 'string',  'imagery'),
  ('SPEC-IMAGERY-EMBB', '5qi',              4, 'integer', '9'),
  ('SPEC-IMAGERY-EMBB', 'arp',              5, 'integer', '8'),
  ('SPEC-IMAGERY-EMBB', 'ambrUplinkMbps',   6, 'integer', '500'),
  ('SPEC-IMAGERY-EMBB', 'ambrDownlinkMbps', 7, 'integer', '100');
