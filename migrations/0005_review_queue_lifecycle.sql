CREATE OR REPLACE FUNCTION list_escalations() RETURNS SETOF jsonb
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
    WHERE e.status <> 'closed'
    ORDER BY e.created_at DESC
    LIMIT 100
$$;

CREATE OR REPLACE FUNCTION record_review_action(
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
    IF p_reason IS NULL OR length(btrim(p_reason)) NOT BETWEEN 3 AND 500 THEN
        RETURN false;
    END IF;
    IF p_action = 'route' AND (
        p_route IS NULL
        OR p_route NOT IN (
            'customer_service',
            'complaints',
            'fraud_operations',
            'hardship',
            'lending_specialist',
            'legal_compliance'
        )
    ) THEN
        RETURN false;
    END IF;
    IF p_action <> 'route' AND p_route IS NOT NULL THEN
        RETURN false;
    END IF;

    UPDATE escalations
    SET
        status = CASE p_action
            WHEN 'acknowledge' THEN 'acknowledged'
            WHEN 'route' THEN 'routed'
            WHEN 'close' THEN 'closed'
            ELSE status
        END,
        route = CASE WHEN p_action = 'route' THEN p_route ELSE route END
    WHERE id = p_escalation_id
      AND (
          (p_action = 'acknowledge' AND status = 'open')
          OR (p_action = 'route' AND status IN ('open', 'acknowledged', 'routed'))
          OR (p_action = 'close' AND status IN ('open', 'acknowledged', 'routed'))
      )
    RETURNING request_id INTO target_request_id;

    IF target_request_id IS NULL THEN
        RETURN false;
    END IF;

    INSERT INTO review_actions(escalation_id, actor_id, action, route, reason)
    VALUES (p_escalation_id, p_actor_id, p_action, p_route, btrim(p_reason));
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
