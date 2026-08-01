-- Existing members with a filled shipping profile should not hit the onboarding gate.
update profiles
set onboarding_completed_at = coalesce(
  (select u.created_at from users u where u.id = profiles.id),
  now()
)
where onboarding_completed_at is null
  and nullif(btrim(coalesce(full_name, '')), '') is not null
  and nullif(btrim(coalesce(phone, '')), '') is not null
  and nullif(btrim(coalesce(shipping_postal, '')), '') is not null
  and nullif(btrim(coalesce(shipping_city, '')), '') is not null
  and nullif(btrim(coalesce(shipping_address, '')), '') is not null;
