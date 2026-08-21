CREATE TABLE rate_limit_buckets (
    subject_hash text NOT NULL CHECK (length(subject_hash) = 64),
    route_group text NOT NULL CHECK (length(route_group) BETWEEN 1 AND 120),
    window_start timestamptz NOT NULL,
    request_count integer NOT NULL CHECK (request_count > 0),
    PRIMARY KEY (subject_hash, route_group, window_start)
);

REVOKE ALL ON TABLE rate_limit_buckets FROM PUBLIC;
REVOKE ALL ON TABLE rate_limit_buckets FROM banking_app;

CREATE OR REPLACE FUNCTION consume_rate_limit(
    p_subject_hash text,
    p_route_group text,
    p_limit integer,
    p_window_seconds integer
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_window timestamptz;
    v_count integer;
BEGIN
    IF length(p_subject_hash) <> 64
        OR length(p_route_group) NOT BETWEEN 1 AND 120
        OR p_limit NOT BETWEEN 1 AND 10000
        OR p_window_seconds NOT BETWEEN 1 AND 3600 THEN
        RAISE EXCEPTION 'invalid rate limit input';
    END IF;

    v_window := to_timestamp(
        floor(extract(epoch FROM clock_timestamp()) / p_window_seconds)
        * p_window_seconds
    );

    INSERT INTO public.rate_limit_buckets(
        subject_hash, route_group, window_start, request_count
    ) VALUES (p_subject_hash, p_route_group, v_window, 1)
    ON CONFLICT (subject_hash, route_group, window_start)
    DO UPDATE SET request_count = public.rate_limit_buckets.request_count + 1
    RETURNING request_count INTO v_count;

    DELETE FROM public.rate_limit_buckets
    WHERE subject_hash = p_subject_hash
      AND route_group = p_route_group
      AND window_start < v_window - make_interval(secs => p_window_seconds * 2);

    RETURN v_count <= p_limit;
END;
$$;

REVOKE ALL ON FUNCTION consume_rate_limit(text, text, integer, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION consume_rate_limit(text, text, integer, integer) TO banking_app;
