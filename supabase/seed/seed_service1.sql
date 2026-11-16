-- Seed for Community Certificate (REV-101).
-- Rows come from docs/service1-documents.md. That file records official names,
-- but formats, mandatory/optional labels, expiry, and key fields are not specified,
-- and the DNC item is an unresolved FAQ vs Service List difference.
-- is_verified stays false. accepted_formats and quality rules below are app defaults, not official rules.
-- Safe to run again.

INSERT INTO public.services (slug, name_en, name_ta, description, is_active, is_verified)
VALUES (
  'community-certificate',
  'Community Certificate',
  'சாதிச் சான்றிதழ்',
  'DRAFT – verify against the official e-Sevai portal. Revenue Administration service REV-101. FAQ Question 7 lists Photo, Address Proof, a parent or sibling community certificate, and a self-declaration. The Service List also lists DNC Certificate. That difference is not resolved.',
  true,
  false
)
ON CONFLICT (slug) DO UPDATE
SET
  name_en = EXCLUDED.name_en,
  name_ta = EXCLUDED.name_ta,
  description = EXCLUDED.description,
  is_active = EXCLUDED.is_active,
  is_verified = EXCLUDED.is_verified,
  updated_at = now();

INSERT INTO public.required_documents (
  service_id, code, name_en, name_ta, description, is_mandatory,
  accepted_formats, max_size_mb, validity_days, keywords, required_fields, rules, sort_order, is_active
)
SELECT
  services.id,
  items.code,
  items.name_en,
  items.name_ta,
  items.description,
  items.is_mandatory,
  items.accepted_formats,
  items.max_size_mb,
  items.validity_days,
  items.keywords,
  items.required_fields,
  items.rules,
  items.sort_order,
  true
FROM public.services AS services
CROSS JOIN (
  VALUES
    (
      'applicant_photo',
      'Photo',
      'புகைப்படம்',
      'Listed as item 1 in FAQ Question 7 and on the Service List. Official format and mandatory label are not specified.',
      true,
      ARRAY['jpg', 'jpeg', 'png', 'pdf'],
      5,
      NULL::int,
      '{"en":[],"ta":[]}'::jsonb,
      '[]'::jsonb,
      '{"min_width":400,"min_height":500,"min_blur_score":80,"min_brightness":60,"max_brightness":220,"check_name_match":false,"fields_are_draft":true}'::jsonb,
      1
    ),
    (
      'address_proof',
      'Address Proof',
      'முகவரிச் சான்று',
      'FAQ Question 7 says Address Proof. The Service List says Any Address Proof. Accepted proof types are not named.',
      true,
      ARRAY['jpg', 'jpeg', 'png', 'pdf'],
      5,
      NULL::int,
      '{"en":["address","address proof"],"ta":["முகவரி"]}'::jsonb,
      '["name","date"]'::jsonb,
      '{"min_width":800,"min_height":600,"min_blur_score":100,"min_brightness":60,"max_brightness":220,"max_age_days":null,"check_name_match":true,"fields_are_draft":true}'::jsonb,
      2
    ),
    (
      'parent_or_sibling_community_certificate',
      'Community Certificate of Father OR Mother OR Siblings',
      'தந்தை அல்லது தாய் அல்லது உடன்பிறந்தவரின் சாதிச் சான்றிதழ்',
      'One checklist item. The sources list the father, mother, or sibling certificate as alternatives and do not say that more than one is required.',
      true,
      ARRAY['jpg', 'jpeg', 'png', 'pdf'],
      5,
      NULL::int,
      '{"en":["community certificate","father","mother","sibling"],"ta":["சாதி"]}'::jsonb,
      '["name","date"]'::jsonb,
      '{"min_width":800,"min_height":600,"min_blur_score":100,"min_brightness":60,"max_brightness":220,"max_age_days":null,"check_name_match":true,"fields_are_draft":true}'::jsonb,
      3
    ),
    (
      'self_declaration',
      'Self-Declaration of Applicant',
      'விண்ணப்பதாரரின் சுய உறுதிமொழி',
      'Listed as item 4 in FAQ Question 7 and on the Service List. Official format and expiry are not specified.',
      true,
      ARRAY['jpg', 'jpeg', 'png', 'pdf'],
      5,
      NULL::int,
      '{"en":["self declaration","declaration","applicant"],"ta":["உறுதிமொழி"]}'::jsonb,
      '["name","date"]'::jsonb,
      '{"min_width":800,"min_height":600,"min_blur_score":100,"min_brightness":60,"max_brightness":220,"max_age_days":null,"check_name_match":true,"fields_are_draft":true}'::jsonb,
      4
    ),
    (
      'dnc_certificate',
      'DNC Certificate',
      'DNC சான்றிதழ்',
      'Listed only on the Service List, not in FAQ Question 7. Do not treat this as required until that difference is confirmed.',
      false,
      ARRAY['jpg', 'jpeg', 'png', 'pdf'],
      5,
      NULL::int,
      '{"en":["DNC","DNC certificate"],"ta":["DNC"]}'::jsonb,
      '["name","date"]'::jsonb,
      '{"min_width":800,"min_height":600,"min_blur_score":100,"min_brightness":60,"max_brightness":220,"max_age_days":null,"check_name_match":true,"fields_are_draft":true,"discrepancy_unresolved":true}'::jsonb,
      5
    )
) AS items (
  code text,
  name_en text,
  name_ta text,
  description text,
  is_mandatory boolean,
  accepted_formats text[],
  max_size_mb int,
  validity_days int,
  keywords jsonb,
  required_fields jsonb,
  rules jsonb,
  sort_order int
)
WHERE services.slug = 'community-certificate'
ON CONFLICT (service_id, code) DO UPDATE
SET
  name_en = EXCLUDED.name_en,
  name_ta = EXCLUDED.name_ta,
  description = EXCLUDED.description,
  is_mandatory = EXCLUDED.is_mandatory,
  accepted_formats = EXCLUDED.accepted_formats,
  max_size_mb = EXCLUDED.max_size_mb,
  validity_days = EXCLUDED.validity_days,
  keywords = EXCLUDED.keywords,
  required_fields = EXCLUDED.required_fields,
  rules = EXCLUDED.rules,
  sort_order = EXCLUDED.sort_order,
  is_active = EXCLUDED.is_active,
  updated_at = now();
