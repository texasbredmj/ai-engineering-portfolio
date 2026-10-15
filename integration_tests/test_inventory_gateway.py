from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from tool_gateway.app import Config, Principal, OPERATOR_SCOPES, ADMIN_SCOPES, create_app


@pytest.mark.parametrize('observed,expected', [(2,'SUCCEEDED'),(3,'UNVERIFIED')])
def test_inventory_write_requires_separate_approval_and_independent_read(tmp_path, observed, expected):
    calls=[]
    args={'workflow_id':'ops-11111111-1111-1111-1111-111111111111-1','quantity':2}
    def upstream(request):
        calls.append(request.method)
        return httpx.Response(200,json={**args,'state':'ACTIVE','observed_quantity':observed})
    config=Config(root=tmp_path,data_dir=tmp_path/'data',upstream_url='http://fixture',
        credentials={'operator-token-123456789':Principal('requester',OPERATOR_SCOPES),
                     'approver-token-123456789':Principal('reviewer',ADMIN_SCOPES)},
        transport=httpx.MockTransport(upstream))
    operator={'Authorization':'Bearer operator-token-123456789'}
    approver={'Authorization':'Bearer approver-token-123456789'}
    with TestClient(create_app(config)) as client:
        body={'arguments':args,'idempotency_key':'reservation-1'}
        blocked=client.post('/v1/tools/inventory.reserve/invoke',headers=operator,json=body)
        assert blocked.status_code in (403,409)
        assert not calls
        approval=client.post('/v1/approvals',headers=operator,json={'tool_id':'inventory.reserve','arguments':args}).json()
        route='/v1/approvals/'+approval['approval_id']+'/decision'
        assert client.post(route,headers=operator,json={'approve':True}).status_code==403
        assert client.post(route,headers=approver,json={'approve':True}).status_code==200
        body['approval_id']=approval['approval_id']
        result=client.post('/v1/tools/inventory.reserve/invoke',headers=operator,json=body)
        assert result.status_code==200
        assert result.json()['state']==expected
        assert result.json()['verified_completion'] is (observed==2)
        assert calls==['POST','GET']
        repeated=client.post('/v1/tools/inventory.reserve/invoke',headers=operator,json=body)
        assert repeated.json()==result.json()
        assert calls==['POST','GET']
