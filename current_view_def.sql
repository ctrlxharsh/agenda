 SELECT ce.event_id,
    ce.user_id AS organizer_id,
    u.username AS organizer_username,
    ce.start_time,
    ce.end_time,
    ce.event_desc,
    ce.event_type,
    ml.meeting_url,
    ml.platform,
    count(ec.collab_id) AS collaborator_count
   FROM calendar_events ce
     LEFT JOIN users u ON ce.user_id = u.id
     LEFT JOIN meeting_links ml ON ce.event_id = ml.event_id
     LEFT JOIN event_collaborators ec ON ce.event_id = ec.event_id
  WHERE ce.event_type::text = 'meeting'::text AND ce.start_time > now()
  GROUP BY ce.event_id, u.username, ml.meeting_url, ml.platform
  ORDER BY ce.start_time;