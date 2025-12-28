CREATE TABLE IF NOT EXISTS public.user_google_accounts (
    google_id serial PRIMARY KEY,
    user_id integer REFERENCES public.users(id) ON DELETE CASCADE,
    access_token text,
    refresh_token text,
    token_expiry timestamp without time zone,
    token_uri text,
    client_id text,
    client_secret text,
    scopes text[],
    created_at timestamp without time zone DEFAULT now(),
    UNIQUE(user_id)
);
