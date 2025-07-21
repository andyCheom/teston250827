from google.cloud import spanner

def query_spanner_triples(user_prompt: str, project_id: str, instance_id: str, database_id: str) -> List[str]:
    spanner_client = spanner.Client(project=project_id)
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    query = """
    SELECT subject, predicate, object
    FROM Triple
    WHERE subject LIKE @term OR predicate LIKE @term OR object LIKE @term
    LIMIT 20
    """
    params = {"term": f"%{user_prompt}%"}
    param_types = {"term": spanner.param_types.STRING}

    triples = []
    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(query, params=params, param_types=param_types)
        for row in results:
            triple_str = f"{row[0]} - {row[1]} - {row[2]}"
            triples.append(triple_str)
    return triples
