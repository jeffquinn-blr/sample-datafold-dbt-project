select * from {{ ref('test_model') }}
where state = 'FL'