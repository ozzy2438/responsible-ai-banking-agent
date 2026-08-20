REVOKE ALL ON customers, accounts, transactions, assist_requests, escalations,
    review_actions, audit_events FROM PUBLIC, banking_app;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, banking_app;

GRANT USAGE ON SCHEMA public TO banking_app;
GRANT EXECUTE ON FUNCTION get_authorized_account(uuid, uuid) TO banking_app;
GRANT EXECUTE ON FUNCTION get_authorized_transactions(uuid, uuid, integer) TO banking_app;

CREATE FUNCTION persist_assist_response(
    p_request_id uuid,
    p_actor_id uuid,
    p_idempotency_key text,
    p_redacted_message text,
    p_risk_level text,
    p_disposition text,
    p_response_json jsonb,
    p_escalation_id uuid,
    p_route text,
    p_summary text
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    stored jsonb;
BEGIN
    INSERT INTO assist_requests(
        id, actor_id, idempotency_key, redacted_message, risk_level, disposition, response_json
    ) VALUES (
        p_request_id, p_actor_id, p_idempotency_key, p_redacted_message,
        p_risk_level, p_disposition, p_response_json
    )
    ON CONFLICT (actor_id, idempotency_key) DO NOTHING;

    IF FOUND THEN
        IF p_escalation_id IS NOT NULL AND p_route IS NOT NULL THEN
            INSERT INTO escalations(id, request_id, route, summary)
            VALUES (p_escalation_id, p_request_id, p_route, p_summary);
        END IF;
        INSERT INTO audit_events(request_id, actor_id, event_type, event_json)
        VALUES (
            p_request_id,
            p_actor_id,
            'assist_completed',
            jsonb_build_object(
                'risk', p_risk_level,
                'disposition', p_disposition,
                'escalated', p_escalation_id IS NOT NULL
            )
        );
    END IF;

    SELECT response_json INTO stored
    FROM assist_requests
    WHERE actor_id = p_actor_id AND idempotency_key = p_idempotency_key;
    RETURN stored;
END
$$;

CREATE FUNCTION get_request_response(p_actor_id uuid, p_request_id uuid) RETURNS jsonb
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public, pg_temp
AS $$
    SELECT response_json
    FROM assist_requests
    WHERE actor_id = p_actor_id AND id = p_request_id
$$;

CREATE FUNCTION list_escalations() RETURNS SETOF jsonb
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public, pg_temp
AS $$
    SELECT jsonb_build_object(
        'id', e.id,
        'request_id', e.request_id,
        'route', e.route,
        'status', e.status,
        'summary', e.summary,
        'created_at', e.created_at,
        'risk_level', r.risk_level,
        'redacted_message', r.redacted_message
    )
    FROM escalations e
    JOIN assist_requests r ON r.id = e.request_id
    ORDER BY e.created_at DESC
$$;

CREATE FUNCTION record_review_action(
    p_escalation_id uuid,
    p_actor_id uuid,
    p_action text,
    p_route text,
    p_reason text
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    target_request_id uuid;
BEGIN
    UPDATE escalations
    SET status = CASE p_action
        WHEN 'acknowledge' THEN 'acknowledged'
        WHEN 'route' THEN 'routed'
        WHEN 'close' THEN 'closed'
        ELSE status
    END
    WHERE id = p_escalation_id AND p_action IN ('acknowledge', 'route', 'close')
    RETURNING request_id INTO target_request_id;
    IF target_request_id IS NULL THEN
        RETURN false;
    END IF;
    INSERT INTO review_actions(escalation_id, actor_id, action, route, reason)
    VALUES (p_escalation_id, p_actor_id, p_action, p_route, p_reason);
    INSERT INTO audit_events(request_id, actor_id, event_type, event_json)
    VALUES (
        target_request_id,
        p_actor_id,
        'review_action',
        jsonb_build_object('action', p_action, 'route', p_route)
    );
    RETURN true;
END
$$;

REVOKE ALL ON FUNCTION persist_assist_response(
    uuid, uuid, text, text, text, text, jsonb, uuid, text, text
) FROM PUBLIC;
REVOKE ALL ON FUNCTION get_request_response(uuid, uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION list_escalations() FROM PUBLIC;
REVOKE ALL ON FUNCTION record_review_action(uuid, uuid, text, text, text) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION persist_assist_response(
    uuid, uuid, text, text, text, text, jsonb, uuid, text, text
) TO banking_app;
GRANT EXECUTE ON FUNCTION get_request_response(uuid, uuid) TO banking_app;
GRANT EXECUTE ON FUNCTION list_escalations() TO banking_app;
GRANT EXECUTE ON FUNCTION record_review_action(uuid, uuid, text, text, text) TO banking_app;
