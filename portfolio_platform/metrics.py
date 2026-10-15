"""Project reported gateway measurements into dashboard units without inventing timings."""


def call_metrics(name, report):
    if name == 'model.generate':
        attempts=report.get('attempts') or []
        usage=[attempt.get('usage') or {} for attempt in attempts]
        if not usage:
            usage=[report.get('usage') or {}]
        return {'duration_ms':sum(attempt.get('latency_ms',0) for attempt in attempts),
                'input_tokens':sum(item.get('input_tokens',0) for item in usage),
                'output_tokens':sum(item.get('output_tokens',0) for item in usage),
                'cost_nusd':report.get('accounted_nusd',0)}
    return {'duration_ms':report.get('metrics',{}).get('duration_seconds',0)*1000,
            'input_tokens':0,'output_tokens':0,'cost_nusd':0}
