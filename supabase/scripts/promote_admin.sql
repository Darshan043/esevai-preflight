-- Create the user first in Supabase Dashboard > Authentication > Users > Add user (tick Auto Confirm User).
-- Replace the placeholder email, then run this script. It does not contain a real address.

UPDATE public.profiles
SET role = 'admin'
WHERE id = (
  SELECT users.id
  FROM auth.users AS users
  WHERE users.email = 'REPLACE_WITH_YOUR_EMAIL'
);

SELECT
  users.email,
  profiles.id,
  profiles.role
FROM public.profiles AS profiles
JOIN auth.users AS users ON users.id = profiles.id
WHERE users.email = 'REPLACE_WITH_YOUR_EMAIL';
