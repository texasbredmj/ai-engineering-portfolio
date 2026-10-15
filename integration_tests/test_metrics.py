from portfolio_platform.metrics import call_metrics


def test_tool_gateway_seconds_are_converted_to_dashboard_milliseconds():
    assert call_metrics('inventory.reserve',{'metrics':{'duration_seconds':.125}})=={
        'duration_ms':125,'input_tokens':0,'output_tokens':0,'cost_nusd':0}


def test_model_usage_includes_every_reported_attempt_and_simulated_accounting():
    result=call_metrics('model.generate',{'attempts':[
        {'latency_ms':10,'usage':{'input_tokens':4,'output_tokens':2}},
        {'latency_ms':20,'usage':{'input_tokens':6,'output_tokens':3}}], 'accounted_nusd':20000})
    assert result=={'duration_ms':30,'input_tokens':10,'output_tokens':5,'cost_nusd':20000}
