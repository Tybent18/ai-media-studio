def validate_pipeline_output(scenes, timeline):
    assert len(scenes) > 0
    assert "timeline" in timeline
    assert all(t["end_time"] > t["start_time"] for t in timeline["timeline"])