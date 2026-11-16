# Setup checklist

Accounts and secret **names** only. Do not put secret values in this repository.

- [ ] GitHub repository (empty HTTPS remote for this project)
- [ ] Supabase project
  - [ ] Project URL
  - [ ] Anon key
  - [ ] Service-role key
  - [ ] JWT secret
  - [ ] Database password
- [ ] Anthropic API key
- [ ] Vercel account
- [ ] Render account

Store every secret outside the repo (a password manager or a local file that Git ignores). Never commit `.env` files, keys, or passwords.
