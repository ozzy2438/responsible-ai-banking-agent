CREATE TABLE customers (
    id uuid PRIMARY KEY,
    display_name text NOT NULL,
    synthetic boolean NOT NULL CHECK (synthetic)
);

CREATE TABLE accounts (
    id uuid PRIMARY KEY,
    customer_id uuid NOT NULL REFERENCES customers(id),
    account_name text NOT NULL,
    currency char(3) NOT NULL,
    available_balance numeric(14,2) NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE transactions (
    id uuid PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES accounts(id),
    description text NOT NULL,
    amount numeric(14,2) NOT NULL,
    booked_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE assist_requests (
    id uuid PRIMARY KEY,
    actor_id uuid NOT NULL,
    idempotency_key text NOT NULL,
    redacted_message text NOT NULL,
    risk_level text NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    disposition text NOT NULL CHECK (disposition IN ('answered', 'escalated', 'needs_information')),
    response_json jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (actor_id, idempotency_key)
);

CREATE TABLE escalations (
    id uuid PRIMARY KEY,
    request_id uuid NOT NULL UNIQUE REFERENCES assist_requests(id),
    route text NOT NULL,
    status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'routed', 'closed')),
    summary text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE review_actions (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    escalation_id uuid NOT NULL REFERENCES escalations(id),
    actor_id uuid NOT NULL,
    action text NOT NULL CHECK (action IN ('acknowledge', 'route', 'close')),
    route text,
    reason text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id uuid NOT NULL REFERENCES assist_requests(id),
    actor_id uuid NOT NULL,
    event_type text NOT NULL,
    event_json jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE FUNCTION deny_immutable_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'immutable record';
END
$$;

CREATE TRIGGER audit_events_immutable
BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION deny_immutable_change();

CREATE TRIGGER review_actions_immutable
BEFORE UPDATE OR DELETE ON review_actions
FOR EACH ROW EXECUTE FUNCTION deny_immutable_change();

CREATE FUNCTION get_authorized_account(p_actor_id uuid, p_account_id uuid)
RETURNS TABLE(
    account_id uuid,
    account_name text,
    currency text,
    available_balance text,
    updated_at timestamptz
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT a.id, a.account_name, a.currency::text,
           to_char(a.available_balance, 'FM999999999990.00'), a.updated_at
    FROM accounts a
    WHERE a.id = p_account_id AND a.customer_id = p_actor_id
$$;

REVOKE ALL ON FUNCTION get_authorized_account(uuid, uuid) FROM PUBLIC;

CREATE FUNCTION get_authorized_transactions(p_actor_id uuid, p_account_id uuid, p_limit integer)
RETURNS TABLE(
    transaction_id uuid,
    description text,
    amount text,
    currency text,
    booked_at timestamptz,
    updated_at timestamptz
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT t.id, t.description, to_char(t.amount, 'FM999999999990.00'), a.currency::text,
           t.booked_at, t.updated_at
    FROM transactions t
    JOIN accounts a ON a.id = t.account_id
    WHERE a.id = p_account_id AND a.customer_id = p_actor_id
    ORDER BY t.booked_at DESC, t.id
    LIMIT LEAST(GREATEST(p_limit, 1), 20)
$$;

REVOKE ALL ON FUNCTION get_authorized_transactions(uuid, uuid, integer) FROM PUBLIC;

INSERT INTO customers(id, display_name, synthetic) VALUES
('11111111-1111-4111-8111-111111111111', 'Alice Example', true),
('22222222-2222-4222-8222-222222222222', 'Bob Example', true);

INSERT INTO accounts(id, customer_id, account_name, currency, available_balance, updated_at) VALUES
('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', '11111111-1111-4111-8111-111111111111', 'Synthetic Everyday', 'AUD', 1250.50, now()),
('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', '22222222-2222-4222-8222-222222222222', 'Synthetic Saver', 'AUD', 875.25, now());

INSERT INTO transactions(id, account_id, description, amount, booked_at, updated_at) VALUES
('a1000000-0000-4000-8000-000000000001', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'Synthetic grocery', -42.10, now() - interval '1 day', now()),
('b1000000-0000-4000-8000-000000000001', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'Synthetic deposit', 100.00, now() - interval '2 days', now());
